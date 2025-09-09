from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request
import openai
import os
import logging
import re
import time
import json
import tempfile
import fcntl
from collections import OrderedDict

# Set up logging - show info level for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

slack_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)
handler = SlackRequestHandler(slack_app)
openai.api_key = os.environ["OPENAI_API_KEY"]
ASSISTANT_ID = os.environ["OPENAI_ASSISTANT_ID"]

# Message deduplication cache to prevent processing the same message twice
# This helps when Heroku dyno wakes up and receives duplicate webhook events
class MessageDeduplicationCache:
    def __init__(self, max_size=1000, ttl_seconds=300):  # 5 minutes TTL
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache_file = os.path.join(tempfile.gettempdir(), 'message_cache.json')
    
    def load_cache(self):
        """Load cache from file with file locking"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                    try:
                        return json.load(f)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Error loading message cache: {str(e)}")
        return {}
    
    def save_cache(self, cache):
        """Save cache to file with file locking"""
        try:
            # Clean up old entries (keep only last max_size to prevent file from growing too large)
            if len(cache) > self.max_size:
                # Keep the most recent entries
                sorted_items = sorted(cache.items(), key=lambda x: x[1], reverse=True)
                cache = dict(sorted_items[:self.max_size])
                logger.info(f"Cleaned up message cache, kept {len(cache)} entries")
            
            with open(self.cache_file, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
                try:
                    json.dump(cache, f)
                    f.flush()  # Ensure data is written to disk
                    os.fsync(f.fileno())  # Force sync to disk
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Error saving message cache: {str(e)}")
    
    def is_processed(self, message_id):
        """Check if message has been processed recently"""
        current_time = time.time()
        cache = self.load_cache()
        
        # Clean expired entries
        expired_keys = [k for k, v in cache.items() if current_time - v > self.ttl_seconds]
        for key in expired_keys:
            del cache[key]
        
        # Check if message exists and is not expired
        if message_id in cache:
            if current_time - cache[message_id] <= self.ttl_seconds:
                return True
            else:
                # Remove expired entry
                del cache[message_id]
                self.save_cache(cache)
        
        return False
    
    def mark_processed(self, message_id):
        """Mark message as processed"""
        current_time = time.time()
        cache = self.load_cache()
        
        # Add to cache
        cache[message_id] = current_time
        
        # Save updated cache
        self.save_cache(cache)
    
    def get_stats(self):
        """Get cache statistics for debugging"""
        current_time = time.time()
        cache = self.load_cache()
        active_entries = sum(1 for v in cache.values() if current_time - v <= self.ttl_seconds)
        return {
            'total_entries': len(cache),
            'active_entries': active_entries,
            'max_size': self.max_size,
            'ttl_seconds': self.ttl_seconds
        }

# Initialize message deduplication cache
message_cache = MessageDeduplicationCache()

# Store thread to OpenAI thread mapping for context retention

THREAD_MAPPING_FILE = os.path.join(tempfile.gettempdir(), 'thread_mapping.json')

def load_thread_mapping():
    """Load thread mapping from file with file locking"""
    try:
        if os.path.exists(THREAD_MAPPING_FILE):
            with open(THREAD_MAPPING_FILE, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                try:
                    return json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        logger.error(f"Error loading thread mapping: {str(e)}")
    return {}

def save_thread_mapping(thread_mapping):
    """Save thread mapping to file with file locking"""
    try:
        # Clean up old mappings (keep only last 100 to prevent file from growing too large)
        if len(thread_mapping) > 100:
            # Keep the most recent 100 entries
            sorted_items = sorted(thread_mapping.items(), key=lambda x: x[0], reverse=True)
            thread_mapping = dict(sorted_items[:100])
            logger.info(f"Cleaned up thread mapping, kept {len(thread_mapping)} entries")
        
        with open(THREAD_MAPPING_FILE, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
            try:
                json.dump(thread_mapping, f)
                f.flush()  # Ensure data is written to disk
                os.fsync(f.fileno())  # Force sync to disk
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        logger.error(f"Error saving thread mapping: {str(e)}")

def get_thread_mapping():
    """Get current thread mapping (loads from file each time to avoid race conditions)"""
    return load_thread_mapping()

def update_thread_mapping(conversation_id, openai_thread_id):
    """Update thread mapping atomically"""
    thread_mapping = load_thread_mapping()
    thread_mapping[conversation_id] = openai_thread_id
    save_thread_mapping(thread_mapping)
    return thread_mapping

# Initialize thread mapping
thread_mapping = load_thread_mapping()
logger.info(f"Loaded thread mapping with {len(thread_mapping)} entries: {list(thread_mapping.keys())}")

def strip_revision_preamble(text: str) -> str:
    """Remove meta prefaces like 'Revised answer:' or 'Here is the revised version' to keep tone natural."""
    try:
        cleaned = text.lstrip()
        lines = cleaned.splitlines()
        # Drop common preface lines at the top
        while lines:
            first = lines[0].strip()
            if re.match(r'^(revised answer|revision|updated answer|final answer|final|self[- ]?check)[:\- ]', first, re.IGNORECASE):
                lines.pop(0)
                continue
            if re.match(r"^(here( is|\'s)?\s+)?(the\s+)?(revised|final|updated)\s+(version|answer)[\.:\-]?$", first, re.IGNORECASE):
                lines.pop(0)
                continue
            if re.match(r'^here.*revised', first, re.IGNORECASE):
                lines.pop(0)
                continue
            break
        result = "\n".join(lines).strip()
        return result if result else cleaned
    except Exception:
        return text

def debug_conversation_history(thread_id):
    """Debug function to check conversation history in OpenAI thread"""
    try:
        current_thread_mapping = get_thread_mapping()
        if thread_id in current_thread_mapping:
            openai_thread_id = current_thread_mapping[thread_id]
            messages = openai.beta.threads.messages.list(thread_id=openai_thread_id)
            logger.info(f"Conversation history for thread {thread_id}:")
            for i, msg in enumerate(messages.data[:5]):  # Show last 5 messages
                role = msg.role
                content = msg.content[0].text.value[:100] + "..." if len(msg.content[0].text.value) > 100 else msg.content[0].text.value
                logger.info(f"  {i+1}. {role}: {content}")
    except Exception as e:
        logger.error(f"Error debugging conversation history: {str(e)}")

def clean_citations(response_text):
    """Clean up citations to show just the filename"""
    # Pattern to match citations like 【4:1†AI Engineering bootcamp_2025_07.pdf】 or 【4:9†source】
    citation_pattern = r'【\d+:\d+†([^】]+)】'
    
    def replace_citation(match):
        citation_content = match.group(1)
        # If it's just "source", remove it entirely
        if citation_content.lower() == 'source':
            return ''
        # Otherwise, show the filename in parentheses with a space before it
        return f' ({citation_content})'
    
    # Replace citations with just the filename in parentheses, or remove if it's "source"
    cleaned_response = re.sub(citation_pattern, replace_citation, response_text)
    
    return cleaned_response

def convert_markdown_to_slack(response_text):
    """Convert markdown formatting to Slack-compatible formatting"""
    # Use placeholders to protect formatting
    header_placeholders = {}
    bold_placeholders = {}
    placeholder_counter = 0
    
    # First, replace headers with placeholders
    def header_replacer(match):
        nonlocal placeholder_counter
        placeholder = f"HEADER_PLACEHOLDER_{placeholder_counter}_END"
        header_placeholders[placeholder] = f"\n*{match.group(1)}*\n"
        placeholder_counter += 1
        return placeholder
    
    # Replace bold text with placeholders to protect them
    def bold_replacer(match):
        nonlocal placeholder_counter
        placeholder = f"BOLD_PLACEHOLDER_{placeholder_counter}_END"
        bold_placeholders[placeholder] = f"*{match.group(1)}*"
        placeholder_counter += 1
        return placeholder
    
    response_text = re.sub(r'^####\s+(.+)$', header_replacer, response_text, flags=re.MULTILINE)
    response_text = re.sub(r'^###\s+(.+)$', header_replacer, response_text, flags=re.MULTILINE)
    response_text = re.sub(r'^##\s+(.+)$', header_replacer, response_text, flags=re.MULTILINE)
    response_text = re.sub(r'^#\s+(.+)$', header_replacer, response_text, flags=re.MULTILINE)
    
    # Convert bold markdown (***text***, **text**, or __text__) to placeholders first
    response_text = re.sub(r'\*\*\*(.*?)\*\*\*', bold_replacer, response_text)
    response_text = re.sub(r'\*\*(.*?)\*\*', bold_replacer, response_text)
    response_text = re.sub(r'__(.*?)__', bold_replacer, response_text)
    
    # Convert italic markdown (*text* or _text_) to Slack italic (_text_)
    # Now safe to do since bold text is protected by placeholders
    response_text = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'_\1_', response_text)
    response_text = re.sub(r'(?<!_)_([^_\n]+)_(?!_)', r'_\1_', response_text)
    
    # Convert markdown lists (- item or * item) to Slack lists
    response_text = re.sub(r'^[-*]\s+(.+)$', r'• \1', response_text, flags=re.MULTILINE)
    
    # Convert numbered lists (1. item) to Slack numbered lists
    response_text = re.sub(r'^(\d+)\.\s+(.+)$', r'\1. \2', response_text, flags=re.MULTILINE)
    
    # Convert markdown code blocks (```code```) to Slack code blocks
    response_text = re.sub(r'```([^`]*)```', r'`\1`', response_text, flags=re.DOTALL)
    
    # Convert inline code (`code`) to Slack inline code
    response_text = re.sub(r'`([^`]+)`', r'`\1`', response_text)
    
    # Restore bold text from placeholders
    for placeholder, bold_text in bold_placeholders.items():
        response_text = response_text.replace(placeholder, bold_text)
    
    # Restore headers from placeholders
    for placeholder, header_text in header_placeholders.items():
        response_text = response_text.replace(placeholder, header_text)
    
    # Clean up extra newlines that might have been created
    response_text = re.sub(r'\n{3,}', r'\n\n', response_text)
    
    # Remove any trailing whitespace
    response_text = response_text.rstrip()
    
    return response_text

def process_message(event, say):
    """Common function to process messages from both mentions and DMs"""
    user_message = event['text']
    
    # Create a unique message ID for deduplication
    # Use combination of channel, timestamp, and user to ensure uniqueness
    message_id = f"{event.get('channel', '')}_{event.get('ts', '')}_{event.get('user', '')}"
    
    # Check if this message has already been processed (deduplication)
    if message_cache.is_processed(message_id):
        logger.info(f"Message already processed, skipping: {message_id}")
        cache_stats = message_cache.get_stats()
        logger.info(f"Cache stats: {cache_stats}")
        return
    
    # Mark message as processed before processing to prevent race conditions
    message_cache.mark_processed(message_id)
    logger.info(f"Processing message with deduplication ID: {message_id}")
    cache_stats = message_cache.get_stats()
    logger.info(f"Cache stats: {cache_stats}")
    
    # Determine the conversation thread
    if event.get('thread_ts'):
        # This is a reply in a thread - use the thread timestamp as the conversation ID
        conversation_id = event['thread_ts']
        logger.info(f"Processing thread reply. Thread ID: {conversation_id}")
    else:
        # This is a new message - use the message timestamp as the conversation ID
        conversation_id = event['ts']
        logger.info(f"Processing new message. Message ID: {conversation_id}")
    
    # Get current thread mapping (load fresh to avoid race conditions)
    current_thread_mapping = get_thread_mapping()
    logger.info(f"Current thread mapping keys: {list(current_thread_mapping.keys())}")
    
    # Debug conversation history if this is an existing thread
    if conversation_id in current_thread_mapping:
        debug_conversation_history(conversation_id)
    
    # Get or create OpenAI thread for this Slack thread
    if conversation_id not in current_thread_mapping:
        # Create new OpenAI thread for this Slack thread
        openai_thread = openai.beta.threads.create()
        current_thread_mapping = update_thread_mapping(conversation_id, openai_thread.id)
        logger.info(f"Created new OpenAI thread: {openai_thread.id} for conversation: {conversation_id}")
    else:
        # Use existing OpenAI thread for this Slack thread
        openai_thread_id = current_thread_mapping[conversation_id]
        logger.info(f"Using existing OpenAI thread: {openai_thread_id} for conversation: {conversation_id}")
    
    try:
        # Get the OpenAI thread ID from current mapping
        openai_thread_id = current_thread_mapping[conversation_id]
        
        # Add the user message to the OpenAI thread
        openai.beta.threads.messages.create(
            thread_id=openai_thread_id,
            role="user",
            content=user_message
        )
        
        # Run the assistant
        run = openai.beta.threads.runs.create(
            thread_id=openai_thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        # Wait for the run to complete
        while run.status == "queued" or run.status == "in_progress":
            run = openai.beta.threads.runs.retrieve(
                thread_id=openai_thread_id,
                run_id=run.id
            )
        
        # Check if run failed
        if run.status == "failed":
            logger.error(f"OpenAI run failed: {run.last_error}")
            say("I'm sorry, I encountered an error processing your request. Please try again.")
            return
        
        # Get the assistant's response (first pass)
        messages = openai.beta.threads.messages.list(thread_id=openai_thread_id)
        assistant_message = messages.data[0].content[0].text.value

        # Second pass: self-check and revise before sending to Slack
        # This prompts the assistant to verify citations, trim unsupported claims,
        # add Not-in-Docs when needed, and keep the response concise.
        reviewer_instruction = (
            "Please review your previous response for accuracy. Follow these steps:\n"
            "\n"
            "1. FACT-CHECK: Verify every claim against the retrieved curriculum documents\n"
            "2. CITATIONS: Ensure all facts can be traced to specific documents and sections\n"
            "3. NO FABRICATION: Remove any information not explicitly stated in the source materials\n"
            "4. GAPS: If information isn't available in docs, state 'This information is not available in the official curriculum documentation'\n"
            "\n"
            "Provide a natural, accurate response based only on what's documented in the retrieved sources."
        )

        assistant_message_revised = None
        try:
            openai.beta.threads.messages.create(
                thread_id=openai_thread_id,
                role="user",
                content=reviewer_instruction
            )

            review_run = openai.beta.threads.runs.create(
                thread_id=openai_thread_id,
                assistant_id=ASSISTANT_ID
            )

            while review_run.status == "queued" or review_run.status == "in_progress":
                review_run = openai.beta.threads.runs.retrieve(
                    thread_id=openai_thread_id,
                    run_id=review_run.id
                )

            if review_run.status != "failed":
                reviewed_messages = openai.beta.threads.messages.list(thread_id=openai_thread_id)
                assistant_message_revised = reviewed_messages.data[0].content[0].text.value
            else:
                logger.warning("Self-check run failed; falling back to first-pass answer.")
        except Exception as e:
            logger.error(f"Error during self-check revision step: {str(e)}")
            assistant_message_revised = None
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        say("I'm sorry, I encountered an error processing your request. Please try again.")
        return
    
    # Choose revised answer if available
    final_text = assistant_message_revised if assistant_message_revised else assistant_message

    # Remove any meta revision preface, then clean citations and convert formatting
    final_text = strip_revision_preamble(final_text)
    cleaned_message = clean_citations(final_text)
    cleaned_message = convert_markdown_to_slack(cleaned_message)
    
    # Reply in the same thread if this was a thread reply, otherwise start a new thread
    if event.get('thread_ts'):
        say(cleaned_message, thread_ts=event['thread_ts'])
        logger.info(f"Replied in existing thread: {event['thread_ts']}")
    else:
        # When starting a new thread, use the message timestamp as the thread ID
        # and update the mapping to use the thread timestamp as the key
        say(cleaned_message, thread_ts=event['ts'])
        # Update mapping: move from message timestamp to thread timestamp
        if conversation_id in current_thread_mapping:
            # Remove old mapping and add new one
            current_thread_mapping.pop(conversation_id)
            current_thread_mapping = update_thread_mapping(event['ts'], openai_thread_id)
            logger.info(f"Updated thread mapping: {conversation_id} -> {event['ts']}")
        logger.info(f"Started new thread: {event['ts']}")

@slack_app.event("app_mention")
def handle_mention(event, say):
    logger.info(f"Bot mentioned: {event.get('text', '')[:100]}...")
    process_message(event, say)

@slack_app.event("message")
def handle_message(event, say):
    # Skip messages from bots (including our own) to prevent loops
    if event.get('bot_id'):
        return
    
    # Handle direct messages (always respond in DMs)
    if event.get('channel_type') == 'im':
        logger.info(f"Direct message received: {event.get('text', '')[:100]}...")
        process_message(event, say)
        return
    
    # Handle thread replies in channels (only if we've already participated in this thread)
    elif event.get('thread_ts'):
        thread_id = event['thread_ts']
        current_thread_mapping = get_thread_mapping()
        if thread_id in current_thread_mapping:
            # This is a reply in a thread where we've already participated
            logger.info(f"Thread reply received: {event.get('text', '')[:100]}...")
            process_message(event, say)
        # If thread_id not in thread_mapping, ignore it (not our conversation)
    
    # For regular channel messages without thread_ts, ignore them
    # (only mentions should trigger responses in channels)

flask_app = Flask(__name__)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    flask_app.run(port=3000)