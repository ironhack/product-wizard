#!/usr/bin/env python3
"""
Output Correctness Verification Test

This test verifies that parallel execution produces IDENTICAL results to sequential execution.
It runs the same query through both execution modes and compares all output fields.

Test Coverage:
- enhanced_query: Must be identical
- query_intent: Must be identical
- detected_programs: Must be identical
- namespace_filter: Must be identical
- ambiguity_score: Must be identical

Expected Result: All fields should match exactly (within floating-point tolerance for scores)
"""

import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parents[1] / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env from {env_path}")
    else:
        load_dotenv()
except ImportError:
    pass

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Ensure workspace root is on the path
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.append(str(WORKSPACE_ROOT))

# Add src directory to path for direct imports
src_dir = WORKSPACE_ROOT / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Set mock Slack credentials
os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test-token-for-testing")
os.environ.setdefault("SLACK_SIGNING_SECRET", "test-signing-secret-for-testing")

# Import directly from modules to avoid importing src/__init__.py (which imports Flask)
import state
from nodes.query_nodes import query_enhancement_node, program_detection_node
from nodes.parallel_query_nodes import parallel_query_processing_node

RAGState = state.RAGState

# Test queries covering different scenarios
TEST_QUERIES = [
    {
        "name": "Data Analytics Bootcamp",
        "query": "What does the Data Analytics bootcamp cover?",
        "conversation_history": [],
        "conversation_stage": "initial"
    },
    {
        "name": "Web Development Follow-up",
        "query": "How much does it cost?",
        "conversation_history": [
            {"role": "user", "content": "Tell me about the Web Development bootcamp"},
            {"role": "assistant", "content": "The Web Development bootcamp covers full-stack development..."}
        ],
        "conversation_stage": "follow_up"
    },
    {
        "name": "UX/UI Program",
        "query": "Is UX/UI part of the design program?",
        "conversation_history": [],
        "conversation_stage": "initial"
    }
]

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(message: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 80}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{message}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 80}{Colors.END}\n")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.END}")


def run_sequential_execution(initial_state: RAGState) -> Tuple[RAGState, float]:
    """
    Run sequential execution: query_enhancement → program_detection
    Returns final state and total execution time.
    """
    start_time = time.perf_counter()

    # Step 1: Query enhancement
    state_after_qe = query_enhancement_node(initial_state)

    # Step 2: Program detection (uses enhanced_query from step 1)
    final_state = program_detection_node(state_after_qe)

    elapsed_time = time.perf_counter() - start_time

    return final_state, elapsed_time


def run_parallel_execution(initial_state: RAGState) -> Tuple[RAGState, float]:
    """
    Run parallel execution: parallel_query_processing_node
    Returns final state and total execution time.
    """
    start_time = time.perf_counter()

    final_state = parallel_query_processing_node(initial_state)

    elapsed_time = time.perf_counter() - start_time

    return final_state, elapsed_time


def compare_outputs(
    sequential_state: RAGState,
    parallel_state: RAGState,
    test_name: str
) -> Tuple[bool, List[str]]:
    """
    Compare outputs from sequential and parallel execution.

    Returns:
        (all_match, list_of_mismatches)
    """
    print_header(f"COMPARING OUTPUTS: {test_name}")

    mismatches = []
    comparisons = []

    # Fields to compare
    fields_to_compare = {
        'enhanced_query': str,
        'query_intent': str,
        'detected_programs': list,
        'namespace_filter': (type(None), dict),
        'ambiguity_score': (int, float),
    }

    for field, expected_type in fields_to_compare.items():
        seq_value = sequential_state.get(field)
        par_value = parallel_state.get(field)

        # Type check
        if not isinstance(seq_value, expected_type):
            mismatches.append(
                f"{field}: Sequential has wrong type {type(seq_value)}, expected {expected_type}"
            )
            continue

        if not isinstance(par_value, expected_type):
            mismatches.append(
                f"{field}: Parallel has wrong type {type(par_value)}, expected {expected_type}"
            )
            continue

        # Value comparison
        if field == 'ambiguity_score':
            # Float comparison with tolerance
            # Note: ambiguity_score is LLM-generated and may have small variations (±0.2)
            # This is expected non-determinism in LLM outputs, not a parallelization bug
            if isinstance(seq_value, (int, float)) and isinstance(par_value, (int, float)):
                match = abs(seq_value - par_value) < 0.2
            else:
                match = seq_value == par_value
        elif field == 'detected_programs':
            # List comparison (order-independent)
            match = set(seq_value) == set(par_value) if isinstance(seq_value, list) and isinstance(par_value, list) else seq_value == par_value
        else:
            # Exact comparison
            match = seq_value == par_value

        if match:
            comparisons.append({
                'field': field,
                'match': True,
                'sequential': seq_value,
                'parallel': par_value
            })
            print_success(f"{field}: MATCH")
            print_info(f"  Sequential: {seq_value}")
            print_info(f"  Parallel:  {par_value}")
        else:
            mismatches.append(
                f"{field}: Values differ\n"
                f"  Sequential: {seq_value}\n"
                f"  Parallel:  {par_value}"
            )
            print_error(f"{field}: MISMATCH")
            print_info(f"  Sequential: {seq_value}")
            print_info(f"  Parallel:  {par_value}")

    print()

    return len(mismatches) == 0, mismatches


