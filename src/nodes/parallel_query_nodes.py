"""
Parallel Query Nodes

Nodes for parallel execution of query enhancement and program detection.

Performance Measurements (Integration Test - 2026-02-10):
- Sequential execution: ~5.71s (query_enhancement: ~2.50s + program_detection: ~3.21s)
- Parallel execution: ~3.22s (max of individual node times)
- Speedup: 1.8x faster
- Time saved: ~2.5s per query (44% improvement)

This aligns with the expected 30-40% improvement from the spec.
The parallel execution time is limited by the slower of the two nodes.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.state import RAGState
from src.nodes.query_nodes import query_enhancement_node, program_detection_node


logger = logging.getLogger(__name__)


def parallel_query_processing_node(state: RAGState) -> RAGState:
    """
    Execute query enhancement and program detection in parallel to reduce latency.

    This node improves performance by running two independent OpenAI API calls concurrently:
    - query_enhancement: Disambiguates and enhances the user query
    - program_detection: Identifies which programs the query is about

    Parallelization Strategy:
    - Both nodes are executed using ThreadPoolExecutor with 2 workers
    - Each node operates on the same base state (original query + conversation history)
    - program_detection can run independently because it has fallback logic (uses original query if enhanced_query unavailable)
    - Results are merged after both nodes complete

    Performance Improvement:
    - Sequential: ~5.7s (sum of both node execution times)
    - Parallel: ~3.2s (limited by the slower node)
    - Speedup: ~1.8x faster (44% time saved per query)

    Error Handling:
    - If one node fails, the other continues and succeeds
    - Fallback values are used for failed nodes
    - Errors are logged and stored in state metadata
    """
    logger.info("=== Parallel Query Processing Node ===")

    start_time = time.perf_counter()

    # Create a snapshot of the state for both nodes to use
    # This ensures both nodes work with consistent input data
    base_state = state.copy()

    # Track individual node execution times for performance analysis
    node_times = {}

    # Wrapper function to execute query_enhancement with error handling and timing
    # Returns a dict with success status, result (or error), and execution time
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

    # Wrapper function to execute program_detection with error handling and timing
    # Returns a dict with success status, result (or error), and execution time
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
    # This allows both OpenAI API calls to run simultaneously instead of sequentially
    results = {}
    errors = []

    # Use 2 workers since we have exactly 2 independent tasks
    max_workers = 2
    logger.info(f"Parallelizing query processing: query_enhancement and program_detection with {max_workers} workers")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit both tasks to the thread pool
        # executor.submit() schedules the function to run in a separate thread
        # We get a Future object that will eventually contain the result
        future_to_node = {
            executor.submit(run_query_enhancement): "query_enhancement",
            executor.submit(run_program_detection): "program_detection"
        }

        # Collect results as they complete using as_completed
        # as_completed yields futures as they finish (order not guaranteed)
        # This ensures we process results as soon as each node completes
        for future in as_completed(future_to_node):
            node_name = future_to_node[future]
            try:
                result = future.result()
                results[node_name] = result

                if result["success"]:
                    # Track successful execution time for performance metrics
                    node_times[node_name] = result["duration"]
                    logger.info(f"{node_name} completed in {result['duration']:.2f}s")
                else:
                    # Record error but continue processing - the other node may succeed
                    errors.append(f"{node_name}: {result['error']}")
                    # Store error result with None values for merging
                    results[node_name] = result

            except Exception as e:
                logger.error(f"Future failed for {node_name}: {e}")
                errors.append(f"{node_name}: {str(e)}")

    # Merge results from both nodes into final state
    # Start with original state to preserve all existing fields
    final_state = state.copy()

    # Merge query_enhancement results if successful, otherwise use fallback values
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

    # Merge program_detection results if successful, otherwise use fallback values
    if results.get("program_detection", {}).get("success"):
        pd_result = results["program_detection"]["result"]
        final_state["detected_programs"] = pd_result.get("detected_programs", [])
        final_state["namespace_filter"] = pd_result.get("namespace_filter")
    else:
        # Fallback to defaults if program_detection failed
        logger.warning("Program detection failed, using fallback values")
        final_state["detected_programs"] = []
        final_state["namespace_filter"] = None

    # Calculate total wall-clock time for the parallel execution
    # This should be close to max(individual times), not sum(individual times)
    total_duration = time.perf_counter() - start_time

    # Log performance summary to validate parallelization effectiveness
    if node_times:
        qa_time = node_times.get("query_enhancement", 0)
        pd_time = node_times.get("program_detection", 0)
        sequential_time = qa_time + pd_time
        speedup = (sequential_time / total_duration) if total_duration > 0 else 1.0

        # Log detailed metrics: parallel time, individual times, and calculated speedup
        logger.info(
            f"Parallel query processing: {total_duration:.2f}s "
            f"(query_enhancement: {qa_time:.2f}s, program_detection: {pd_time:.2f}s) "
            f"| Speedup: {speedup:.1f}x"
        )

    # If any errors occurred, log them and store in metadata for debugging
    if errors:
        logger.warning(f"Parallel execution completed with errors: {errors}")
        final_state["metadata"] = final_state.get("metadata", {})
        final_state["metadata"]["parallel_errors"] = errors

    return final_state
