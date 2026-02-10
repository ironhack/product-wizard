"""
RAG LangGraph Workflow Builder
Constructs the LangGraph StateGraph with all nodes and routing logic.
"""

import logging
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.state import RAGState

# ---------------- Query Nodes ----------------
from src.nodes.query_nodes import (
    query_enhancement_node,
    program_detection_node,
)

# ---------------- Retrieval Nodes ----------------
from src.nodes.retrieval_nodes import (
    hybrid_retrieval_node,
)

# ---------------- Assessment Nodes ----------------
from src.nodes.assessment_nodes import (
    relevance_assessment_node,
    document_filtering_node,
)

# ---------------- Verification Nodes ----------------
from src.nodes.verification_nodes import (
    coverage_classification_node,
    coverage_verification_node,
    faithfulness_verification_node,
)

# ---------------- Generation Nodes ----------------
from src.nodes.generation_nodes import (
    generate_response_node,
    generate_negative_coverage_node,
)

# ---------------- Fallback Nodes ----------------
from src.nodes.fallback_nodes import (
    iterative_refinement_node,
    generate_fun_fallback_node,
    finalize_response_node,
)

# ---------------- Routing Functions ----------------
from src.routes import (
    route_after_query_enhancement,
    route_after_document_filtering,
    route_after_coverage_classification,
    route_after_coverage_verification,
    route_after_faithfulness_verification,
    route_after_refinement,
)

logger = logging.getLogger(__name__)


def build_workflow() -> StateGraph:
    """Build the LangGraph workflow with all nodes and routing."""
    logger.info("Building RAG workflow...")

    workflow = StateGraph(RAGState)

    # Add all nodes
    workflow.add_node("query_enhancement", query_enhancement_node)
    workflow.add_node("program_detection", program_detection_node)
    workflow.add_node("hybrid_retrieval", hybrid_retrieval_node)
    workflow.add_node("relevance_assessment", relevance_assessment_node)
    workflow.add_node("document_filtering", document_filtering_node)
    workflow.add_node("coverage_classification", coverage_classification_node)
    workflow.add_node("coverage_verification", coverage_verification_node)
    workflow.add_node("generate_response", generate_response_node)
    workflow.add_node("faithfulness_verification", faithfulness_verification_node)
    workflow.add_node("iterative_refinement", iterative_refinement_node)
    workflow.add_node("generate_fun_fallback", generate_fun_fallback_node)
    workflow.add_node("generate_negative_coverage", generate_negative_coverage_node)
    workflow.add_node("finalize_response", finalize_response_node)

    # Set entry point
    workflow.set_entry_point("query_enhancement")

    # Add edges
    workflow.add_edge("query_enhancement", "program_detection")
    workflow.add_edge("program_detection", "hybrid_retrieval")
    workflow.add_edge("hybrid_retrieval", "relevance_assessment")
    workflow.add_edge("relevance_assessment", "document_filtering")

    # Conditional routing after document filtering (re-fetch if not enough docs)
    workflow.add_conditional_edges(
        "document_filtering",
        route_after_document_filtering,
        {
            "hybrid_retrieval": "hybrid_retrieval",
            "coverage_classification": "coverage_classification"
        }
    )

    # Conditional routing after coverage classification
    workflow.add_conditional_edges(
        "coverage_classification",
        route_after_coverage_classification,
        {
            "coverage_verification": "coverage_verification",
            "generate_response": "generate_response"
        }
    )

    # Routing after coverage verification
    workflow.add_conditional_edges(
        "coverage_verification",
        route_after_coverage_verification,
        {
            "generate_response": "generate_response",
            "generate_negative_coverage": "generate_negative_coverage"
        }
    )

    # Negative coverage goes straight to END
    workflow.add_edge("generate_negative_coverage", END)

    # Generation goes to faithfulness verification
    workflow.add_edge("generate_response", "faithfulness_verification")

    # Routing after faithfulness verification
    workflow.add_conditional_edges(
        "faithfulness_verification",
        route_after_faithfulness_verification,
        {
            "finalize_response": "finalize_response",
            "iterative_refinement": "iterative_refinement",
            "generate_fun_fallback": "generate_fun_fallback"
        }
    )

    # Routing after refinement
    workflow.add_conditional_edges(
        "iterative_refinement",
        route_after_refinement,
        {
            "hybrid_retrieval": "hybrid_retrieval",
            "query_enhancement": "query_enhancement",
            "coverage_verification": "coverage_verification",
            "generate_fun_fallback": "generate_fun_fallback"
        }
    )

    # Fun fallback and finalize both go to END
    workflow.add_edge("generate_fun_fallback", END)
    workflow.add_edge("finalize_response", END)

    # Compile with memory
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# ---------------- Initialize Workflow ----------------
rag_workflow = build_workflow()
logger.info("RAG workflow initialized successfully")
