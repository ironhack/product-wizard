"""
Generation Nodes

Nodes for generating responses and handling negative coverage in the RAG workflow.
"""

import logging
import re

from src.state import RAGState
from src.config import (
    MASTER_PROMPT,
    GENERATION_INSTRUCTIONS,
    COMPARISON_INSTRUCTIONS,
    PROGRAM_SYNONYMS,
)
from src.utils import call_openai_text, format_conversation_history
from src.slack_helpers import send_slack_update


logger = logging.getLogger(__name__)


def generate_response_node(state: RAGState) -> RAGState:
    """
    Generate answer from filtered, relevant documents.
    - Enforce citation requirements
    - Constrained generation
    """
    logger.info("=== Generate Response Node ===")
    send_slack_update(state, "Generating response")

    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    filtered_docs = state.get("filtered_docs", [])
    conversation_history = state.get("conversation_history", [])
    detected_programs = state.get("detected_programs", [])
    query_intent = state.get("query_intent", "general_info")
    coverage_verification = state.get("coverage_verification", {})

    if not filtered_docs:
        logger.warning("No documents available for generation")
        return {
            **state,
            "generated_response": "I don't have sufficient information in the curriculum documents to answer this question accurately.",
            "source_citations": [],
            "is_fallback": True
        }

    # Compile context from filtered documents
    # Include full chunk content - low usage volume makes cost negligible, completeness is more important
    context_chunks = []
    for idx, doc in enumerate(filtered_docs[:10]):
        source = doc.get("source", "unknown")
        content = doc.get("content", "")
        context_chunks.append(f"[Chunk {idx+1} - Source: {source}]\n{content}")

    context = "\n\n---\n\n".join(context_chunks)

    # For coverage questions with positive verification, include the verification evidence
    # This ensures detailed topics are available even if they're in a different chunk
    if query_intent == "coverage" and coverage_verification.get("is_present", False):
        evidence = coverage_verification.get("evidence", [])
        if evidence:
            # Add evidence to context if not already included
            evidence_text = "\n\n".join([
                f"Evidence: {e.get('quote', '')} [Source: {e.get('source', 'unknown')}]"
                for e in evidence if isinstance(e, dict)
            ])
            if evidence_text and evidence_text not in context:
                context = f"{context}\n\n---\n\nCoverage Verification Evidence:\n{evidence_text}"
    conv_context = format_conversation_history(conversation_history, limit=3)

    # Use comparison instructions for comparison queries
    if query_intent == "comparison" and COMPARISON_INSTRUCTIONS:
        additional_instructions = COMPARISON_INSTRUCTIONS
    else:
        additional_instructions = ""

    # Add specific emphasis for duration queries
    duration_emphasis = ""
    if query_intent == "duration":
        duration_emphasis = "\n\nCRITICAL FOR DURATION QUERIES: If the retrieved documents contain a breakdown of hours (e.g., prework hours + course hours), you MUST include BOTH the total hours AND the breakdown in your response. Format: 'X hours total: Y hours prework + Z hours course' or similar format that clearly shows both total and breakdown."

    system_prompt = f"""{MASTER_PROMPT}

{GENERATION_INSTRUCTIONS}

{additional_instructions}
{duration_emphasis}

CRITICAL: Generate answers ONLY from the provided document context. Never use external knowledge.
"""

    user_prompt = f"""
User Query: "{enhanced_query}"
Query Intent: {query_intent}
Programs: {detected_programs}

Conversation Context:
{conv_context}

Retrieved Document Context:
{context}

Generate a comprehensive, accurate answer with proper source citations.
"""

    generated_response = call_openai_text(system_prompt, user_prompt)

    # Extract citations from response
    citations = []
    # First, try to extract citations from response text (preferred - LLM included them)
    for doc in filtered_docs:
        source = doc.get("source", "")
        if source and source in generated_response:
            citations.append(source)

    # Fallback: If no citations found in text, include all filtered doc sources
    # This ensures citations are always available even if LLM doesn't include them in response
    if not citations:
        citations = [doc.get("source", "") for doc in filtered_docs if doc.get("source")]
        logger.info(f"No citations found in response text, using fallback: {len(citations)} citations from filtered_docs")

    logger.info(f"Generated response: {len(generated_response)} chars | Citations: {len(citations)}")

    return {
        **state,
        "generated_response": generated_response,
        "source_citations": citations
    }


