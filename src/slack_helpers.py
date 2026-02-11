"""
Slack helper functions for event deduplication and progress updates.
Includes conversation history retrieval, event deduplication, and Slack message management.
"""

import logging
import re
import threading
from collections import deque
from typing import Dict, List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from src.config import SLACK_BOT_TOKEN, slack_web_client
from src.state import RAGState

# Configure logging
logger = logging.getLogger(__name__)


# ---------------- Slack Event De-duplication ----------------
SEEN_EVENT_IDS: deque = deque(maxlen=512)
SEEN_ENVELOPE_IDS: deque = deque(maxlen=1024)


def _build_event_dedupe_key(event: Dict) -> Optional[str]:
    """Build a stable dedupe key for Slack events."""
    try:
        if not isinstance(event, dict):
            return None
        ev_id = event.get('event_id')
        if ev_id:
            return f"id:{ev_id}"
        client_msg_id = event.get('client_msg_id')
        if client_msg_id:
            ev_type = str(event.get('type') or '')
            return f"cmid:{ev_type}:{client_msg_id}"
        channel = str(event.get('channel', '') or '')
        ts = event.get('event_ts') or event.get('ts')
        ev_type = str(event.get('type') or '')
        thread_ts = event.get('thread_ts') or ''
        if channel and ts:
            return f"ch_ts:{ev_type}:{channel}:{ts}:{thread_ts}"
        return None
    except Exception:
        return None


def get_conversation_history(
    channel: str,
    thread_ts: str,
    limit: int = 10,
    latest_ts: Optional[str] = None
) -> List[BaseMessage]:
    """
    Retrieve conversation history from Slack thread.
    Returns a list of BaseMessage objects for use in RAG pipeline.

    If ``latest_ts`` is provided, the corresponding message is excluded so the
    active Slack event can be handled separately.

    Note: This requires the following Slack app scopes:
    - channels:history (for public channels)
    - groups:history (for private channels)
    - mpim:history (for multi-party direct messages)
    - im:history (for direct messages)
    """
    try:
        if not slack_web_client:
            logger.warning("Slack web client not available")
            return []

        # Get conversation history from the thread
        response = slack_web_client.conversations_replies(
            channel=channel,
            ts=thread_ts,
            limit=limit
        )

        messages = []
        for msg in response.get("messages", []):
            msg_ts = msg.get("ts")

            # Skip the most recent Slack event to avoid duplicating the active query
            if latest_ts and msg_ts == latest_ts:
                continue

            text = msg.get("text", "")
            user_id = msg.get("user", "")
            bot_id = msg.get("bot_id", "")

            # Skip empty messages
            if not text.strip():
                continue

            # Remove bot mentions from user messages
            clean_text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
            if not clean_text:
                continue

            # Determine if it's a user message or bot message
            if bot_id or user_id == "USLACKBOT":
                # Bot message
                messages.append(AIMessage(content=clean_text))
            else:
                # User message
                messages.append(HumanMessage(content=clean_text))

        # Return messages in chronological order (oldest first)
        return messages

    except Exception as e:
        logger.warning(f"Failed to retrieve conversation history: {e}")

        # Check if it's a permissions issue
        if "missing_scope" in str(e):
            logger.warning("Missing Slack API scopes for conversation history. Required scopes: channels:history, groups:history, mpim:history, im:history")

        return []


def _already_processed(event: Dict) -> bool:
    """Check if event was already processed."""
    try:
        key = _build_event_dedupe_key(event)
        if not key:
            return False
        if key in SEEN_EVENT_IDS:
            logger.info(f"Duplicate event suppressed: {key}")
            return True
        SEEN_EVENT_IDS.append(key)
        return False
    except Exception:
        return False


# ---------------- Slack Update Helper ----------------

# Global variables to store the current say function and progress message (avoid serialization issues)
_current_say_function = None
_current_progress_message_ts = None
_progress_steps = [
    "🔍 Analyzing your question...",
    "🎯 Detecting program focus...",
    "📚 Searching curriculum documents...",
    "🔍 Filtering best matches...",
    "⚖️ Assessing document relevance...",
    "❓ Checking if this is a coverage question...",
    "✅ Verifying topic presence...",
    "🤖 Generating response...",
    "🔍 Verifying answer accuracy...",
    "✅ Finalizing response..."
]
_current_step = 0

# Lock for thread-safe access to _current_progress_message_ts and _current_step
_message_lock = threading.Lock()


def set_slack_say_function(say_func):
    """Set the current Slack say function for updates."""
    global _current_say_function, _current_progress_message_ts, _current_step
    with _message_lock:
        _current_say_function = say_func
        _current_progress_message_ts = None
        _current_step = 0


def clear_slack_say_function():
    """Clear the current Slack say function."""
    global _current_say_function, _current_progress_message_ts, _current_step
    with _message_lock:
        _current_say_function = None
        _current_progress_message_ts = None
        _current_step = 0


def send_slack_update(state: RAGState, step_name: str):
    """Safely send/update Slack progress message with step numbering."""
    try:
        if _current_say_function and state.get("slack_channel"):
            global _current_step, _current_progress_message_ts

            # Find the step index and update _current_step under lock
            with _message_lock:
                step_index = next((i for i, step in enumerate(_progress_steps) if step_name in step), _current_step)
                _current_step = step_index
                current_progress_message_ts = _current_progress_message_ts

            # Create progress message with numbering (outside lock - no shared state)
            total_steps = len(_progress_steps)
            progress_text = f"({_current_step + 1}/{total_steps}) {_progress_steps[_current_step]}"

            if current_progress_message_ts:
                # Update existing message using Slack Web API
                try:
                    if not slack_web_client:
                        logger.warning("Slack web client not available for update")
                        # Fallback to sending new message
                        response = _current_say_function(
                            text=progress_text,
                            thread_ts=state.get("slack_thread_ts"),
                            channel=state.get("slack_channel")
                        )
                        # Try to extract timestamp from response and update under lock
                        new_ts = None
                        if hasattr(response, 'get') and response.get('ts'):
                            new_ts = response.get('ts')
                        elif hasattr(response, 'ts'):
                            new_ts = response.ts
                        if new_ts:
                            with _message_lock:
                                _current_progress_message_ts = new_ts
                    else:
                        slack_web_client.chat_update(
                            channel=state.get("slack_channel"),
                            ts=current_progress_message_ts,
                            text=progress_text
                        )
                except Exception as update_error:
                    logger.warning(f"Failed to update message, sending new one: {update_error}")
                    # Fallback to sending new message
                    response = _current_say_function(
                        text=progress_text,
                        thread_ts=state.get("slack_thread_ts"),
                        channel=state.get("slack_channel")
                    )
                    # Try to extract timestamp from response and update under lock
                    new_ts = None
                    if hasattr(response, 'get') and response.get('ts'):
                        new_ts = response.get('ts')
                    elif hasattr(response, 'ts'):
                        new_ts = response.ts
                    if new_ts:
                        with _message_lock:
                            _current_progress_message_ts = new_ts
            else:
                # Send new message and store timestamp
                response = _current_say_function(
                    text=progress_text,
                    thread_ts=state.get("slack_thread_ts"),
                    channel=state.get("slack_channel")
                )
                # Try to extract timestamp from response and update under lock
                new_ts = None
                if hasattr(response, 'get') and response.get('ts'):
                    new_ts = response.get('ts')
                elif hasattr(response, 'ts'):
                    new_ts = response.ts
                if new_ts:
                    with _message_lock:
                        _current_progress_message_ts = new_ts

    except Exception as e:
        logger.warning(f"Failed to send Slack update: {e}")
