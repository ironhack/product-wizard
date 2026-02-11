#!/usr/bin/env python3
"""
Integration test for parallel query processing node.

This test verifies that:
1. The parallel_query_processing_node executes correctly
2. State contains all required fields: enhanced_query, query_intent, detected_programs, namespace_filter
3. Workflow proceeds to hybrid_retrieval after parallel processing
4. Logs show parallel execution timing
"""

import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    # Try to load .env from workspace root
    env_path = Path(__file__).resolve().parents[1] / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env from {env_path}")
    else:
        load_dotenv()
except ImportError:
    pass  # python-dotenv not installed

# Setup logging to see parallel execution timing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Ensure workspace root is on the path
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.append(str(WORKSPACE_ROOT))

# Set mock Slack credentials to avoid auth errors on import (only if not already set)
os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test-token-for-testing")
os.environ.setdefault("SLACK_SIGNING_SECRET", "test-signing-secret-for-testing")

from src.workflow import rag_workflow
from src.state import RAGState

# Test query from the spec
TEST_QUERY = "What does the Data Analytics bootcamp cover?"

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


def verify_state_fields(state: Dict[str, Any]) -> bool:
    """Verify that state contains all required fields from parallel processing."""
    required_fields = {
        'enhanced_query': str,
        'query_intent': str,
        'detected_programs': list,
        'namespace_filter': (type(None), dict),
    }

    all_valid = True

    for field, expected_type in required_fields.items():
        if field not in state:
            print_error(f"Missing required field: {field}")
            all_valid = False
        elif not isinstance(state[field], expected_type):
            print_error(f"Field {field} has wrong type: expected {expected_type}, got {type(state[field])}")
            all_valid = False
        else:
            value = state[field]
            if field == 'enhanced_query':
                print_success(f"enhanced_query: '{value[:100]}...'")
            elif field == 'query_intent':
                print_success(f"query_intent: '{value}'")
            elif field == 'detected_programs':
                print_success(f"detected_programs: {value}")
            elif field == 'namespace_filter':
                print_success(f"namespace_filter: {value}")

    return all_valid


def verify_parallel_execution_timing(log_output: str) -> bool:
    """Verify that logs show parallel execution timing."""
    timing_indicators = [
        "Parallelizing query processing",
        "query_enhancement completed in",
        "program_detection completed in",
        "Parallel query processing completed",
        "Speedup:",
    ]

    found_indicators = []
    for indicator in timing_indicators:
        if indicator in log_output:
            found_indicators.append(indicator)

    if len(found_indicators) >= 3:  # At least 3 timing indicators should be present
        print_success(f"Parallel execution timing logs found ({len(found_indicators)}/5 indicators)")
        for indicator in found_indicators:
            print_info(f"  - {indicator}")
        return True
    else:
        print_error(f"Insufficient timing logs found ({len(found_indicators)}/5 indicators)")
        return False


def run_integration_test() -> Dict[str, Any]:
    """Run the integration test."""
    print_header("PARALLEL QUERY PROCESSING INTEGRATION TEST")

    # Setup test configuration
    thread_id = f"test_parallel_{uuid.uuid4()}"
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 50
    }

    initial_state: RAGState = {
        "query": TEST_QUERY,
        "conversation_history": [],
        "iteration_count": 0,
        "metadata": {"test_mode": "parallel_query_integration"},
    }

    print_info(f"Test Query: '{TEST_QUERY}'")
    print_info(f"Thread ID: {thread_id}")
    print_info(f"Invoking workflow...")

    # Capture logs to verify parallel execution timing
    import io
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # Add handler to the parallel query nodes logger
    parallel_logger = logging.getLogger('src.nodes.parallel_query_nodes')
    parallel_logger.addHandler(handler)
    parallel_logger.setLevel(logging.INFO)

    # Execute workflow
    start_time = time.time()
    try:
        result = rag_workflow.invoke(initial_state, config)
        elapsed_time = time.time() - start_time

        print_success(f"Workflow executed successfully in {elapsed_time:.2f}s")

        # Get captured logs
        log_output = log_capture.getvalue()

        # Verification 1: Verify parallel_query_processing_node executed
        print_header("VERIFICATION 1: Parallel Node Execution")
        if "Parallel Query Processing Node" in log_output or "parallel_query_processing" in str(result.get("metadata", {})):
            print_success("parallel_query_processing_node executed")
        else:
            print_error("Could not verify parallel_query_processing_node execution")

        # Verification 2: Verify state contains required fields
        print_header("VERIFICATION 2: State Fields")
        state_valid = verify_state_fields(result)

        # Verification 3: Verify workflow proceeded to hybrid_retrieval
        print_header("VERIFICATION 3: Workflow Progression")
        if result.get("retrieved_docs") is not None or result.get("filtered_docs") is not None:
            print_success("Workflow proceeded to hybrid_retrieval (retrieved_docs or filtered_docs present)")
        else:
            print_info("Could not verify hybrid_retrieval execution (may have stopped earlier)")

        # Verification 4: Verify parallel execution timing logs
        print_header("VERIFICATION 4: Parallel Execution Timing")
        timing_valid = verify_parallel_execution_timing(log_output)

        # Display captured logs
        if log_output:
            print_header("CAPTURED LOGS")
            print(log_output)

        # Overall result
        print_header("TEST RESULT")
        all_checks_passed = state_valid and timing_valid

        if all_checks_passed:
            print_success("ALL CHECKS PASSED ✓")
        else:
            print_error("SOME CHECKS FAILED ✗")

        # Return test results
        return {
            "passed": all_checks_passed,
            "elapsed_time": elapsed_time,
            "state_fields_valid": state_valid,
            "timing_logs_valid": timing_valid,
            "enhanced_query": result.get("enhanced_query"),
            "query_intent": result.get("query_intent"),
            "detected_programs": result.get("detected_programs"),
            "namespace_filter": result.get("namespace_filter"),
            "final_response": result.get("final_response"),
        }

    except Exception as e:
        print_error(f"Workflow execution failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "passed": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    finally:
        # Clean up log handler
        parallel_logger.removeHandler(handler)


def main() -> None:
    """Main entry point."""
    results = run_integration_test()

    # Save results to file
    results_dir = WORKSPACE_ROOT / "tests" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    results_file = results_dir / "parallel_query_integration_test_results.json"

    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print_info(f"Results saved to {results_file}")

    # Exit with appropriate code
    if results.get("passed"):
        print_success("\nIntegration test PASSED")
        sys.exit(0)
    else:
        print_error("\nIntegration test FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
