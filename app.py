from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request
import openai
import os
import logging
import re

# Set up logging - only show warnings and errors by default
logging.basicConfig(level=logging.WARNING)
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

def clean_citations(response_text):
    """Clean up citations to show just the filename"""
    # Pattern to match citations like 【4:1†AI Engineering bootcamp_2025_07.pdf】 or 【4:9†source】
    citation_pattern = r'【\d+:\d+†([^】]+)】'
    
    def replace_citation(match):
        citation_content = match.group(1)
        # If it's just "source", remove it entirely
        if citation_content.lower() == 'source':
            return ''
        # Otherwise, show the filename in parentheses
        return f'({citation_content})'
    
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
    else:
        # This is a new message - use the message timestamp as the conversation ID
        conversation_id = event['ts']
    
    # Get or create OpenAI thread for this Slack thread
    if conversation_id not in thread_mapping:
        # Create new OpenAI thread for this Slack thread
        openai_thread = openai.beta.threads.create()
        thread_mapping[conversation_id] = openai_thread.id
    else:
        # Use existing OpenAI thread for this Slack thread
        openai_thread_id = thread_mapping[conversation_id]
    
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
    
    # Clean up citations in the response
    cleaned_message = clean_citations(assistant_message)
    
    # Reply in the same thread if this was a thread reply, otherwise start a new thread
    if event.get('thread_ts'):
        say(cleaned_message, thread_ts=event['thread_ts'])
    else:
        # When starting a new thread, we need to map the new thread ID back to the original conversation
        # The new thread ID will be the bot's response timestamp
        new_thread_ts = event['ts']
        # Don't add this to mapping - the original conversation_id should remain the key
        say(cleaned_message, thread_ts=event['ts'])

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
        if thread_id in thread_mapping:
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