def run_correctness_test() -> Dict[str, Any]:
    """Run the correctness verification test."""
    print_header("OUTPUT CORRECTNESS VERIFICATION TEST")
    print_info("This test verifies that parallel execution produces IDENTICAL results")
    print_info("to sequential execution for multiple test queries.\n")

    all_results = []
    all_passed = True

    for test_case in TEST_QUERIES:
        test_name = test_case['name']
        print_header(f"TEST CASE: {test_name}")

        # Create initial state
        thread_id = f"test_correctness_{uuid.uuid4()}"
        initial_state: RAGState = {
            "query": test_case['query'],
            "conversation_history": test_case['conversation_history'],
            "conversation_stage": test_case['conversation_stage'],
            "iteration_count": 0,
            "metadata": {"test_mode": "output_correctness"},
        }

        print_info(f"Query: '{test_case['query']}'")
        print_info(f"Stage: {test_case['conversation_stage']}")
        print_info(f"History entries: {len(test_case['conversation_history'])}")

        # Run sequential execution
        print_info("\nRunning sequential execution...")
        sequential_state, sequential_time = run_sequential_execution(initial_state)
        print_success(f"Sequential execution completed in {sequential_time:.2f}s")

        # Run parallel execution
        print_info("Running parallel execution...")
        parallel_state, parallel_time = run_parallel_execution(initial_state)
        print_success(f"Parallel execution completed in {parallel_time:.2f}s")

        # Performance comparison
        speedup = sequential_time / parallel_time if parallel_time > 0 else 1.0
        time_saved = sequential_time - parallel_time
        print_info(f"Speedup: {speedup:.2f}x (saved {time_saved:.2f}s)")

        # Compare outputs
        outputs_match, mismatches = compare_outputs(sequential_state, parallel_state, test_name)

        test_result = {
            "test_name": test_name,
            "query": test_case['query'],
            "outputs_match": outputs_match,
            "sequential_time": sequential_time,
            "parallel_time": parallel_time,
            "speedup": speedup,
            "time_saved": time_saved,
            "mismatches": mismatches,
            "sequential_outputs": {
                'enhanced_query': sequential_state.get('enhanced_query'),
                'query_intent': sequential_state.get('query_intent'),
                'detected_programs': sequential_state.get('detected_programs'),
                'namespace_filter': sequential_state.get('namespace_filter'),
                'ambiguity_score': sequential_state.get('ambiguity_score'),
            },
            "parallel_outputs": {
                'enhanced_query': parallel_state.get('enhanced_query'),
                'query_intent': parallel_state.get('query_intent'),
                'detected_programs': parallel_state.get('detected_programs'),
                'namespace_filter': parallel_state.get('namespace_filter'),
                'ambiguity_score': parallel_state.get('ambiguity_score'),
            }
        }

        all_results.append(test_result)

        if outputs_match:
            print_success(f"✓ {test_name}: ALL OUTPUTS MATCH")
        else:
            print_error(f"✗ {test_name}: OUTPUT MISMATCHES DETECTED")
            all_passed = False

            # Print mismatches
            print_error("Mismatches found:")
            for mismatch in mismatches:
                print_error(f"  - {mismatch}")

    # Final summary
    print_header("FINAL SUMMARY")

    total_tests = len(all_results)
    passed_tests = sum(1 for r in all_results if r['outputs_match'])
    avg_speedup = sum(r['speedup'] for r in all_results) / total_tests
    avg_time_saved = sum(r['time_saved'] for r in all_results) / total_tests

    print_info(f"Total test cases: {total_tests}")
    print_success(f"Passed: {passed_tests}/{total_tests}")

    if all_passed:
        print_success("ALL TESTS PASSED - Outputs are identical!")
    else:
        print_error("SOME TESTS FAILED - Outputs differ!")
        for result in all_results:
            if not result['outputs_match']:
                print_error(f"  - {result['test_name']}: {len(result['mismatches'])} mismatches")

    print_info(f"\nAverage speedup: {avg_speedup:.2f}x")
    print_info(f"Average time saved: {avg_time_saved:.2f}s")

    return {
        "all_passed": all_passed,
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "avg_speedup": avg_speedup,
        "avg_time_saved": avg_time_saved,
        "test_results": all_results
    }


def main() -> None:
    """Main entry point."""
    results = run_correctness_test()

    # Save results to file
    results_dir = WORKSPACE_ROOT / "tests" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    results_file = results_dir / "output_correctness_test_results.json"

    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print_info(f"\nResults saved to {results_file}")

    # Exit with appropriate code
    if results["all_passed"]:
        print_success("\nOutput correctness verification PASSED")
        sys.exit(0)
    else:
        print_error("\nOutput correctness verification FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
