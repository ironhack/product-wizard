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
from src.utils import (
    call_openai_text,
    format_conversation_history,
    docs_for_program_syllabi,
    unique_citations_from_docs,
)
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

    # Citations = syllabus sources we actually grounded on (trust, not random chunk names)
    valid_detected = [p for p in detected_programs if p in PROGRAM_SYNONYMS]
    syllabus_docs = (
        docs_for_program_syllabi(filtered_docs, valid_detected, PROGRAM_SYNONYMS)
        if valid_detected
        else filtered_docs
    )
    citations = unique_citations_from_docs(syllabus_docs[:15] if syllabus_docs else filtered_docs[:15])
    if not citations:
        citations = unique_citations_from_docs(filtered_docs[:10])

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

    # Cite exactly what coverage_verification searched (sources_checked), not a guess.
    citations = list(coverage_verification.get("sources_checked") or [])
    valid_detected = [p for p in detected_programs if p in PROGRAM_SYNONYMS]
    primary_program = valid_detected[0] if valid_detected else None

    if not primary_program:
        query_lower = enhanced_query.lower()

        def _alias_matches(alias: str) -> bool:
            a = alias.lower().strip()
            if not a:
                return False
            if len(a) <= 3 and re.match(r"^[a-z0-9]+$", a):
                return bool(re.search(rf"(?<!\w){re.escape(a)}(?!\w)", query_lower))
            return a in query_lower

        alias_candidates = []
        for prog_id, prog_info in PROGRAM_SYNONYMS.items():
            for alias in prog_info.get("aliases", []):
                alias_candidates.append((prog_id, alias))
        alias_candidates.sort(key=lambda x: -len(x[1]))
        for prog_id, alias in alias_candidates:
            if _alias_matches(alias):
                primary_program = prog_id
                break
        if not primary_program:
            for prog_id, prog_info in PROGRAM_SYNONYMS.items():
                for filename in prog_info.get("filenames", []):
                    base_name = filename.replace("_", " ").replace(".txt", "").replace(".md", "").lower()
                    if len(base_name) >= 4 and base_name in query_lower:
                        primary_program = prog_id
                        break
                if primary_program:
                    break

    if primary_program and primary_program in PROGRAM_SYNONYMS:
        prog_info = PROGRAM_SYNONYMS[primary_program]
        program_name = (prog_info.get("aliases") or [primary_program])[0]
    else:
        program_name = primary_program.replace("_", " ") if primary_program else "this program"

    # Fallback citations only if verifier had no syllabus chunks (should be rare)
    if not citations and primary_program and primary_program in PROGRAM_SYNONYMS:
        fn = PROGRAM_SYNONYMS[primary_program].get("filenames", [])
        if fn:
            citations = [fn[0].replace(".txt", ".md").replace(".md.md", ".md")]

    sources_line = ", ".join(citations) if citations else "the scoped curriculum"
    response = (
        f"*What we checked:* {sources_line}\n"
        f"*Result:* *{topic}* is not mentioned in that curriculum, so it is not documented as part of {program_name}. "
        f"If you need this topic on the syllabus, Product can confirm with the academic team."
    )

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
