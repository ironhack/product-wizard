"""
Best Practice RAG Architecture v2 - LangGraph Implementation
Following research-backed best practices for sales enablement RAG systems:
- Namespace isolation via metadata filtering
- Hybrid retrieval (keyword-enhanced semantic search)
- Query enhancement for disambiguation
- Faithfulness verification dedicated node
- Iterative refinement with fallback strategies

This module serves as a compatibility shim, re-exporting all components
from the refactored modular structure.
"""

# ---------------- Configuration ----------------
from src.config import (
    SLACK_BOT_TOKEN,
    SLACK_SIGNING_SECRET,
    OPENAI_API_KEY,
    VECTOR_STORE_ID,
    openai_client,
    load_config_file,
    MASTER_PROMPT,
    GENERATION_INSTRUCTIONS,
    COMPARISON_INSTRUCTIONS,
    DOCUMENT_FILTERING_INSTRUCTIONS,
    COVERAGE_CLASSIFICATION_PROMPT,
    COVERAGE_VERIFICATION_PROMPT,
    FUN_FALLBACK_GENERATION,
    QUERY_ENHANCEMENT_PROMPT,
    PROGRAM_DETECTION_PROMPT,
    RELEVANCE_ASSESSMENT_PROMPT,
    FAITHFULNESS_VERIFICATION_PROMPT,
    REFINEMENT_STRATEGIES_PROMPT,
    PROGRAM_SYNONYMS,
)

# ---------------- State Schema ----------------
from src.state import RAGState

# ---------------- Utils ----------------
from src.utils import (
    convert_markdown_to_slack,
    call_openai_json,
    call_openai_text,
    format_conversation_history,
)

# ---------------- Slack Helpers ----------------
from src.slack_helpers import (
    _already_processed,
    get_conversation_history,
    set_slack_say_function,
    clear_slack_say_function,
    send_slack_update,
)

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

# ---------------- Workflow ----------------
from src.workflow import rag_workflow

# ---------------- Slack Integration ----------------
from src.slack_integration import handle_mention, handle_message

# ---------------- Flask App ----------------
from src.app import flask_app, slack_app, slack_handler

