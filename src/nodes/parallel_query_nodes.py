"""
Parallel Query Nodes

Nodes for parallel execution of query enhancement and program detection.
This reduces the query phase from ~4s sequential to ~2-2.5s parallel.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.state import RAGState
from src.query_nodes import query_enhancement_node, program_detection_node
from src.slack_helpers import send_slack_update


logger = logging.getLogger(__name__)


def parallel_query_processing_node(state: RAGState) -> RAGState:
    """
    Execute query_enhancement and program_detection in parallel using ThreadPoolExecutor.

    These two nodes are independent because:
    - query_enhancement operates on the original query and conversation history
    - program_detection has fallback logic (enhanced_query -> query) and can use the original query

    Performance improvement: ~4s sequential -> ~2-2.5s parallel (30-40% faster)
    """
    logger.info("=== Parallel Query Processing Node ===")
    send_slack_update(state, "Analyzing your question")

    start_time = time.perf_counter()

    # Extract base state needed by both nodes
    base_state = state.copy()

    # Track individual node execution times
    node_times = {}

    def run_query_enhancement():
        """Execute query_enhancement_node with timing."""
        node_start = time.perf_counter()
        try:
            result = query_enhancement_node(base_state)
            node_duration = time.perf_counter() - node_start
            return {"success": True, "result": result, "duration": node_duration, "node": "query_enhancement"}
        except Exception as e:
            node_duration = time.perf_counter() - node_start
            logger.error(f"Query enhancement failed: {e}")
            return {"success": False, "error": str(e), "duration": node_duration, "node": "query_enhancement"}

    def run_program_detection():
        """Execute program_detection_node with timing."""
        node_start = time.perf_counter()
        try:
            result = program_detection_node(base_state)
            node_duration = time.perf_counter() - node_start
            return {"success": True, "result": result, "duration": node_duration, "node": "program_detection"}
        except Exception as e:
            node_duration = time.perf_counter() - node_start
            logger.error(f"Program detection failed: {e}")
            return {"success": False, "error": str(e), "duration": node_duration, "node": "program_detection"}

    # Execute both nodes in parallel using ThreadPoolExecutor
    results = {}
    errors = []

    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both tasks
        future_to_node = {
            executor.submit(run_query_enhancement): "query_enhancement",
            executor.submit(run_program_detection): "program_detection"
        }

        # Collect results as they complete
        for future in as_completed(future_to_node):
            node_name = future_to_node[future]
            try:
                result = future.result()
                results[node_name] = result

                if result["success"]:
                    node_times[node_name] = result["duration"]
                    logger.info(f"{node_name} completed in {result['duration']:.2f}s")
                else:
                    errors.append(f"{node_name}: {result['error']}")
                    # Store error result with None values for merging
                    results[node_name] = result

            except Exception as e:
                logger.error(f"Future failed for {node_name}: {e}")
                errors.append(f"{node_name}: {str(e)}")

    # Merge results from both nodes into final state
    # Start with original state
    final_state = state.copy()

    # Merge query_enhancement results
    if results.get("query_enhancement", {}).get("success"):
        qa_result = results["query_enhancement"]["result"]
        final_state["enhanced_query"] = qa_result.get("enhanced_query", state.get("query", ""))
        final_state["query_intent"] = qa_result.get("query_intent", "general_info")
        final_state["ambiguity_score"] = qa_result.get("ambiguity_score", 0.5)
    else:
        # Fallback to defaults if query_enhancement failed
        logger.warning("Query enhancement failed, using fallback values")
        final_state["enhanced_query"] = state.get("query", "")
        final_state["query_intent"] = "general_info"
        final_state["ambiguity_score"] = 0.5

    # Merge program_detection results
    if results.get("program_detection", {}).get("success"):
        pd_result = results["program_detection"]["result"]
        final_state["detected_programs"] = pd_result.get("detected_programs", [])
        final_state["namespace_filter"] = pd_result.get("namespace_filter")
    else:
        # Fallback to defaults if program_detection failed
        logger.warning("Program detection failed, using fallback values")
        final_state["detected_programs"] = []
        final_state["namespace_filter"] = None

    # Calculate total wall-clock time
    total_duration = time.perf_counter() - start_time

    # Log performance summary
    if node_times:
        qa_time = node_times.get("query_enhancement", 0)
        pd_time = node_times.get("program_detection", 0)
        sequential_time = qa_time + pd_time
        speedup = (sequential_time / total_duration) if total_duration > 0 else 1.0

        logger.info(
            f"Parallel query processing: {total_duration:.2f}s "
            f"(query_enhancement: {qa_time:.2f}s, program_detection: {pd_time:.2f}s) "
            f"| Speedup: {speedup:.1f}x"
        )

    if errors:
        logger.warning(f"Parallel execution completed with errors: {errors}")
        final_state["metadata"] = final_state.get("metadata", {})
        final_state["metadata"]["parallel_errors"] = errors

    return final_state
