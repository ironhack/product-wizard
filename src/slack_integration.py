"""
Slack integration handlers for app mentions and direct messages.
Handles event processing for the RAG bot in Slack channels and DMs.
"""

import logging
import re
from typing import Dict

from src.config import SLACK_BOT_TOKEN
from src.workflow import rag_workflow

# ---------------- Slack Helpers ----------------
from src.slack_helpers import (
    _already_processed,
    get_conversation_history,
    set_slack_say_function,
    clear_slack_say_function,
    _current_progress_message_ts,
)

# Configure logging
logger = logging.getLogger(__name__)


def handle_mention(event, say):
    """Handle @mentions in Slack."""
    if _already_processed(event):
        return

    text = event.get("text", "")
    user_id = event.get("user", "unknown")
    channel = event.get("channel", "")
    event_ts = event.get("ts") or event.get("event_ts", "")
    thread_ts = event.get("thread_ts", event_ts)
    channel_type = event.get("channel_type")

    # Remove bot mention from text
    query = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
    # Remove bot summon phrases (case-insensitive)
    query = re.sub(r'^product\s+wizard\s*', '', query, flags=re.IGNORECASE).strip()

    logger.info(f"Processing mention from {user_id} in {channel} ({channel_type}): {query}")

    try:
        # Set the current say function for progress updates
        set_slack_say_function(say)

        # Retrieve conversation history from the thread
        conversation_history = get_conversation_history(
            channel,
            thread_ts,
            limit=10,
            latest_ts=event_ts
        )
        prior_message_count = len(conversation_history)
        is_follow_up = prior_message_count > 0
        conversation_stage = "follow_up" if is_follow_up else "initial"
        logger.info(
            "Retrieved %s prior messages (conversation_stage=%s)",
            prior_message_count,
            conversation_stage
        )

        # Run the RAG workflow
        config = {"configurable": {"thread_id": thread_ts}}
        initial_state = {
            "query": query,
            "conversation_history": conversation_history,
            "is_follow_up": is_follow_up,
            "conversation_stage": conversation_stage,
            "iteration_count": 0,
            "metadata": {
                "slack_user_id": user_id,
                "slack_channel_type": channel_type,
                "is_follow_up": is_follow_up,
                "conversation_stage": conversation_stage,
                "prior_message_count": prior_message_count
            },
            # Slack context for progress updates (no say function to avoid serialization)
            "slack_channel": channel,
            "slack_thread_ts": thread_ts
        }

        result = rag_workflow.invoke(initial_state, config)

        response = result.get("final_response", "I encountered an error processing your question.")

        # Update the progress message with the final answer
        if _current_progress_message_ts:
            try:
                from slack_sdk import WebClient
                client = WebClient(token=SLACK_BOT_TOKEN)
                # Note: Don't include thread_ts when updating a reply in a thread
                # The ts parameter is sufficient to identify the message to update
                client.chat_update(
                    channel=channel,
                    ts=_current_progress_message_ts,
                    text=response
                )
            except Exception as e:
                logger.warning(f"Failed to update progress message with final answer: {e}")
                # Fallback to sending new message
                say(text=response, thread_ts=thread_ts, channel=channel)
        else:
            # Send response in thread
            say(text=response, thread_ts=thread_ts, channel=channel)

    except Exception as e:
        logger.error(f"Error processing mention: {e}")
        say(text="I encountered an error processing your question. Please try again.", thread_ts=thread_ts, channel=channel)
    finally:
        # Clean up the say function
        clear_slack_say_function()


def handle_message(event, say):
    """Handle DMs."""
    if event.get("subtype") or event.get("bot_id"):
        return

    channel_type = event.get("channel_type")
    if channel_type not in {"im", "mpim"}:
        logger.debug("Ignoring message in channel_type=%s without mention", channel_type)
        return

    if _already_processed(event):
        return

    query = event.get("text", "")
    # Remove bot summon phrases (case-insensitive)
    query = re.sub(r'^product\s+wizard\s*', '', query, flags=re.IGNORECASE).strip()
    channel = event.get("channel", "")
    event_ts = event.get("ts") or event.get("event_ts", "")
    thread_ts = event.get("thread_ts", event_ts)
    user_id = event.get("user", "unknown")

    logger.info(f"Processing DM from {user_id} ({channel_type}): {query}")

    try:
        # Set the current say function for progress updates
        set_slack_say_function(say)

        # Retrieve conversation history from the thread
        conversation_history = get_conversation_history(
            channel,
            thread_ts,
            limit=10,
            latest_ts=event_ts
        )
        prior_message_count = len(conversation_history)
        is_follow_up = prior_message_count > 0
        conversation_stage = "follow_up" if is_follow_up else "initial"
        logger.info(
            "Retrieved %s prior messages in DM (conversation_stage=%s)",
            prior_message_count,
            conversation_stage
        )

        config = {"configurable": {"thread_id": thread_ts}}
        initial_state = {
            "query": query,
            "conversation_history": conversation_history,
            "is_follow_up": is_follow_up,
            "conversation_stage": conversation_stage,
            "iteration_count": 0,
            "metadata": {
                "slack_user_id": user_id,
                "slack_channel_type": channel_type,
                "is_follow_up": is_follow_up,
                "conversation_stage": conversation_stage,
                "prior_message_count": prior_message_count
            },
            # Slack context for progress updates (no say function to avoid serialization)
            "slack_channel": channel,
            "slack_thread_ts": thread_ts
        }

        result = rag_workflow.invoke(initial_state, config)
        response = result.get("final_response", "I encountered an error processing your question.")

        # Update the progress message with the final answer
        if _current_progress_message_ts:
            try:
                from slack_sdk import WebClient
                client = WebClient(token=SLACK_BOT_TOKEN)
                client.chat_update(
                    channel=channel,
                    ts=_current_progress_message_ts,
                    text=response
                )
            except Exception as e:
                logger.warning(f"Failed to update progress message with final answer: {e}")
                # Fallback to sending new message
                say(text=response, channel=channel)
        else:
            # Send response
            say(text=response, channel=channel)

    except Exception as e:
        logger.error(f"Error processing DM: {e}")
        say(text="I encountered an error processing your question. Please try again.", channel=channel)
    finally:
        # Clean up the say function
        clear_slack_say_function()
