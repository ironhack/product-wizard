"""
Retrieval Nodes

Nodes for document retrieval in the RAG workflow.
"""

import logging

from src.state import RAGState
from src.config import (
    VECTOR_STORE_ID,
    PROGRAM_SYNONYMS,
    MODEL_FAST,
    openai_client,
)
from src.slack_helpers import send_slack_update
from src.utils import load_full_syllabus_docs


logger = logging.getLogger(__name__)


def hybrid_retrieval_node(state: RAGState) -> RAGState:
    """
    Retrieve documents using keyword-enhanced semantic search.
    - Apply namespace filtering
    - Enhance query with keywords
    - Perform vector search
    - Boost keyword matches
    """
    logger.info("=== Hybrid Retrieval Node ===")
    send_slack_update(state, "Searching curriculum documents")

    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    detected_programs = state.get("detected_programs", [])
    namespace_filter = state.get("namespace_filter")
    query_intent = state.get("query_intent", "general_info")
    iteration_count = state.get("iteration_count", 0)
    refinement_strategy = state.get("refinement_strategy", "")

    # Build keyword-enhanced query
    keyword_additions = []

    # Add program names
    for prog_id in detected_programs:
        prog_info = PROGRAM_SYNONYMS.get(prog_id, {})
        filenames = prog_info.get("filenames", [])
        if filenames:
            keyword_additions.append(filenames[0].replace("_", " ").replace(".txt", ""))

    # Add intent-specific keywords
    intent_keywords = {
        "coverage": "curriculum teaches includes covers contains",
        "certification": "certification credentials certificate industry",
        "duration": "hours weeks schedule duration time format",
        "technical_detail": "tools technologies frameworks libraries platforms",
        "requirements": "prerequisites requirements computer specs hardware software"
    }
    keyword_additions.append(intent_keywords.get(query_intent, ""))

    # Build enhanced retrieval query
    keywords = " ".join(keyword_additions)

    # For certification queries, explicitly include program name in query
    if query_intent == "certification" and detected_programs:
        valid_programs = [p for p in detected_programs if p in PROGRAM_SYNONYMS]
        if valid_programs:
            # Add program name variations to keywords
            for prog_id in valid_programs:
                prog_info = PROGRAM_SYNONYMS.get(prog_id, {})
                aliases = prog_info.get("aliases", [])
                if aliases:
                    keywords += " " + " ".join(aliases[:2])  # Add first 2 aliases

    retrieval_query = f"{enhanced_query} | KEYWORDS: {keywords}".strip()

    # Determine top_k based on query type and iteration
    # Strategy: 30 → 50 on refetch (2 attempts max, efficient API usage)
    top_k = 30
    if query_intent == "comparison":
        top_k = 50  # Comparison queries need max docs upfront
    elif query_intent == "certification":
        top_k = 30  # Certification queries need universal doc + program doc
    if state.get("is_portfolio_wide", False):
        top_k = 50  # Portfolio-wide questions need chunks from every program
    if "EXPAND_CHUNKS" in refinement_strategy:
        top_k = 40 if iteration_count == 1 else 50

    # Jump to max if this is a re-fetch after filtering removed too many docs
    refetch_count = state.get("metadata", {}).get("refetch_count", 0)
    if refetch_count > 0:
        top_k = 50  # Max out on first refetch (30 → 50, or 40 → 50)
        logger.info(f"Re-fetch attempt {refetch_count}: using top_k={top_k}")

    logger.info(f"Retrieval Query: {retrieval_query[:100]}...")
    logger.info(f"Top-K: {top_k} | Namespace Filter: {namespace_filter}")
    logger.info(f"Vector Store ID: {VECTOR_STORE_ID}")

    # Validate vector store ID
    if not VECTOR_STORE_ID or VECTOR_STORE_ID == "vs_xxx":
        logger.error(f"❌ Invalid vector store ID: {VECTOR_STORE_ID}")
        return {
            **state,
            "retrieval_query": retrieval_query,
            "retrieved_docs": [],
            "retrieval_stats": {"error": "Invalid vector store ID"}
        }

    # Perform vector search using OpenAI's Responses API (same as working system)
    try:
        # Use OpenAI's Responses API for vector search (non-deprecated approach)
        instructions = """Retrieve relevant curriculum information from the knowledge base. Focus on:
- Program details (duration, topics, technologies)
- Specific course content and learning objectives
- Prerequisites and requirements
- Certifications and outcomes
- Exact quotes from curriculum documents when possible"""

        # Apply namespace filtering through instructions if needed
        # Portfolio-wide questions must NOT be scoped to one program - the answer
        # is the list of programs where the topic appears
        if detected_programs and not state.get("is_portfolio_wide", False):
            # Filter out non-program IDs like "certifications"
            valid_program_hints = [p for p in detected_programs if p in PROGRAM_SYNONYMS]
            if valid_program_hints:
                program_names = []
                for prog_id in valid_program_hints:
                    prog_info = PROGRAM_SYNONYMS.get(prog_id, {})
                    # Get the main program name
                    filenames = prog_info.get("filenames", [])
                    if filenames:
                        program_names.append(filenames[0].replace("_", " ").replace(".txt", "").replace(".md", ""))
                    else:
                        program_names.append(prog_id.replace("_", " "))

                instructions = f"PROGRAM_HINT: {', '.join(program_names)}\n\n" + instructions

        # For certification queries, emphasize finding specific certification names
        if query_intent == "certification":
            valid_programs = [p for p in detected_programs if p in PROGRAM_SYNONYMS]
            if valid_programs:
                prog_info = PROGRAM_SYNONYMS.get(valid_programs[0], {})
                aliases = prog_info.get("aliases", [])
                program_name = aliases[0] if aliases else valid_programs[0].replace("_", " ")
                instructions += f"\n\nIMPORTANT: For certification queries, retrieve chunks from the Certifications document that specifically mention '{program_name}' or related program name variations. Look for chunks containing specific certification names and their issuing organizations."

        logger.info(f"🔍 Calling OpenAI Responses API with vector store search...")
        resp = openai_client.responses.create(
            model=MODEL_FAST,
            input=[{"role": "user", "content": retrieval_query}],
            instructions=instructions,
            tools=[{
                "type": "file_search",
                "vector_store_ids": [VECTOR_STORE_ID],
                "max_num_results": top_k
            }],
            tool_choice={"type": "file_search"},
            include=["file_search_call.results"],
            # We only consume the search results; capping the (discarded) text
            # answer halves call latency (~22s -> ~11s measured, same results)
            max_output_tokens=64,
            timeout=30,
        )

        logger.info(f"✅ Received response from OpenAI Responses API")
        logger.debug(f"Response type: {type(resp)}")
        logger.debug(f"Response attributes: {dir(resp)}")

        # Extract hits from response (same logic as working system)
        hits = []
        response_output = getattr(resp, "output", [])
        logger.info(f"Response output structure: {type(response_output)}, length: {len(response_output) if response_output else 0}")

        for out in response_output:
            res = getattr(out, "results", None)
            if res:
                hits = res
                logger.info(f"Found hits in output.results: {len(hits)}")
                break
            fsc = getattr(out, "file_search_call", None)
            if fsc:
                if getattr(fsc, "results", None):
                    hits = fsc.results
                    logger.info(f"Found hits in file_search_call.results: {len(hits)}")
                    break
                if getattr(fsc, "search_results", None):
                    hits = fsc.search_results
                    logger.info(f"Found hits in file_search_call.search_results: {len(hits)}")
                    break

        # Also check response-level attributes
        if not hits:
            if hasattr(resp, "results"):
                hits = resp.results
                logger.info(f"Found hits in response.results: {len(hits)}")
            elif hasattr(resp, "file_search_call"):
                fsc = resp.file_search_call
                if hasattr(fsc, "results"):
                    hits = fsc.results
                    logger.info(f"Found hits in response.file_search_call.results: {len(hits)}")

        logger.info(f"Total hits extracted from vector store: {len(hits)}")

        # Process hits into retrieved_docs format
        retrieved_docs = []
        for idx, r in enumerate(hits):
            fname = getattr(r, "filename", None) or getattr(getattr(r, "document", None), "filename", None)
            fid = getattr(r, "file_id", None) or getattr(getattr(r, "document", None), "id", None)
            score = float(getattr(r, "score", 0.0) or 0.0)

            text = ""
            if hasattr(r, "text") and r.text:
                text = r.text
            elif hasattr(r, "content") and r.content:
                text = r.content
            elif hasattr(r, "document") and hasattr(r.document, "content"):
                text = r.document.content

            if text and len(text.strip()) > 50:  # Minimum content length
                retrieved_docs.append({
                    "content": text.strip(),
                    "source": fname or fid or "unknown",
                    "quote": text[:200] + "..." if len(text) > 200 else text,
                    "score": score
                })
                logger.debug(f"Processed hit {idx+1}: source={fname or fid}, score={score:.3f}, length={len(text)}")
            else:
                logger.warning(f"Skipped hit {idx+1}: insufficient content (length={len(text) if text else 0})")

        logger.info(f"Successfully processed {len(retrieved_docs)} documents from vector store")

        # Log warning if no hits found - system will handle empty results gracefully
        if not retrieved_docs:
            logger.warning(f"⚠️  Vector store returned no results for query: {retrieval_query[:100]}")
            logger.warning(f"⚠️  Vector Store ID: {VECTOR_STORE_ID}")
            logger.warning(f"⚠️  System will handle empty results gracefully (no fake documents generated)")

        retrieval_stats = {
            "total_retrieved": len(retrieved_docs),
            "top_k": top_k,
            "namespace_filter_applied": namespace_filter is not None,
            "programs_targeted": detected_programs,
            "vector_store_used": True,
            "fallback_used": False
        }

        if retrieved_docs:
            logger.info(f"✅ Retrieved {len(retrieved_docs)} documents from vector store")
            # Log sample sources
            sources = [doc.get("source", "unknown") for doc in retrieved_docs[:3]]
            logger.info(f"   Sample sources: {', '.join(sources)}")
        else:
            logger.warning(f"⚠️  No documents retrieved from vector store")

    except Exception as e:
        logger.error(f"❌ Vector store retrieval failed: {e}")
        logger.error(f"❌ Query: {retrieval_query[:100]}")
        logger.error(f"❌ Vector Store ID: {VECTOR_STORE_ID}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

        # Return empty results - system will handle gracefully (no fake documents)
        retrieved_docs = []
        retrieval_stats = {
            "error": str(e),
            "fallback_used": False,
            "total_retrieved": 0
        }
        logger.warning(f"⚠️  Returning empty results - system will handle gracefully")

    # For breakdown/overview questions, top-k chunks only surface fragments of the
    # curriculum (users got weeks 5-6 of a 9-week program). Prepend the complete
    # syllabus document(s) from the local knowledge base so generation sees the
    # whole structure. Flagged full_syllabus=True so filtering keeps them.
    if state.get("is_breakdown_request", False):
        valid_programs = [p for p in detected_programs if p in PROGRAM_SYNONYMS]
        if valid_programs:
            full_docs = load_full_syllabus_docs(valid_programs, PROGRAM_SYNONYMS)
            if full_docs:
                retrieved_docs = full_docs + retrieved_docs
                retrieval_stats["full_syllabus_docs"] = [d["source"] for d in full_docs]
                logger.info(f"Prepended {len(full_docs)} full syllabus doc(s) for breakdown request")

    return {
        **state,
        "retrieval_query": retrieval_query,
        "retrieved_docs": retrieved_docs,
        "retrieval_stats": retrieval_stats
    }
