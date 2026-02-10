"""
Assessment Nodes

Nodes for relevance assessment and document filtering in the RAG workflow.
"""

import logging
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.state import RAGState
from src.config import (
    RELEVANCE_ASSESSMENT_PROMPT,
    DOCUMENT_FILTERING_INSTRUCTIONS,
    PROGRAM_SYNONYMS,
)
from src.utils import call_openai_json
from src.slack_helpers import send_slack_update


logger = logging.getLogger(__name__)


def relevance_assessment_node(state: RAGState) -> RAGState:
    """
    AI-powered relevance scoring for pre-filtered documents.
    - Score 0-1 for each chunk
    - Filter out low-relevance docs
    - Detect cross-contamination
    - Now runs AFTER document_filtering to save API costs
    """
    logger.info("=== Relevance Assessment Node ===")
    send_slack_update(state, "Assessing document relevance")

    # Use filtered_docs from document_filtering (cheaper: only assess relevant program docs)
    docs_to_assess = state.get("filtered_docs", []) or state.get("retrieved_docs", [])
    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    detected_programs = state.get("detected_programs", [])
    query_intent = state.get("query_intent", "general_info")
    conversation_history = state.get("conversation_history", [])

    if not docs_to_assess:
        logger.warning("No documents to assess")
        return {
            **state,
            "filtered_docs": [],
            "relevance_scores": [],
            "rejection_reasons": ["No documents retrieved"]
        }

    # Format conversation context for relevance assessment
    conv_context = ""
    if conversation_history:
        # Get last 2 turns for context
        recent_history = conversation_history[-4:] if len(conversation_history) > 4 else conversation_history
        conv_lines = []
        for msg in recent_history:
            role = msg.type if hasattr(msg, 'type') else 'unknown'
            content = msg.content if hasattr(msg, 'content') else str(msg)
            if content and len(content) < 500:  # Only include short context
                conv_lines.append(f"{role}: {content}")
        if conv_lines:
            conv_context = f"\nConversation Context:\n" + "\n".join(conv_lines)

    # Assess relevance for each chunk in parallel
    def assess_single_doc(idx_doc_pair):
        """Assess a single document's relevance."""
        idx, doc = idx_doc_pair
        doc_content = doc.get("content", "")[:500]  # Preview
        doc_source = doc.get("source", "unknown")

        user_prompt = f"""
Query: "{enhanced_query}"
Query Intent: {query_intent}
Detected Programs: {detected_programs}{conv_context}

Document Chunk {idx+1}:
Source: {doc_source}
Content Preview: {doc_content}

Assess this chunk's relevance to the query.
"""

        try:
            # Use faster model for relevance assessment (classification task)
            assessment = call_openai_json(RELEVANCE_ASSESSMENT_PROMPT, user_prompt, model="gpt-4o-mini", timeout=15)

            relevance_score = assessment.get("relevance_score", 0.5)
            should_include = assessment.get("should_include", False)
            red_flags = assessment.get("red_flags", [])

            # For comparison and certification queries, use lower threshold and be more permissive
            # Comparison queries need chunks from multiple programs
            # Certification queries need chunks from universal documents (Certifications doc, Portfolio Overview) which may score lower
            if query_intent == "comparison":
                threshold = 0.2
                # For comparison queries, override should_include if score is high enough
                # This ensures we get chunks from all programs even if AI is conservative
                if relevance_score >= 0.5:
                    should_include = True
            elif query_intent == "certification":
                threshold = 0.2
                # BOOST: For certification queries, automatically include universal/overview documents
                # These contain the certification information even if AI gives them low scores
                doc_source_lower = doc_source.lower()
                is_universal_or_overview = any(univ in doc_source_lower for univ in [
                    "certifications_2025_07",
                    "ironhack_portfolio_overview",
                    "course_design_overview"
                ])
                if is_universal_or_overview:
                    relevance_score = max(relevance_score, 0.8)  # Boost to high relevance
                    should_include = True
                elif relevance_score >= 0.4:
                    should_include = True
            else:
                threshold = 0.3

            return {
                "idx": idx,
                "doc": doc,
                "relevance_score": relevance_score,
                "should_include": should_include and relevance_score >= threshold,
                "red_flags": red_flags,
                "reasoning": assessment.get("reasoning", "Low relevance"),
                "error": None
            }
        except Exception as e:
            logger.error(f"Assessment failed for doc {idx+1}: {e}")
            # On error, include the doc with medium score
            return {
                "idx": idx,
                "doc": doc,
                "relevance_score": 0.6,
                "should_include": True,
                "red_flags": [],
                "reasoning": f"Error: {str(e)}",
                "error": str(e)
            }

    # Parallelize assessments using ThreadPoolExecutor
    assessed_docs = []
    relevance_scores = []
    rejection_reasons = []

    # For comparison and certification queries, assess all filtered docs
    # Comparison queries need chunks from all programs
    # Certification queries need chunks from universal documents which may be lower in retrieval order
    # After filtering, we have fewer docs, so we can assess more (or all) of them
    max_docs_to_assess = len(docs_to_assess) if query_intent in ["comparison", "certification"] else len(docs_to_assess)
    docs_to_assess_enumerated = list(enumerate(docs_to_assess[:max_docs_to_assess]))

    # Use ThreadPoolExecutor with max_workers (OpenAI API can handle concurrent requests)
    # Increased to 8 concurrent requests for better performance (OpenAI allows higher concurrency)
    max_workers = min(8, len(docs_to_assess_enumerated))

    if len(docs_to_assess_enumerated) > 1:
        query_type_note = "comparison/certification queries" if query_intent in ["comparison", "certification"] else "standard queries"
        logger.info(f"Parallelizing relevance assessment: {len(docs_to_assess_enumerated)} docs with {max_workers} workers (assessing all docs for {query_type_note})")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all assessment tasks
        future_to_idx = {executor.submit(assess_single_doc, idx_doc): idx_doc[0]
                        for idx_doc in docs_to_assess_enumerated}

        # Collect results as they complete
        results = []
        for future in as_completed(future_to_idx):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                idx = future_to_idx[future]
                logger.error(f"Future failed for doc {idx+1}: {e}")
                # Include doc with medium score on future failure
                if idx < len(retrieved_docs):
                    results.append({
                        "idx": idx,
                        "doc": retrieved_docs[idx],
                        "relevance_score": 0.6,
                        "should_include": True,
                        "red_flags": [],
                        "reasoning": f"Future error: {str(e)}",
                        "error": str(e)
                    })

        # Sort results by original index to maintain order
        results.sort(key=lambda x: x["idx"])

        # Process results
        for result in results:
            idx = result["idx"]
            doc = result["doc"]
            relevance_score = result["relevance_score"]
            should_include = result["should_include"]
            red_flags = result["red_flags"]
            reasoning = result["reasoning"]

            if should_include:
                assessed_docs.append(doc)
                relevance_scores.append(relevance_score)
            else:
                rejection_reasons.append(f"Doc {idx+1}: {reasoning}")
                if red_flags:
                    logger.warning(f"Red flags for doc {idx+1}: {red_flags}")

    # If no docs passed assessment, include top 3 docs anyway as fallback
    if not assessed_docs and docs_to_assess:
        logger.warning("No docs passed relevance assessment, using fallback strategy")
        assessed_docs = docs_to_assess[:3]
        relevance_scores = [0.6] * len(assessed_docs)  # Give them medium scores

    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    logger.info(f"Assessed {len(assessed_docs)} docs | Avg Relevance: {avg_relevance:.2f}")

    return {
        **state,
        "filtered_docs": assessed_docs,
        "relevance_scores": relevance_scores,
        "rejection_reasons": rejection_reasons
    }


