"""
Utility functions for RAG service.
Includes markdown conversion, OpenAI API calls, and conversation formatting.
"""

import json
import logging
import re
from typing import Dict, List

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from src.config import openai_client

# Configure logging
logger = logging.getLogger(__name__)


def convert_markdown_to_slack(text: str) -> str:
    """
    Convert markdown formatting to Slack-friendly formatting.
    - Headers (##, ###) -> Bold with newlines
    - **bold** -> *bold* (Slack uses single asterisk)
    - Markdown lists -> Slack-friendly lists with bullets
    - Code blocks -> Preserved with backticks
    - Links -> Slack link format
    """
    # Protect code blocks from being modified
    code_blocks = []
    def protect_code(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(code_blocks)-1}__"

    # Protect inline code
    inline_code = []
    def protect_inline_code(match):
        inline_code.append(match.group(0))
        return f"__INLINE_CODE_{len(inline_code)-1}__"

    # Protect code blocks (```code```)
    text = re.sub(r'```[\s\S]*?```', protect_code, text)

    # Protect inline code (`code`)
    text = re.sub(r'`([^`]+)`', protect_inline_code, text)

    # Remove markdown headers and convert to bold
    # Handle both ## and ### headers
    text = re.sub(r'^##+\s+(.+)$', r'*\1*', text, flags=re.MULTILINE)

    # Convert markdown bold (**text**) to Slack bold (*text*)
    # But be careful not to convert single asterisks that are already Slack formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'*\1*', text)

    # Convert markdown links [text](url) to Slack format <url|text>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<\2|\1>', text)

    # Convert markdown lists (- or *) to Slack bullets (•)
    # Handle both - and * list markers, but avoid converting asterisks in bold text
    text = re.sub(r'^[\s]*[-]\s+', '• ', text, flags=re.MULTILINE)
    # For asterisk lists, be more careful - only convert if it's at start of line with spaces
    text = re.sub(r'^[\s]+\*\s+', '• ', text, flags=re.MULTILINE)

    # Convert numbered lists (1. 2. etc.) to Slack format (1. 2. etc. - keep as is)
    # Slack supports numbered lists, so we can keep them

    # Remove excessive blank lines (more than 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Restore inline code
    for i, code in enumerate(inline_code):
        text = text.replace(f"__INLINE_CODE_{i}__", code)

    # Restore code blocks
    for i, code in enumerate(code_blocks):
        text = text.replace(f"__CODE_BLOCK_{i}__", code)

    # Clean up any remaining markdown artifacts
    text = text.strip()

    return text


def format_conversation_history(messages: List[BaseMessage], limit: int = 5) -> str:
    """Format conversation history for prompts."""
    if not messages:
        return "No previous conversation."

    recent_messages = messages[-limit:]
    formatted = []
    for msg in recent_messages:
        if isinstance(msg, HumanMessage):
            formatted.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            formatted.append(f"Assistant: {msg.content}")

    return "\n".join(formatted) if formatted else "No previous conversation."


def call_openai_json(system_prompt: str, user_prompt: str, model: str = "gpt-4o-mini", timeout: int = 30) -> Dict:
    """Call OpenAI API and parse JSON response.

    Args:
        system_prompt: System prompt for the API call
        user_prompt: User prompt for the API call
        model: Model to use (default: gpt-4o-mini for speed, use gpt-4o for complex tasks)
        timeout: Request timeout in seconds
    """
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            timeout=timeout
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"OpenAI JSON call failed: {e}")
        return {}


def call_openai_text(system_prompt: str, user_prompt: str, model: str = "gpt-4o", timeout: int = 60) -> str:
    """Call OpenAI API and get text response.

    Args:
        system_prompt: System prompt for the API call
        user_prompt: User prompt for the API call
        model: Model to use (default: gpt-4o for quality, use gpt-4o-mini for speed)
        timeout: Request timeout in seconds
    """
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            timeout=timeout
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI text call failed: {e}")
        return ""