def generate_negative_coverage_node(state: RAGState) -> RAGState:
    """Generate clear 'No' response for negative coverage."""
    logger.info("=== Generate Negative Coverage Response ===")

    coverage_verification = state.get("coverage_verification", {})
    topic = coverage_verification.get("topic", "the requested topic")
    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    detected_programs = state.get("detected_programs", [])
    filtered_docs = state.get("filtered_docs", [])
    retrieved_docs = state.get("retrieved_docs", [])

    # Validate topic - if it looks like instruction text or is invalid, extract from query
    invalid_topic_indicators = [
        "single explicit topic",
        "multiple_topics",
        "if the query asks",
        "else",
        "broad queries"
    ]
    if any(indicator in topic.lower() for indicator in invalid_topic_indicators) or len(topic) > 100:
        # Extract topic from query - look for common patterns
        # Pattern 1: "Does X include/teach/cover Y?" -> extract Y
        match = re.search(r'(?:include|teach|cover|have|contain)\s+([^?]+)', enhanced_query, re.IGNORECASE)
        if match:
            topic = match.group(1).strip()
            # Clean up common trailing words
            topic = re.sub(r'\s+(in|for|at|with|from).*$', '', topic, flags=re.IGNORECASE)
            logger.info(f"Extracted topic from query: {topic}")
        else:
            # Pattern 2: "Is Y in X?" -> extract Y
            match = re.search(r'^is\s+([^?]+?)\s+(?:in|part of|taught in)', enhanced_query, re.IGNORECASE)
            if match:
                topic = match.group(1).strip()
                logger.info(f"Extracted topic from query (pattern 2): {topic}")
            else:
                # Fallback: use a generic phrase
                topic = "the requested topic"
                logger.warning(f"Could not extract topic from query, using fallback")

    # For negative coverage, we MUST cite the correct program's document
    # Even if it wasn't retrieved (because the topic isn't in it)
    # Extract the program name directly from the query to ensure we cite the right program
    citations = []

    # Extract program name from query - look for patterns like "Does [Program] include..."
    program_from_query = None
    query_lower = enhanced_query.lower()
    for prog_id, prog_info in PROGRAM_SYNONYMS.items():
        aliases = prog_info.get("aliases", [])
        filenames = prog_info.get("filenames", [])
        # Check if any alias or filename appears in query
        for alias in aliases:
            if alias.lower() in query_lower:
                program_from_query = prog_id
                logger.info(f"Extracted program from query: {prog_id} (matched alias: {alias})")
                break
        if program_from_query:
            break
        # Also check filenames
        for filename in filenames:
            base_name = filename.replace("_", " ").replace(".txt", "").replace(".md", "").lower()
            if base_name in query_lower:
                program_from_query = prog_id
                logger.info(f"Extracted program from query: {prog_id} (matched filename: {filename})")
                break
        if program_from_query:
            break

    # Use program from query if found, otherwise use first detected program
    primary_program = program_from_query or (detected_programs[0] if detected_programs else None)

    if not primary_program:
        logger.warning("Could not determine primary program for negative coverage citation")
    else:
        logger.info(f"Using primary program for citation: {primary_program}")

    # First, try to find the correct program document in retrieved_docs
    # IMPORTANT: Only look for documents matching the primary program, ignore others
    if primary_program and primary_program in PROGRAM_SYNONYMS:
        prog_info = PROGRAM_SYNONYMS[primary_program]
        filenames = prog_info.get("filenames", [])

        # Check all retrieved documents (not just filtered) for correct program document
        for doc in retrieved_docs:
            source = doc.get("source", "")
            for filename in filenames:
                # Match filename (with or without extension, case-insensitive)
                base_filename = filename.replace(".txt", "").replace(".md", "")
                if base_filename.lower() in source.lower() or filename.lower() in source.lower():
                    if source not in citations:
                        citations.append(source)
                        logger.debug(f"Found correct program citation in retrieved docs: {source}")
                        break

    # If not found in retrieved docs, use expected filename from PROGRAM_SYNONYMS
    # This ensures we cite the correct document even if it wasn't retrieved
    if not citations and primary_program and primary_program in PROGRAM_SYNONYMS:
        prog_info = PROGRAM_SYNONYMS[primary_program]
        filenames = prog_info.get("filenames", [])
        if filenames:
            # Use the expected filename as citation (prefer .md format for consistency)
            expected_filename = filenames[0].replace(".txt", ".md").replace(".md.md", ".md")
            citations.append(expected_filename)
            logger.info(f"Using expected program document citation: {expected_filename}")

    # Build response with correct citation
    # For negative coverage, we just need to state clearly that the topic is not included
    # and cite the correct program document - no need for extra context
    # Format program name for display
    if primary_program and primary_program in PROGRAM_SYNONYMS:
        prog_info = PROGRAM_SYNONYMS[primary_program]
        aliases = prog_info.get("aliases", [])
        program_name = aliases[0] if aliases else primary_program.replace("_", " ")
    else:
        program_name = primary_program.replace("_", " ") if primary_program else "the program"

    if citations:
        primary_source = citations[0]
        response = f"No, {program_name} does not include {topic}. Based on the curriculum documents, this topic is not part of the program. [Source: {primary_source}]"
    else:
        response = f"No, {program_name} does not include {topic}. Based on the curriculum documents, this topic is not part of the program."

    # Convert markdown formatting to Slack-friendly format
    from src.utils import convert_markdown_to_slack
    response = convert_markdown_to_slack(response)

    logger.info(f"Generated negative coverage response: {len(response)} chars | Citations: {len(citations)}")

    return {
        **state,
        "generated_response": response,
        "final_response": response,
        "source_citations": citations
    }
