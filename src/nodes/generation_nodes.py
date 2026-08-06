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

    # Portfolio-wide questions get a deterministic term index: a literal scan of ALL
    # local syllabus files. Retrieval alone clusters on the strongest program and
    # missed e.g. Linux in Cybersecurity/Cloud Engineering ("which course have linux in?").
    # Prepended as a doc so faithfulness verification sees the same evidence.
    if state.get("is_portfolio_wide", False):
        from src.utils import local_topic_index
        index_entries = local_topic_index(enhanced_query or state.get("query", ""), PROGRAM_SYNONYMS)
        if index_entries:
            index_lines = [
                f"- \"{e['term']}\" appears in {e['program_name']} [{e['source']}]: {e['evidence']}"
                for e in index_entries
            ]
            index_sources = list(dict.fromkeys(e["source"] for e in index_entries))
            index_doc = {
                "content": (
                    "LITERAL TERM INDEX - deterministic scan of ALL program syllabus files. "
                    "This is the authoritative list of which programs mention the queried term(s):\n"
                    + "\n".join(index_lines)
                ),
                "source": ", ".join(index_sources),
                "score": 1.0,
            }
            filtered_docs = [index_doc] + filtered_docs
            logger.info(f"Portfolio-wide term index: {len(index_entries)} matches across programs")

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

    # Breakdown requests get the complete syllabus in context - the answer must cover
    # ALL of it, not a fragment (users previously got weeks 5-6 of a 9-week program)
    breakdown_emphasis = ""
    if state.get("is_breakdown_request", False):
        breakdown_emphasis = (
            "\n\nCRITICAL FOR BREAKDOWN/OVERVIEW REQUESTS: The context includes the complete syllabus "
            "document. Your answer MUST cover the ENTIRE program structure - every unit/module/week "
            "present in the document, in order, from prework to final project. Do NOT stop partway, "
            "do NOT cover only some units, and do NOT tell the user to contact a team for the rest. "
            "Keep per-unit detail concise (topics and hours) so the full structure fits."
        )

    # Portfolio-wide questions must enumerate every program where the topic appears
    portfolio_emphasis = ""
    if state.get("is_portfolio_wide", False):
        portfolio_emphasis = (
            "\n\nCRITICAL FOR PORTFOLIO-WIDE QUESTIONS: The user is asking across ALL Ironhack programs, "
            "not one. The context includes a LITERAL TERM INDEX built by scanning every program's "
            "syllabus file - treat it as the authoritative list of which programs mention the term. "
            "Your answer MUST name EVERY program listed in that index (citing each program's syllabus "
            "file), with a one-line note of how the topic appears in each. Do not stop at the first "
            "match and do not omit programs that the index shows."
        )

    # Deterministic undocumented-entity guard: if the query names an acronym/entity
    # that appears NOWHERE in the retrieved context, the answer must say so instead
    # of dumping generic adjacent info (e.g. the IHK certification question answered
    # with the generic certification catalog).
    entity_emphasis = ""
    _known_short_terms = {
        "AI", "IT", "PT", "FT", "EN", "ES", "UX", "UI", "THE", "AND", "FOR", "HOW", "WHAT",
    } | {(info.get("code") or "").upper() for info in PROGRAM_SYNONYMS.values()}
    _query_acronyms = set(re.findall(r"\b[A-Z]{2,6}\b", f"{state.get('query', '')} {enhanced_query}"))
    _missing_entities = sorted(
        a for a in _query_acronyms - _known_short_terms if a.lower() not in context.lower()
    )
    if _missing_entities:
        _ents = ", ".join(_missing_entities)
        entity_emphasis = (
            f"\n\nCRITICAL - UNDOCUMENTED ENTITY: The user asked about '{_ents}', which appears "
            f"NOWHERE in the retrieved documents. You MUST begin your answer by stating clearly that "
            f"there is no documentation about '{_ents}' and that the Education team can confirm "
            f"whether it exists. Do NOT answer with generic related information as if it answered "
            f"the question about '{_ents}'. You may add clearly-labeled related context afterwards."
        )
        logger.info(f"Undocumented entities in query: {_missing_entities}")

    system_prompt = f"""{MASTER_PROMPT}

{GENERATION_INSTRUCTIONS}

{additional_instructions}
{duration_emphasis}{breakdown_emphasis}{portfolio_emphasis}{entity_emphasis}

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
        # Pass docs back including any injected term-index doc, so faithfulness
        # verification checks the answer against the same evidence generation saw
        "filtered_docs": filtered_docs,
        "generated_response": generated_response,
        "source_citations": citations
    }


def _find_other_programs_covering(topic: str, exclude_program_ids: list) -> list:
    """
    Which other programs' syllabi literally mention the topic PHRASE, via the
    local knowledge base (instant, deterministic ground truth - no API call).
    Whole-phrase matching: "Site Reliability Engineering" must not match every
    syllabus containing the word "engineering".
    Returns display names (max 3). Best-effort: any failure returns [].
    """
    from src.utils import load_full_syllabus_docs, program_display_name

    phrase = (topic or "").strip().lower()
    if len(phrase) < 3:
        return []
    try:
        found = []
        for pid in PROGRAM_SYNONYMS:
            if pid in exclude_program_ids:
                continue
            docs = load_full_syllabus_docs([pid], PROGRAM_SYNONYMS)
            if docs and phrase in docs[0]["content"].lower():
                found.append(pid)
        return [program_display_name(pid, PROGRAM_SYNONYMS) for pid in found[:3]]
    except Exception as e:
        logger.warning(f"Cross-program coverage lookup failed (skipping suggestion): {e}")
        return []


def generate_negative_coverage_node(state: RAGState) -> RAGState:
    """Generate clear 'No' response for negative coverage."""
    logger.info("=== Generate Negative Coverage Response ===")

    from src.utils import is_valid_coverage_topic, program_display_name

    coverage_verification = state.get("coverage_verification", {})
    topic = coverage_verification.get("topic", "")
    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    detected_programs = state.get("detected_programs", [])

    # Validate topic - if it looks like instruction text or is invalid, extract from query
    if not is_valid_coverage_topic(topic):
        topic = ""
        # Pattern 1: "Does X include/teach/cover Y?" -> extract Y
        match = re.search(r'(?:include|teach|cover|have|contain)s?\s+([^?]+)', enhanced_query, re.IGNORECASE)
        if match:
            topic = match.group(1).strip()
            # Clean up common trailing words
            topic = re.sub(r'\s+(in|for|at|with|from).*$', '', topic, flags=re.IGNORECASE)
            logger.info(f"Extracted topic from query: {topic}")
        else:
            # Pattern 2: "Is Y in X?" -> extract Y
            match = re.search(r'^is\s+([^?]+?)\s+(?:in|part of|taught in|covered in)', enhanced_query, re.IGNORECASE)
            if match:
                topic = match.group(1).strip()
                logger.info(f"Extracted topic from query (pattern 2): {topic}")

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

    program_name = program_display_name(primary_program, PROGRAM_SYNONYMS)

    # Fallback citations only if verifier had no syllabus chunks (should be rare)
    if not citations and primary_program and primary_program in PROGRAM_SYNONYMS:
        fn = PROGRAM_SYNONYMS[primary_program].get("filenames", [])
        if fn:
            citations = [fn[0].replace(".txt", ".md").replace(".md.md", ".md")]

    # Last-resort guard: if we still have no nameable topic, answer honestly without the template
    if not topic or not topic.strip():
        logger.warning("No nameable topic for negative coverage - using generic honest phrasing")
        topic = "the topic you asked about"

    # Check whether OTHER programs document this topic, so sales can redirect the
    # prospect instead of hitting a dead end ("CE doesn't have it, but DevOps does").
    exclude_ids = [primary_program] if primary_program else []
    other_programs = _find_other_programs_covering(topic, exclude_ids)

    sources_line = ", ".join(citations) if citations else "the scoped curriculum"
    if primary_program:
        result_line = (
            f"*Result:* *{topic}* is not listed in the {program_name} syllabus, "
            f"so we can't confirm it's part of that program."
        )
    else:
        result_line = (
            f"*Result:* *{topic}* is not mentioned in the documents we checked, "
            f"so we can't confirm it."
        )
    response_parts = [
        f"*What we checked:* {sources_line}",
        result_line,
    ]
    if other_programs:
        response_parts.append(
            f"*Covered elsewhere:* {topic} does appear in the curriculum for: {', '.join(other_programs)}."
        )
    response_parts.append(
        "_Note: this check runs against the syllabus summaries. A topic can still get brief hands-on "
        "exposure inside lessons without being listed - the Education team can confirm._"
    )
    response = "\n".join(response_parts)

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
