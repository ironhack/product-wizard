from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request
import openai
import os
import logging

# Set up logging
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
thread_mapping = {}

def process_message(event, say):
    """Common function to process messages from both mentions and DMs"""
    user_message = event['text']
    
    # Determine the conversation thread
    if event.get('thread_ts'):
        # This is a reply in a thread - use the thread timestamp as the conversation ID
        conversation_id = event['thread_ts']
        logger.info(f"Thread reply detected. Thread ID: {conversation_id}")
    else:
        # This is a new message - use the message timestamp as the conversation ID
        conversation_id = event['ts']
        logger.info(f"New conversation. Message ID: {conversation_id}")
    
    logger.info(f"Current thread_mapping keys: {list(thread_mapping.keys())}")
    
    # Get or create OpenAI thread for this Slack thread
    if conversation_id not in thread_mapping:
        # Create new OpenAI thread for this Slack thread
        openai_thread = openai.beta.threads.create()
        thread_mapping[conversation_id] = openai_thread.id
        logger.info(f"Created new OpenAI thread: {openai_thread.id} for conversation: {conversation_id}")
    else:
        # Use existing OpenAI thread for this Slack thread
        openai_thread_id = thread_mapping[conversation_id]
        logger.info(f"Using existing OpenAI thread: {openai_thread_id} for conversation: {conversation_id}")
    
    # Add the user message to the OpenAI thread
    openai.beta.threads.messages.create(
        thread_id=thread_mapping[conversation_id],
        role="user",
        content=user_message
    )
    
    # Run the assistant
    run = openai.beta.threads.runs.create(
        thread_id=thread_mapping[conversation_id],
        assistant_id=ASSISTANT_ID
    )
    
    # Wait for the run to complete
    while run.status == "queued" or run.status == "in_progress":
        run = openai.beta.threads.runs.retrieve(
            thread_id=thread_mapping[conversation_id],
            run_id=run.id
        )
    
    # Get the assistant's response
    messages = openai.beta.threads.messages.list(thread_id=thread_mapping[conversation_id])
    assistant_message = messages.data[0].content[0].text.value
    
    # Reply in the same thread if this was a thread reply, otherwise start a new thread
    if event.get('thread_ts'):
        say(assistant_message, thread_ts=event['thread_ts'])
        logger.info(f"Replied in thread: {event['thread_ts']}")
    else:
        # When starting a new thread, we need to map the new thread ID back to the original conversation
        # The new thread ID will be the bot's response timestamp
        new_thread_ts = event['ts']
        logger.info(f"Starting new thread with ID: {new_thread_ts}")
        # Don't add this to mapping - the original conversation_id should remain the key
        say(assistant_message, thread_ts=event['ts'])
        logger.info(f"Started new thread: {event['ts']}")
        logger.info(f"Thread mapping after response: {list(thread_mapping.keys())}")

@slack_app.event("app_mention")
def handle_mention(event, say):
    logger.info(f"App mention event received: {event.get('text', '')}")
    process_message(event, say)

@slack_app.event("message")
def handle_message(event, say):
    logger.info(f"Message event received - Channel: {event.get('channel')}, Thread: {event.get('thread_ts')}, Type: {event.get('channel_type')}, Text: {event.get('text', '')[:50]}...")
    
    # Skip messages from bots (including our own) to prevent loops
    if event.get('bot_id'):
        logger.info("Skipping bot message")
        return
    
    # Handle direct messages (always respond in DMs)
    if event.get('channel_type') == 'im':
        logger.info("Processing direct message")
        process_message(event, say)
        return
    
    # Handle thread replies in channels (only if we've already participated in this thread)
    elif event.get('thread_ts'):
        thread_id = event['thread_ts']
        logger.info(f"Thread reply detected. Thread ID: {thread_id}, In mapping: {thread_id in thread_mapping}")
        logger.info(f"Available thread mappings: {list(thread_mapping.keys())}")
        if thread_id in thread_mapping:
            # This is a reply in a thread where we've already participated
            logger.info("Processing thread reply")
            process_message(event, say)
        else:
            logger.info("Thread not in mapping, ignoring")
        # If thread_id not in thread_mapping, ignore it (not our conversation)
    
    # For regular channel messages without thread_ts, ignore them
    # (only mentions should trigger responses in channels)
    else:
        logger.info("Regular channel message, ignoring")

flask_app = Flask(__name__)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    flask_app.run(port=3000)