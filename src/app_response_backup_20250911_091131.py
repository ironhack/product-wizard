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

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Vector Store ID for file search
VECTOR_STORE_ID = os.environ.get("OPENAI_VECTOR_STORE_ID", "vs_68c14625e8d88191a27acb8a3845a706")

# Load the master prompt
def load_master_prompt():
    try:
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_path = os.path.join(script_dir, 'assistant_config', 'MASTER_PROMPT.md')
        with open(prompt_path, 'r') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading master prompt: {e}")
        return "You are a helpful assistant for Ironhack course information."

MASTER_PROMPT = load_master_prompt()

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
            with open(self.cache_file, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
                try:
                    json.dump(cache, f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Error saving message cache: {str(e)}")
    
    def is_duplicate(self, message_id):
        """Check if message has been processed recently"""
        cache = self.load_cache()
        current_time = time.time()
        
        # Clean expired entries
        cache = {k: v for k, v in cache.items() if current_time - v < self.ttl_seconds}
        
        if message_id in cache:
            return True
        
        # Add new message
        cache[message_id] = current_time
        
        # Limit cache size
        if len(cache) > self.max_size:
            # Remove oldest entries
            sorted_items = sorted(cache.items(), key=lambda x: x[1])
            cache = dict(sorted_items[-self.max_size:])
        
        self.save_cache(cache)
        return False

# Initialize deduplication cache
dedup_cache = MessageDeduplicationCache()

# Conversation mapping to track previous_response_id for each Slack thread
# This replaces the OpenAI thread system
def load_conversation_mapping():
    """Load conversation mapping from file with file locking"""
    try:
        mapping_file = os.path.join(tempfile.gettempdir(), 'conversation_mapping.json')
        if os.path.exists(mapping_file):
            with open(mapping_file, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    return json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        logger.error(f"Error loading conversation mapping: {str(e)}")
    return {}

def save_conversation_mapping(mapping):
    """Save conversation mapping to file with file locking"""
    try:
        mapping_file = os.path.join(tempfile.gettempdir(), 'conversation_mapping.json')
        with open(mapping_file, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(mapping, f)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        logger.error(f"Error saving conversation mapping: {str(e)}")

def get_conversation_mapping():
    """Get current conversation mapping"""
    return load_conversation_mapping()

def update_conversation_mapping(conversation_id, conversation_data):
    """Update conversation mapping for a specific conversation"""
    mapping = load_conversation_mapping()
    mapping[conversation_id] = conversation_data
    save_conversation_mapping(mapping)
    return mapping

def clean_citations(text):
    """Clean up citations for Slack display"""
    # Remove markdown link syntax but keep the text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Clean up any remaining citation artifacts
    text = re.sub(r'\[([^\]]+)\]', r'\1', text)
    return text

def convert_markdown_to_slack(text):
    """Convert markdown formatting to Slack formatting"""
    # Convert bold **text** to *text*
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
    # Convert italic *text* to _text_
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'_\1_', text)
    # Convert code blocks ```code``` to ```code```
    # (Slack handles this the same way)
    # Convert inline code `code` to `code`
    # (Slack handles this the same way)
    # Convert headers # Header to *Header*
    text = re.sub(r'^#+\s*(.+)$', r'*\1*', text, flags=re.MULTILINE)
    # Convert bullet points - item to • item
    text = re.sub(r'^-\s+', '• ', text, flags=re.MULTILINE)
    # Convert numbered lists 1. item to 1. item (keep as is)
    return text

@slack_app.event("app_mention")
def handle_mention(event, say):
    """Handle @mentions in channels"""
    process_message(event, say)

@slack_app.event("message")
def handle_message(event, say):
    """Handle direct messages"""
    # Only process if it's a DM (no channel in event)
    if "channel" not in event or event.get("channel_type") == "im":
        process_message(event, say)

def process_message(event, say):
    """Process incoming messages using Responses API"""
    user_message = event['text']
    
    # Get message ID for deduplication
    message_id = event.get('ts', str(time.time()))
    
    # Check for duplicates
    if dedup_cache.is_duplicate(message_id):
        logger.info(f"Duplicate message detected: {message_id}")
        return
    
    # Get conversation ID (thread or channel)
    conversation_id = event.get('thread_ts', event.get('channel'))
    
    logger.info(f"Processing message in conversation: {conversation_id}")
    logger.info(f"User message: {user_message}")
    
    # Get current conversation mapping
    current_conversation_mapping = get_conversation_mapping()
    if conversation_id not in current_conversation_mapping:
        conversation_data = {"previous_response_id": None}
        current_conversation_mapping = update_conversation_mapping(conversation_id, conversation_data)
    else:
        conversation_data = current_conversation_mapping[conversation_id]
    
    try:
        # Prepare the Responses API request parameters
        request_params = {
            "model": "gpt-4o",
            "input": user_message,
            "instructions": MASTER_PROMPT,
            "tools": [
                {
                    "type": "file_search",
                    "vector_store_ids": [VECTOR_STORE_ID]
                }
            ]
        }
        
        # Add previous response ID for conversation context
        if conversation_data.get("previous_response_id"):
            request_params["previous_response_id"] = conversation_data["previous_response_id"]
        
        logger.info("Making Responses API call...")
        start_time = time.time()
        
        # Make the Responses API call
        response = client.responses.create(**request_params)
        
        end_time = time.time()
        response_time = end_time - start_time
        logger.info(f"Response received in {response_time:.2f} seconds")
        
        # Extract the assistant's response
        assistant_message = "I apologize, but I couldn't generate a proper response."
        
        if response.output and len(response.output) > 0:
            # Look for the message output (not tool calls)
            for output_item in response.output:
                if hasattr(output_item, 'type') and output_item.type == 'message':
                    if hasattr(output_item, 'content') and len(output_item.content) > 0:
                        content = output_item.content[0]
                        if hasattr(content, 'text'):
                            assistant_message = content.text
                            break
        
        # Update conversation mapping with new response ID
        conversation_data["previous_response_id"] = response.id
        update_conversation_mapping(conversation_id, conversation_data)
        
        logger.info(f"Assistant response: {assistant_message[:100]}...")
        
    except Exception as e:
        logger.error(f"Error processing message with Responses API: {str(e)}")
        say("I'm sorry, I encountered an error processing your request. Please try again.")
        return
    
    # Clean up citations for Slack
    cleaned_message = clean_citations(assistant_message)
    
    # Convert markdown to Slack formatting
    slack_message = convert_markdown_to_slack(cleaned_message)
    
    # Reply in the same thread or channel
    try:
        say(slack_message, thread_ts=event.get('ts'))
        logger.info("Response sent successfully")
    except Exception as e:
        logger.error(f"Error sending response: {str(e)}")
        say("I'm sorry, I encountered an error sending the response. Please try again.")

# Flask app for Heroku
flask_app = Flask(__name__)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle Slack events"""
    return handler.handle(request)

@flask_app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "api": "responses"}

if __name__ == "__main__":
    flask_app.run(debug=True, port=int(os.environ.get("PORT", 3000)))