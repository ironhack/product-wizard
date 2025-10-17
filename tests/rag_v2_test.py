"""
RAG v2 Architecture Test Suite
Test the best-practice RAG implementation with real queries
"""

import sys
import os
import json
from datetime import datetime
from typing import List, Dict, Any
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
from contextlib import redirect_stdout

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

# Set mock Slack environment variables before importing (prevents Slack auth errors)
os.environ['SLACK_BOT_TOKEN'] = 'xoxb-test-token-for-testing'
os.environ['SLACK_SIGNING_SECRET'] = 'test-signing-secret-for-testing'

from app_rag_v2 import rag_workflow

def test_rag_v2(query: str, description: str):
    """Test RAG v2 with a specific query."""
    print(f"\n{'='*80}")
    print(f"TEST: {description}")
    print(f"Query: {query}")
    print(f"{'='*80}\n")
    
    try:
        # Run the workflow
        config = {"configurable": {"thread_id": f"test_{datetime.now().timestamp()}"}}
        initial_state = {
            "query": query,
            "conversation_history": [],
            "iteration_count": 0,
            "metadata": {}
        }
        
        print("Running RAG v2 workflow...\n")
        result = rag_workflow.invoke(initial_state, config)
        
        # Display results
        print("RESULTS:")
        print(f"\nFinal Response:\n{result.get('final_response', 'No response')}\n")
        
        print("\nPipeline Metrics:")
        print(f"  - Enhanced Query: {result.get('enhanced_query', 'N/A')}")
        print(f"  - Query Intent: {result.get('query_intent', 'N/A')}")
        print(f"  - Detected Programs: {result.get('detected_programs', [])}")
        print(f"  - Documents Retrieved: {len(result.get('retrieved_docs', []))}")
        print(f"  - Documents After Filtering: {len(result.get('filtered_docs', []))}")
        print(f"  - Coverage Question: {result.get('is_coverage_question', False)}")
        print(f"  - Faithfulness Score: {result.get('faithfulness_score', 0.0):.2f}")
        print(f"  - Is Grounded: {result.get('is_grounded', False)}")
        print(f"  - Is Fallback: {result.get('is_fallback', False)}")
        print(f"  - Iterations: {result.get('iteration_count', 0)}")
        print(f"  - Source Citations: {len(result.get('source_citations', []))}")
        
        if result.get('faithfulness_violations'):
            print(f"\nFaithfulness Violations:")
            for violation in result.get('faithfulness_violations', []):
                print(f"  - {violation}")
        
        print("\nMetadata:")
        print(json.dumps(result.get('metadata', {}), indent=2))
        
        return result
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_tests() -> List[Dict[str, Any]]:
    """Return the list of tests."""
    return [
        {
            "query": "Does Data Analytics teach Python?",
            "description": "Coverage Question - Program Isolation Test",
            "expected": "Should detect as coverage question, search only Data Analytics docs, verify Python presence"
        },
        {
            "query": "Does Data Analytics include machine learning?",
            "description": "Negative Coverage - Cross-Contamination Prevention",
            "expected": "Should NOT mix Data Science content, clear 'No' answer"
        },
        {
            "query": "What programming languages are taught in Web Development?",
            "description": "Technical Detail Query - Namespace Filtering",
            "expected": "Should filter to Web Dev docs only, list JavaScript, React, Node.js"
        },
        {
            "query": "What's the difference between Data Analytics and Data Science?",
            "description": "Comparison Query - Multi-Program Retrieval",
            "expected": "Should retrieve from BOTH programs, balanced comparison"
        },
        {
            "query": "What certifications are available for Web Development graduates?",
            "description": "Certification Query - Multi-Document Type",
            "expected": "Should retrieve from both Certifications doc AND Web Dev doc"
        },
        {
            "query": "How long is the Data Science bootcamp?",
            "description": "Duration Query - Specific Information",
            "expected": "Should find duration information with exact hours/weeks"
        },
        {
            "query": "What do you learn?",
            "description": "Ambiguous Query - Enhancement Test",
            "expected": "High ambiguity score, query enhancement should improve it"
        },
        {
            "query": "Tell me about machine learning frameworks in the DS bootcamp",
            "description": "Technology Stack - Faithfulness Test",
            "expected": "Should mention TensorFlow, scikit-learn, etc. with high faithfulness score"
        }
    ]

def run_single_test(test: Dict[str, Any]) -> Dict[str, Any]:
    """Run a single test case and capture its stdout to avoid interleaving."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        print(f"\n\nExpected Behavior: {test['expected']}")
        result = test_rag_v2(test['query'], test['description'])
        print("\n" + "-"*80 + "\n")
    output = buf.getvalue()
    return {
        "test": test['description'],
        "query": test['query'],
        "result": result,
        "expected": test['expected'],
        "output": output,
    }

def summarize_results(results: List[Dict[str, Any]]):
    print("\n" + "="*80)
    print("TEST SUITE SUMMARY")
    print("="*80)
    for idx, test_result in enumerate(results, 1):
        result = test_result['result']
        if result:
            status = "✅ COMPLETED"
            grounded = "✅" if result.get('is_grounded', False) else "❌"
            fallback = "❌" if result.get('is_fallback', False) else "✅"
        else:
            status = "❌ FAILED"
            grounded = "❌"
            fallback = "❌"
        print(f"\n{idx}. {test_result['test']}")
        print(f"   Status: {status}")
        print(f"   Grounded: {grounded} | No Fallback: {fallback}")
        print(f"   Expected: {test_result['expected']}")
    print("\n" + "="*80)
    print("Please manually evaluate the responses above:")
    print("1. Were documents properly isolated (no cross-contamination)?")
    print("2. Were coverage questions handled correctly?")
    print("3. Are responses well-grounded in source documents?")
    print("4. Did comparisons retrieve from multiple programs?")
    print("5. Were citations accurate and complete?")
    print("="*80 + "\n")

def run_test_suite(parallel: bool = False, workers: int = 4):
    """Run comprehensive test suite, optionally in parallel."""
    print("\n" + "="*80)
    print("RAG V2 ARCHITECTURE - COMPREHENSIVE TEST SUITE")
    print("="*80)

    tests = get_tests()

    results: List[Dict[str, Any]] = []

    if parallel:
        # Run tests concurrently, capture outputs, then print in order of completion
        futures = []
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            for test in tests:
                futures.append(executor.submit(run_single_test, test))
            for fut in as_completed(futures):
                res = fut.result()
                # Print the captured output of each test as it completes
                print(res["output"], end="")
                results.append({k: v for k, v in res.items() if k != "output"})
    else:
        # Sequential execution (original behavior)
        for test in tests:
            res = run_single_test(test)
            print(res["output"], end="")
            results.append({k: v for k, v in res.items() if k != "output"})

    summarize_results(results)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAG v2 Test Suite")
    parser.add_argument("--parallel", action="store_true", help="Run tests in parallel")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
    parser.add_argument("--manual", type=str, help="Test a specific manual question")
    args = parser.parse_args()
    
    if args.manual:
        # Run manual test
        print(f"Running manual test: {args.manual}")
        test_rag_v2(args.manual, "Manual Test")
    else:
        # Run full test suite
        run_test_suite(parallel=args.parallel, workers=args.workers)

