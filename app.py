from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request
import openai
import os
import logging
import re

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

# Store thread to OpenAI thread mapping for context retention
import json
import tempfile
import fcntl

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

def process_message(event, say):
    """Common function to process messages from both mentions and DMs"""
    user_message = event['text']
    
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
        
        # Get the assistant's response
        messages = openai.beta.threads.messages.list(thread_id=openai_thread_id)
        assistant_message = messages.data[0].content[0].text.value
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        say("I'm sorry, I encountered an error processing your request. Please try again.")
        return
    
    # Clean up citations in the response
    cleaned_message = clean_citations(assistant_message)
    
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