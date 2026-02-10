"""
RAG State Schema for LangGraph
Defines the TypedDict state used throughout the RAG pipeline.
"""

from typing import Dict, List, TypedDict, Optional, Any
from langchain_core.messages import BaseMessage


class RAGState(TypedDict, total=False):
    """State schema for RAG LangGraph pipeline."""

    # Input
    query: str
    conversation_history: List[BaseMessage]

    # Conversation context metadata
    is_follow_up: bool
    conversation_stage: str

    # Query Enhancement
    enhanced_query: str
    query_intent: str
    ambiguity_score: float

    # Program Detection & Namespace
    detected_programs: List[str]
    namespace_filter: Optional[Dict[str, Any]]

    # Retrieval
    retrieval_query: str
    retrieved_docs: List[Dict]
    retrieval_stats: Dict

    # Slack Integration (stored separately to avoid serialization issues)
    slack_channel: Optional[str]
    slack_thread_ts: Optional[str]

    # Relevance & Filtering
    relevance_scores: List[float]
    filtered_docs: List[Dict]
    rejection_reasons: List[str]

    # Coverage Detection
    is_coverage_question: bool
    coverage_verification: Dict

    # Generation
    generated_response: str
    source_citations: List[str]

    # Faithfulness Verification
    faithfulness_score: float
    faithfulness_violations: List[str]
    is_grounded: bool

    # Fallback & Iteration
    is_fallback: bool
    has_critical_violations: bool
    iteration_count: int
    refinement_strategy: str

    # Final
    final_response: str
    metadata: Dict

    # Error handling
    error: Optional[str]
