"""
Query Processing Nodes

Nodes for query enhancement and program detection in the RAG workflow.
"""

import logging
import json
import time

from src.state import RAGState
from src.config import (
    QUERY_ENHANCEMENT_PROMPT,
    PROGRAM_DETECTION_PROMPT,
    PROGRAM_SYNONYMS,
)
from src.utils import (
    format_conversation_history,
    call_openai_json,
)


logger = logging.getLogger(__name__)


def query_enhancement_node(state: RAGState) -> RAGState:
    """
    Disambiguate and enhance user query.
    - Clarify vague questions using conversation context
    - Classify query intent
    - Score ambiguity level
    """
    logger.info("=== Query Enhancement Node ===")

    start_time = time.perf_counter()

    query = state.get("query", "")
    conversation_history = state.get("conversation_history", [])
    conversation_stage = state.get("conversation_stage", "initial")

    if conversation_stage == "follow_up":
        stage_description = "follow-up message within an existing Slack thread"
    else:
        stage_description = "new question kicking off a Slack thread"

    # Format conversation context
    conv_context = format_conversation_history(conversation_history, limit=5)

    user_prompt = f"""
Conversation Stage: {stage_description}

Original Query: "{query}"

Conversation Context:
{conv_context}

Analyze and enhance this query following the guidelines.
"""

    # Use faster model for query enhancement (can use mini for speed)
    result = call_openai_json(QUERY_ENHANCEMENT_PROMPT, user_prompt, model="gpt-4o-mini", timeout=15)

    enhanced_query = result.get("enhanced_query", query)
    query_intent = result.get("query_intent", "general_info")
    ambiguity_score = result.get("ambiguity_score", 0.5)

    logger.info(f"Enhanced: '{enhanced_query}' | Intent: {query_intent} | Ambiguity: {ambiguity_score}")

    duration = time.perf_counter() - start_time
    logger.info(f"query_enhancement_node completed in {duration:.2f}s")

    return {
        **state,
        "enhanced_query": enhanced_query,
        "query_intent": query_intent,
        "ambiguity_score": ambiguity_score
    }


def program_detection_node(state: RAGState) -> RAGState:
    """
    Detect which programs the query is about.
    - Extract program names
    - Map synonyms
    - Build namespace metadata filter
    """
    logger.info("=== Program Detection Node ===")

    start_time = time.perf_counter()

    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    conversation_history = state.get("conversation_history", [])
    query_intent = state.get("query_intent", "general_info")

    conv_context = format_conversation_history(conversation_history, limit=3)

    user_prompt = f"""
Query: "{enhanced_query}"
Query Intent: {query_intent}

Conversation Context:
{conv_context}

Program Synonyms Available:
{json.dumps(PROGRAM_SYNONYMS, indent=2)}

Detect which programs this query is about and build appropriate namespace filter.
"""

    # Use faster model for program detection (classification task)
    result = call_openai_json(PROGRAM_DETECTION_PROMPT, user_prompt, model="gpt-4o-mini", timeout=15)

    detected_programs = result.get("detected_programs", [])
    namespace_filter = result.get("namespace_filter")
    confidence = result.get("confidence", 0.5)

    logger.info(f"Detected Programs: {detected_programs} | Confidence: {confidence}")
    logger.info(f"Namespace Filter: {namespace_filter}")

    duration = time.perf_counter() - start_time
    logger.info(f"program_detection_node completed in {duration:.2f}s")

    return {
        **state,
        "detected_programs": detected_programs,
        "namespace_filter": namespace_filter
    }