def document_filtering_node(state: RAGState) -> RAGState:
    """
    Simple document filtering: keep only docs from detected program + universal docs.
    If not enough docs after filtering, signal for re-fetch with higher limits.
    Now runs BEFORE relevance assessment to save API costs.
    """
    logger.info("=== Document Filtering Node ===")
    send_slack_update(state, "Filtering best matches")

    # Use retrieved_docs if running before relevance assessment, otherwise use filtered_docs
    docs_to_filter = state.get("retrieved_docs", []) or state.get("filtered_docs", [])
    detected_programs = state.get("detected_programs", [])
    query_intent = state.get("query_intent", "general_info")
    enhanced_query = state.get("enhanced_query", state.get("query", ""))

    # Clear the refetch flag at start (we're now processing after a potential refetch)
    metadata = state.get("metadata", {}).copy()
    metadata["needs_refetch"] = False

    if not docs_to_filter:
        return {**state, "metadata": metadata}

    # Universal documents that apply to all programs
    UNIVERSAL_DOCUMENTS = [
        "certifications_2025_07",
        "course_design_overview_2025_07",
        "computer_specs_min_requirements",
        "ironhack_portfolio_overview_2025_07"
    ]

    # Get valid programs (actual program IDs, not document names like "certifications")
    valid_programs = [prog_id for prog_id in detected_programs if prog_id in PROGRAM_SYNONYMS]

    # Build expected source patterns for detected programs
    expected_sources = set()
    for prog_id in valid_programs:
        prog_info = PROGRAM_SYNONYMS.get(prog_id, {})
        filenames = prog_info.get("filenames", [])
        for filename in filenames:
            expected_sources.add(filename.lower())
            expected_sources.add(filename.replace(".txt", "").replace(".md", "").lower())

    # Simple filtering: keep only matching docs
    source_filtered_docs = []
    program_doc_count = 0  # Track program-specific docs separately

    for doc in docs_to_filter:
        source = doc.get("source", "").lower()

        # Keep universal documents (but don't count toward program docs)
        if any(univ in source for univ in UNIVERSAL_DOCUMENTS):
            source_filtered_docs.append(doc)
            continue

        # If no program detected, keep all docs
        if not valid_programs:
            source_filtered_docs.append(doc)
            program_doc_count += 1
            continue

        # Keep only docs matching detected program
        if any(expected in source for expected in expected_sources):
            source_filtered_docs.append(doc)
            program_doc_count += 1
        else:
            logger.debug(f"Filtered out: {doc.get('source', 'unknown')}")

    logger.info(f"Source filtering: {len(docs_to_filter)} → {len(source_filtered_docs)} docs ({program_doc_count} program-specific)")

    # If we have very few PROGRAM-SPECIFIC docs, signal for re-fetch (universal docs don't count)
    needs_refetch = program_doc_count < 2 and valid_programs

    if needs_refetch:
        # Check if we already did a re-fetch (to avoid infinite loop)
        refetch_count = state.get("metadata", {}).get("refetch_count", 0)
        if refetch_count < 1:  # Only 1 refetch allowed: 30 → 50
            logger.warning(f"Only {program_doc_count} program-specific docs after filtering, signaling re-fetch (attempt {refetch_count + 1})")
            return {
                **state,
                "filtered_docs": source_filtered_docs,
                "metadata": {
                    **state.get("metadata", {}),
                    "needs_refetch": True,
                    "refetch_count": refetch_count + 1
                }
            }
        else:
            logger.warning(f"Max re-fetch (30 → 50) completed, proceeding with {len(source_filtered_docs)} docs")

    filtered_docs = source_filtered_docs

    # STEP 2: AI-based fine-grained filtering (only if we have enough docs after source filtering)
    # For comparison and certification queries, use higher threshold and ensure proper representation
    # Optimized: Only run AI filtering if we have more than 5 docs (reduces unnecessary calls)
    # SKIP AI filtering for certification queries - they need all available chunks and relevance assessment handles it better
    if len(filtered_docs) > 5 and query_intent != "certification":
        # For comparison queries, process more docs and ensure balanced representation
        # For certification queries, process more docs to ensure we get certification chunks
        max_docs_for_filtering = 20 if query_intent == "comparison" else (15 if query_intent == "certification" else 12)
        docs_summary = []
        for idx, doc in enumerate(filtered_docs[:max_docs_for_filtering]):
            docs_summary.append({
                "chunk_id": idx + 1,
                "source": doc.get("source", "unknown"),
                "content_preview": doc.get("content", "")[:150]  # Reduced preview length
            })

        # Build comparison-specific or certification-specific context
        special_context = ""
        if query_intent == "comparison" and valid_programs:
            program_names = []
            for prog_id in valid_programs:
                prog_info = PROGRAM_SYNONYMS.get(prog_id, {})
                aliases = prog_info.get("aliases", [])
                program_names.append(aliases[0] if aliases else prog_id.replace("_", " "))

            special_context = f"""
CRITICAL: This is a COMPARISON query comparing: {', '.join(program_names)}
- You MUST select chunks from ALL programs being compared
- Ensure balanced representation - roughly equal chunks from each program
- Select chunks that provide comparable information (e.g., curriculum structure, technologies, hours)
- The goal is to enable side-by-side comparison, so parallel information is crucial
"""
        elif query_intent == "certification" and valid_programs:
            program_names = []
            for prog_id in valid_programs:
                prog_info = PROGRAM_SYNONYMS.get(prog_id, {})
                aliases = prog_info.get("aliases", [])
                program_names.append(aliases[0] if aliases else prog_id.replace("_", " "))

            program_name = program_names[0] if program_names else "the program"
            special_context = f"""
CRITICAL: This is a CERTIFICATION query for {program_name}
- You MUST select chunks from the Certifications document that mention {program_name} or related program names
- Certification chunks may have the program name in section headers - still include them if they list certifications
- Look for chunks containing specific certification names (e.g., "Certified React Developer", "MongoDB Developer Certification")
- Even if a chunk doesn't explicitly repeat the program name, include it if it's from the Certifications document and lists certifications
"""

        user_prompt = f"""
Query: "{enhanced_query}"
Query Intent: {query_intent}
Detected Programs: {detected_programs}
{special_context}
Retrieved Document Chunks (already filtered by source):
{json.dumps(docs_summary, indent=2)}

Apply fine-grained relevance filtering. These chunks are already from the correct program documents.
Return the IDs of chunks that should be KEPT (others will be rejected).
Return as JSON: {{"kept_chunk_ids": [1, 2, 5, ...], "reasoning": "explanation"}}
"""

        try:
            # Use faster model for document filtering (classification task)
            result = call_openai_json(DOCUMENT_FILTERING_INSTRUCTIONS, user_prompt, model="gpt-4o-mini", timeout=20)
            kept_ids = result.get("kept_chunk_ids", [])

            # Filter docs based on kept IDs - but be more permissive if too few docs
            final_docs = [doc for idx, doc in enumerate(filtered_docs) if (idx + 1) in kept_ids]

            # For certification queries, ensure we have chunks from Certifications document
            if query_intent == "certification":
                # Check if we have chunks from Certifications document
                has_certifications_doc = any("certifications" in doc.get("source", "").lower() for doc in final_docs)
                if not has_certifications_doc:
                    # Find and add top certification chunks
                    logger.warning(f"Certification query missing Certifications document chunks, adding top certification chunks")
                    for doc in filtered_docs:
                        source = doc.get("source", "").lower()
                        if "certifications" in source and doc not in final_docs:
                            final_docs.append(doc)
                            logger.info(f"Added certification chunk: {doc.get('source', 'unknown')}")
                            # Add up to 3 certification chunks
                            if len([d for d in final_docs if "certifications" in d.get("source", "").lower()]) >= 3:
                                break

            # For comparison queries, ensure we have docs from all programs
            if query_intent == "comparison" and valid_programs:
                # Check if we have docs from all programs
                programs_represented = set()
                for doc in final_docs:
                    source = doc.get("source", "").lower()
                    for prog_id in valid_programs:
                        prog_info = PROGRAM_SYNONYMS.get(prog_id, {})
                        filenames = prog_info.get("filenames", [])
                        for filename in filenames:
                            base_filename = filename.replace(".txt", "").replace(".md", "").lower()
                            if base_filename in source or filename.lower() in source:
                                programs_represented.add(prog_id)
                                break

                # If missing programs, add top docs from missing programs
                missing_programs = set(valid_programs) - programs_represented
                if missing_programs:
                    logger.warning(f"Comparison query missing docs from programs: {missing_programs}")
                    for prog_id in missing_programs:
                        prog_info = PROGRAM_SYNONYMS.get(prog_id, {})
                        filenames = prog_info.get("filenames", [])
                        # Find top doc from this program
                        for doc in filtered_docs:
                            source = doc.get("source", "").lower()
                            for filename in filenames:
                                base_filename = filename.replace(".txt", "").replace(".md", "").lower()
                                if base_filename in source or filename.lower() in source:
                                    if doc not in final_docs:
                                        final_docs.append(doc)
                                        programs_represented.add(prog_id)
                                        logger.info(f"Added doc from missing program: {prog_id}")
                                        break
                            if prog_id in programs_represented:
                                break

            # If AI filtering removed too many docs, be more permissive
            if len(final_docs) < 2 and len(filtered_docs) >= 2:
                # Keep top 3 docs even if filtering was strict
                final_docs = filtered_docs[:3]
                logger.info(f"AI filtering too strict, keeping top 3 docs instead")

            filtered_docs = final_docs
            logger.info(f"AI filtering: {len(filtered_docs)} docs after fine-grained filtering")

        except Exception as e:
            logger.error(f"AI document filtering failed: {e}, keeping source-filtered docs")
            # On error, keep source-filtered docs

    logger.info(f"Final filtering result: {len(state.get('filtered_docs', []))} → {len(filtered_docs)} docs")

    return {
        **state,
        "filtered_docs": filtered_docs,
        "metadata": metadata  # Pass through with needs_refetch cleared
    }
