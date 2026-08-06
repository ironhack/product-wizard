"""
Routing Functions for RAG LangGraph Workflow
Defines conditional routing logic for the RAG pipeline.
"""

import logging
from src.state import RAGState
from src.utils import is_valid_coverage_topic

logger = logging.getLogger(__name__)


def route_after_cohort_calendar_classification(state: RAGState) -> str:
    """Route after triage: discontinued-program answer, cohort response, or standard retrieval."""
    if state.get("discontinued_program"):
        logger.info(f"Routing to discontinued_program_response ({state['discontinued_program']})")
        return "discontinued_program_response"
    if state.get("is_cohort_calendar_question", False):
        logger.info("Routing to cohort_calendar_response (cohort/calendar question)")
        return "cohort_calendar_response"
    return "hybrid_retrieval"


def route_after_query_enhancement(state: RAGState) -> str:
    """Route after query enhancement based on ambiguity."""
    ambiguity_score = state.get("ambiguity_score", 0.5)

    # If extremely ambiguous, might need clarification
    # For now, always proceed to program detection
    return "program_detection"


def route_after_document_filtering(state: RAGState) -> str:
    """Route after document filtering - re-fetch if not enough docs."""
    needs_refetch = state.get("metadata", {}).get("needs_refetch", False)

    if needs_refetch:
        # Clear the flag and go back to retrieval with higher limits
        logger.info("Routing back to retrieval for re-fetch with doubled limits")
        return "hybrid_retrieval"

    return "coverage_classification"


def route_after_coverage_classification(state: RAGState) -> str:
    """Route to coverage verification or generation."""
    # Skip coverage verification for comparison queries - they need full generation
    query_intent = state.get("query_intent", "general_info")
    if query_intent == "comparison":
        return "generate_response"
    # Portfolio-wide questions ("which courses include X?") span all programs;
    # per-program coverage verification would give a wrongly-scoped negative answer
    if state.get("is_portfolio_wide", False):
        logger.info("Portfolio-wide question - skipping per-program coverage verification")
        return "generate_response"
    if state.get("is_coverage_question", False):
        return "coverage_verification"
    return "generate_response"


def route_after_coverage_verification(state: RAGState) -> str:
    """Route to appropriate response generation based on coverage."""
    coverage_verification = state.get("coverage_verification", {})
    is_present = coverage_verification.get("is_present", False)

    if is_present:
        return "generate_response"

    # Only emit the "not mentioned" template when we have a real topic to name.
    # If topic extraction failed, a templated negative would read as
    # "*the requested topic* is not mentioned" - answer from the docs instead.
    topic = coverage_verification.get("topic", "")
    if not is_valid_coverage_topic(topic):
        logger.info(f"Coverage negative but topic invalid ({topic!r}) - routing to standard generation")
        return "generate_response"

    return "generate_negative_coverage"


def route_after_faithfulness_verification(state: RAGState) -> str:
    """Route based on faithfulness and iteration count."""
    is_grounded = state.get("is_grounded", False)
    faithfulness_score = state.get("faithfulness_score", 0.0)
    iteration_count = state.get("iteration_count", 0)
    query_intent = state.get("query_intent", "general_info")

    # Deliberate "entity not documented" answers finalize immediately: when the
    # query names an entity absent from every retrieved doc and the answer
    # explicitly addresses that entity, that IS the correct answer - looping it
    # through refinement can't improve it and previously ended in a dead fallback
    undocumented_entities = state.get("undocumented_entities") or []
    generated_response = state.get("generated_response", "")
    if undocumented_entities and len(generated_response) > 100 and any(
        e.lower() in generated_response.lower() for e in undocumented_entities
    ):
        logger.info(
            f"Finalizing deliberate undocumented-entity answer ({undocumented_entities})"
        )
        return "finalize_response"

    # Adjust threshold based on query type
    # Comparison queries synthesize multiple documents, so lower threshold
    # RAG systems cannot retrieve full curricula, so be realistic about what can be verified
    if query_intent == "comparison":
        threshold = 0.4  # Lower threshold for comparisons - they synthesize info from multiple docs
        max_iterations = 2
    elif query_intent in ["duration", "technical_detail", "certification"]:
        threshold = 0.6  # Lower for queries requiring synthesis of details
        max_iterations = 1
    else:
        threshold = 0.7
        max_iterations = 1

    # Production gate: require faithfulness >= threshold to finalize
    # NEVER allow responses with critical violations (fabrication, cross-contamination, wrong numbers)
    has_critical_violations = state.get("has_critical_violations", False)
    if has_critical_violations:
        logger.warning(f"Blocking response due to critical violations (fabrication/cross-contamination)")
        if iteration_count < max_iterations:
            return "iterative_refinement"
        else:
            return "generate_fun_fallback"

    # For comparison and technical_detail queries, accept if score >= threshold even if not fully grounded
    # These queries synthesize information and may not be perfectly grounded but still accurate
    if query_intent in ["comparison", "technical_detail"] and faithfulness_score >= threshold:
        return "finalize_response"
    elif faithfulness_score >= threshold and not state.get("is_fallback", False):
        # Critical violations were already handled above; a high score with no critical
        # violations finalizes even if the verifier's is_grounded boolean disagrees.
        # Some models return score=0.9 with is_grounded=false, which sent correct
        # answers into pointless refinement loops ending in a fallback.
        if not is_grounded:
            logger.info(
                f"Verifier score {faithfulness_score:.2f} >= {threshold} but is_grounded=false; "
                "trusting the score (no critical violations)"
            )
        return "finalize_response"
    # Allow refinement attempts based on query type
    elif iteration_count < max_iterations:
        return "iterative_refinement"
    else:
        # Max iterations reached - force fun fallback
        logger.warning(f"Max iterations ({max_iterations}) reached for {query_intent} query, routing to fun fallback")
        return "generate_fun_fallback"


def route_after_refinement(state: RAGState) -> str:
    """Route based on selected refinement strategy."""
    strategy = state.get("refinement_strategy", "FUN_FALLBACK")

    if strategy == "EXPAND_CHUNKS":
        return "hybrid_retrieval"
    elif strategy == "RELAX_NAMESPACE_FILTER":
        return "hybrid_retrieval"
    elif strategy == "ENHANCE_QUERY_KEYWORDS":
        return "query_enhancement"
    elif strategy == "SWITCH_TO_COVERAGE_PATH":
        return "coverage_verification"
    else:  # FUN_FALLBACK
        return "generate_fun_fallback"
