"""
Verification Nodes

Nodes for coverage classification, coverage verification, and faithfulness verification in the RAG workflow.
"""

import logging
import re

from src.state import RAGState
from src.config import (
    COVERAGE_CLASSIFICATION_PROMPT,
    COVERAGE_VERIFICATION_PROMPT,
    FAITHFULNESS_VERIFICATION_PROMPT,
    PROGRAM_SYNONYMS,
)
from src.utils import call_openai_json
from src.slack_helpers import send_slack_update


logger = logging.getLogger(__name__)


def coverage_classification_node(state: RAGState) -> RAGState:
    """
    Detect if query is asking about curriculum coverage.
    """
    logger.info("=== Coverage Classification Node ===")
    send_slack_update(state, "Checking if this is a coverage question")

    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    query_intent = state.get("query_intent", "general_info")

    # Quick heuristic check first
    coverage_keywords = ["does", "is", "include", "cover", "teach", "contain", "have"]
    has_coverage_keyword = any(kw in enhanced_query.lower() for kw in coverage_keywords)

    if not has_coverage_keyword and query_intent != "coverage":
        return {
            **state,
            "is_coverage_question": False
        }

    # AI classification - use faster model for classification tasks
    user_prompt = f"""
Query: "{enhanced_query}"
Query Intent: {query_intent}

Is this a curriculum coverage question (asking if a program includes/teaches specific topics)?
Return JSON: {{"is_coverage_question": true/false, "reasoning": "explanation"}}
"""

    result = call_openai_json(COVERAGE_CLASSIFICATION_PROMPT, user_prompt, model="gpt-4o-mini", timeout=15)
    is_coverage = result.get("is_coverage_question", False)

    logger.info(f"Coverage Question: {is_coverage}")

    return {
        **state,
        "is_coverage_question": is_coverage
    }


def coverage_verification_node(state: RAGState) -> RAGState:
    """
    Verify if topic is explicitly present in retrieved documents.
    """
    logger.info("=== Coverage Verification Node ===")
    send_slack_update(state, "Verifying topic presence")

    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    filtered_docs = state.get("filtered_docs", [])
    detected_programs = state.get("detected_programs", [])
    query_intent = state.get("query_intent", "general_info")

    # Compile document content
    # Include full chunk content - low usage volume makes cost negligible, completeness is more important
    docs_content = "\n\n---\n\n".join([
        f"Source: {doc.get('source', 'unknown')}\n{doc.get('content', '')}"
        for doc in filtered_docs[:10]
    ])

    user_prompt = f"""
Query: "{enhanced_query}"
Programs: {detected_programs}

Retrieved Documents:
{docs_content}

Verify if the queried topic is explicitly mentioned in these documents.
Return JSON: {{"is_present": true/false, "topic": "extracted topic", "evidence": "quote from docs if present"}}
"""

    # Use faster model for verification (classification task)
    result = call_openai_json(COVERAGE_VERIFICATION_PROMPT, user_prompt, model="gpt-4o-mini", timeout=20)

    coverage_verification = {
        "is_present": result.get("is_present", False),
        "topic": result.get("topic", ""),
        "evidence": result.get("evidence", "")
    }

    logger.info(f"Coverage Verification: {coverage_verification}")

    return {
        **state,
        "coverage_verification": coverage_verification
    }


def faithfulness_verification_node(state: RAGState) -> RAGState:
    """
    Verify that generated answer is grounded in retrieved documents.
    - Detect hallucinations
    - Score faithfulness
    - Flag violations
    """
    logger.info("=== Faithfulness Verification Node ===")
    send_slack_update(state, "Verifying answer accuracy")

    generated_response = state.get("generated_response", "")
    filtered_docs = state.get("filtered_docs", [])
    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    query_intent = state.get("query_intent", "general_info")

    if not generated_response or not filtered_docs:
        return {
            **state,
            "faithfulness_score": 0.0,
            "is_grounded": False,
            "is_fallback": True,
            "faithfulness_violations": ["No response or documents to verify"]
        }

    # Quick heuristic check for obvious fallbacks (very short responses)
    if len(generated_response) < 50:
        return {
            **state,
            "faithfulness_score": 0.0,
            "is_grounded": False,
            "is_fallback": True,
            "faithfulness_violations": ["Response too short to be substantive"]
        }

    # Compile retrieved documents for verification
    # Include full content for certification queries to ensure proper verification
    # Optimized: Reduced content limit and doc count for faster processing
    max_docs_for_verification = 6 if query_intent == "certification" else 6
    # Include full chunk content - low usage volume makes cost negligible, completeness is more important
    docs_text = "\n\n".join([
        f"[{doc.get('source', 'unknown')}]\n{doc.get('content', '')}"
        for doc in filtered_docs[:max_docs_for_verification]
    ])

    logger.debug(f"Faithfulness verification: checking {len(filtered_docs)} docs, full content included")

    user_prompt = f"""
User Query: "{enhanced_query}"

Retrieved Documents:
{docs_text}

Generated Answer:
{generated_response}

Verify that every claim in the generated answer is grounded in the retrieved documents.
"""

    # Use faster model for faithfulness verification (can use mini for speed)
    result = call_openai_json(FAITHFULNESS_VERIFICATION_PROMPT, user_prompt, model="gpt-4o-mini", timeout=25)

    faithfulness_score = result.get("faithfulness_score", 0.5)
    is_grounded = result.get("is_grounded", False)
    is_fallback = result.get("is_fallback", False)
    violations = result.get("violations", [])
    recommendation = result.get("recommendation", "approve")

    # Check for critical violations that should block responses regardless of score
    # For comparison queries, cross-contamination is expected (comparing multiple programs)
    # For technical_detail queries, be less strict (they synthesize information)
    # Only block on truly critical violations (severity="critical") for these query types
    query_intent = state.get("query_intent", "general_info")
    if query_intent == "comparison":
        critical_violation_types = ["fabricated_fact", "wrongnumbers"]
        required_severity = ["critical"]  # Only block on critical severity for comparisons
    elif query_intent == "technical_detail":
        critical_violation_types = ["fabricated_fact", "wrongnumbers"]
        required_severity = ["critical"]  # Only block on critical severity for technical_detail
    else:
        critical_violation_types = ["fabricated_fact", "cross_contamination", "wrongnumbers"]
        required_severity = ["critical", "major"]

    has_critical_violations = any(
        v.get("type") in critical_violation_types and v.get("severity") in required_severity
        for v in violations
    )

    logger.info(f"Faithfulness: {faithfulness_score:.2f} | Grounded: {is_grounded} | Fallback: {is_fallback} | Violations: {len(violations)} | Critical: {has_critical_violations}")

    return {
        **state,
        "faithfulness_score": faithfulness_score,
        "is_grounded": is_grounded,
        "is_fallback": is_fallback,
        "has_critical_violations": has_critical_violations,
        "faithfulness_violations": [v.get("claim", "") for v in violations] if violations else []
    }
