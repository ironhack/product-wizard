"""
Unified Triage Node

One structured LLM call performs what previously took four separate calls:
query enhancement, program detection, cohort/calendar classification, and
coverage-question classification. Strict structured output enforces the shape;
deterministic backstops (breakdown/portfolio flags, cohort filter regexes)
still run in code. Falls back to the legacy multi-call path if the call fails.
"""

import logging
import json
import time

from src.state import RAGState
from src.config import UNIFIED_TRIAGE_PROMPT, PROGRAM_SYNONYMS
from src.utils import (
    call_openai_json,
    format_conversation_history,
    is_breakdown_request,
    is_portfolio_wide_query,
)
from src.slack_helpers import send_slack_update

logger = logging.getLogger(__name__)

_VALID_INTENTS = {
    "coverage", "comparison", "technical_detail", "duration",
    "certification", "requirements", "career_outcome", "general_info",
}

_TRIAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "enhanced_query": {"type": "string"},
        "query_intent": {
            "type": "string",
            "enum": sorted(_VALID_INTENTS),
        },
        "ambiguity_score": {"type": "number"},
        "detected_programs": {
            "type": "array",
            "items": {"type": "string"},
        },
        "is_cohort_calendar_question": {"type": "boolean"},
        "cohort_filters": {
            "type": "object",
            "properties": {
                "track": {"type": ["string", "null"]},
                "type": {"type": ["string", "null"]},
                "month": {"type": ["string", "null"]},
                "year": {"type": ["integer", "null"]},
                "future_only": {"type": "boolean"},
            },
            "required": ["track", "type", "month", "year", "future_only"],
            "additionalProperties": False,
        },
        "is_coverage_question": {"type": "boolean"},
        "coverage_topic": {"type": ["string", "null"]},
    },
    "required": [
        "enhanced_query", "query_intent", "ambiguity_score", "detected_programs",
        "is_cohort_calendar_question", "cohort_filters", "is_coverage_question",
        "coverage_topic",
    ],
    "additionalProperties": False,
}


def _program_reference() -> str:
    """Compact program id/alias reference for the triage prompt."""
    lines = []
    for pid, info in PROGRAM_SYNONYMS.items():
        aliases = ", ".join(info.get("aliases", [])[:6])
        lines.append(f"- {pid} (code {info.get('code', '?')}): {info.get('display_name', pid)} | aliases: {aliases}")
    return "\n".join(lines)


def unified_triage_node(state: RAGState) -> RAGState:
    """
    Single-call triage. Sets: enhanced_query, query_intent, ambiguity_score,
    detected_programs, is_cohort_calendar_question, cohort_filters,
    is_coverage_question (+ topic hint), and the deterministic query-shape flags.
    """
    logger.info("=== Unified Triage Node ===")
    start_time = time.perf_counter()

    query = state.get("query", "")
    conversation_history = state.get("conversation_history", [])
    conversation_stage = state.get("conversation_stage", "initial")
    conv_context = format_conversation_history(conversation_history, limit=5)

    user_prompt = f"""
Conversation Stage: {"follow-up message within an existing Slack thread" if conversation_stage == "follow_up" else "new question kicking off a Slack thread"}

Original Query: "{query}"

Conversation Context:
{conv_context}

Program ids and aliases:
{_program_reference()}

Analyze the query and return the triage JSON.
"""

    result = call_openai_json(
        UNIFIED_TRIAGE_PROMPT,
        user_prompt,
        timeout=20,
        schema=_TRIAGE_SCHEMA,
        schema_name="query_triage",
    )

    if not result:
        # Legacy fallback: run the old multi-call path so one failed API call
        # never takes the bot down
        logger.warning("Unified triage failed; falling back to legacy multi-call path")
        from src.nodes.parallel_query_nodes import parallel_query_processing_node
        from src.nodes.cohort_calendar_nodes import cohort_calendar_classification_node
        fallback_state = parallel_query_processing_node(state)
        fallback_state = cohort_calendar_classification_node(fallback_state)
        return {**fallback_state, "triage_used": False}

    enhanced_query = (result.get("enhanced_query") or query).strip() or query
    query_intent = result.get("query_intent", "general_info")
    if query_intent not in _VALID_INTENTS:
        query_intent = "general_info"
    detected_programs = [p for p in result.get("detected_programs", []) if p in PROGRAM_SYNONYMS]

    cohort_filters = result.get("cohort_filters") or {}
    is_cohort = bool(result.get("is_cohort_calendar_question", False))

    # Deterministic query-shape flags (same backstops as before)
    is_breakdown = is_breakdown_request(query) or is_breakdown_request(enhanced_query)
    is_portfolio = is_portfolio_wide_query(query) or is_portfolio_wide_query(enhanced_query)

    # Breakdown/overview requests are never coverage questions
    is_coverage = bool(result.get("is_coverage_question", False)) and not is_breakdown

    duration = time.perf_counter() - start_time
    logger.info(
        f"Triage in {duration:.2f}s | intent={query_intent} | programs={detected_programs} | "
        f"cohort={is_cohort} | coverage={is_coverage} | breakdown={is_breakdown} | portfolio={is_portfolio}"
    )

    return {
        **state,
        "enhanced_query": enhanced_query,
        "query_intent": query_intent,
        "ambiguity_score": result.get("ambiguity_score", 0.5),
        "detected_programs": detected_programs,
        "namespace_filter": None,
        "is_cohort_calendar_question": is_cohort,
        "cohort_filters": cohort_filters if is_cohort else {},
        "is_coverage_question": is_coverage,
        "triage_coverage_topic": result.get("coverage_topic") or "",
        "is_breakdown_request": is_breakdown,
        "is_portfolio_wide": is_portfolio,
        "triage_used": True,
    }
