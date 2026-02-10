"""
Fallback Nodes

Nodes for iterative refinement, fun fallback generation, and response finalization
in the RAG workflow.
"""

import logging
import json

from src.state import RAGState
from src.config import (
    FUN_FALLBACK_GENERATION,
    REFINEMENT_STRATEGIES_PROMPT,
)
from src.utils import (
    convert_markdown_to_slack,
    call_openai_json,
    call_openai_text,
)
from src.slack_helpers import send_slack_update


logger = logging.getLogger(__name__)


def iterative_refinement_node(state: RAGState) -> RAGState:
    """
    Determine and apply refinement strategy.
    - Expand chunks
    - Relax filters
    - Enhance query
    - Generate fun fallback
    """
    logger.info("=== Iterative Refinement Node ===")

    iteration_count = state.get("iteration_count", 0)
    faithfulness_score = state.get("faithfulness_score", 1.0)
    is_fallback = state.get("is_fallback", False)
    filtered_docs = state.get("filtered_docs", [])
    relevance_scores = state.get("relevance_scores", [])

    # Prevent infinite loops - check query intent for max iterations
    query_intent = state.get("query_intent", "general_info")
    max_allowed_iterations = 3 if query_intent == "comparison" else 2

    if iteration_count >= max_allowed_iterations:
        logger.warning(f"Max iterations reached ({iteration_count}), forcing fun fallback")
        return {
            **state,
            "refinement_strategy": "FUN_FALLBACK",
            "iteration_count": iteration_count + 1
        }

    # Analyze failure mode
    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    num_docs = len(filtered_docs)

    failure_analysis = {
        "iteration_count": iteration_count,
        "faithfulness_score": faithfulness_score,
        "is_fallback": is_fallback,
        "num_docs_retrieved": num_docs,
        "avg_relevance": avg_relevance
    }

    user_prompt = f"""
Failure Analysis:
{json.dumps(failure_analysis, indent=2)}

Determine the best refinement strategy to improve results.
"""

    # Use faster model for refinement strategy selection (classification task)
    result = call_openai_json(REFINEMENT_STRATEGIES_PROMPT, user_prompt, model="gpt-4o-mini", timeout=15)

    selected_strategy = result.get("selected_strategy", "FUN_FALLBACK")
    refinement_params = result.get("parameters", {})

    logger.info(f"Refinement Strategy: {selected_strategy} | Iteration: {iteration_count + 1}")

    # Update state with refinement decision
    return {
        **state,
        "iteration_count": iteration_count + 1,
        "refinement_strategy": selected_strategy,
        "metadata": {
            **state.get("metadata", {}),
            "refinement_applied": selected_strategy,
            "refinement_params": refinement_params
        }
    }


def generate_fun_fallback_node(state: RAGState) -> RAGState:
    """
    Generate contextual fun fallback message with team routing.
    """
    logger.info("=== Generate Fun Fallback Node ===")

    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    detected_programs = state.get("detected_programs", [])

    system_prompt = FUN_FALLBACK_GENERATION

    user_prompt = f"""User Query: "{enhanced_query}"
Programs: {detected_programs}

Generate an appropriate fun fallback response using the templates and routing rules provided."""

    # Use faster model for fallback generation (simpler task)
    fallback_response = call_openai_text(system_prompt, user_prompt, model="gpt-4o-mini", timeout=20)

    # Convert markdown formatting to Slack-friendly format
    fallback_response = convert_markdown_to_slack(fallback_response)

    logger.info("Generated fun fallback response")

    return {
        **state,
        "final_response": fallback_response
    }


def finalize_response_node(state: RAGState) -> RAGState:
    """
    Format final response with citations and metadata.
    Convert markdown to Slack-friendly formatting.
    """
    logger.info("=== Finalize Response Node ===")
    send_slack_update(state, "Finalizing response")

    generated_response = state.get("generated_response", "")
    source_citations = state.get("source_citations", [])
    faithfulness_score = state.get("faithfulness_score", 0.0)
    detected_programs = state.get("detected_programs", [])

    # Format citations if not already in response
    if source_citations and "[Source:" not in generated_response:
        citation_text = "\n\nSources: " + ", ".join(set(source_citations))
        final_response = generated_response + citation_text
    else:
        final_response = generated_response

    # Convert markdown formatting to Slack-friendly format
    final_response = convert_markdown_to_slack(final_response)

    metadata = {
        **state.get("metadata", {}),
        "detected_programs": detected_programs,
        "faithfulness_score": faithfulness_score,
        "num_sources": len(source_citations),
        "iteration_count": state.get("iteration_count", 0)
    }

    logger.info(f"Finalized response: {len(final_response)} chars")

    return {
        **state,
        "final_response": final_response,
        "metadata": metadata
    }
