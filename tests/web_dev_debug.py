"""
Web Development Query Debug Script
Focus on analyzing why Web Dev queries are failing with "wrong_topic" flags
"""

import sys
import os
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import io
from contextlib import redirect_stdout

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

# Set mock Slack environment variables before importing (prevents Slack auth errors)
os.environ['SLACK_BOT_TOKEN'] = 'xoxb-test-token-for-testing'
os.environ['SLACK_SIGNING_SECRET'] = 'test-signing-secret-for-testing'

from app_rag_v2 import rag_workflow

def debug_web_dev_query(query: str, description: str):
    """Debug a specific Web Development query with detailed logging."""
    print(f"\n{'='*80}")
    print(f"DEBUG: {description}")
    print(f"Query: {query}")
    print(f"{'='*80}\n")
    
    try:
        # Run the workflow
        config = {"configurable": {"thread_id": f"debug_{datetime.now().timestamp()}"}}
        initial_state = {
            "query": query,
            "conversation_history": [],
            "iteration_count": 0,
            "metadata": {}
        }
        
        print("Running RAG v2 workflow...\n")
        result = rag_workflow.invoke(initial_state, config)
        
        # Detailed analysis
        print("DETAILED ANALYSIS:")
        print(f"\n1. Query Enhancement:")
        print(f"   - Original: {query}")
        print(f"   - Enhanced: {result.get('enhanced_query', 'N/A')}")
        print(f"   - Intent: {result.get('query_intent', 'N/A')}")
        print(f"   - Ambiguity: {result.get('ambiguity_score', 'N/A')}")
        
        print(f"\n2. Program Detection:")
        print(f"   - Detected: {result.get('detected_programs', [])}")
        print(f"   - Confidence: {result.get('program_confidence', 'N/A')}")
        
        print(f"\n3. Retrieval Results:")
        retrieved_docs = result.get('retrieved_docs', [])
        print(f"   - Total Retrieved: {len(retrieved_docs)}")
        for i, doc in enumerate(retrieved_docs[:5]):  # Show top 5
            print(f"   - Doc {i+1}: {doc.get('source', 'unknown')}")
            print(f"     Preview: {doc.get('content', '')[:100]}...")
        
        print(f"\n4. Relevance Assessment:")
        relevance_scores = result.get('relevance_scores', [])
        rejection_reasons = result.get('rejection_reasons', [])
        print(f"   - Scores: {relevance_scores}")
        print(f"   - Rejection Reasons: {rejection_reasons}")
        
        print(f"\n5. Document Filtering:")
        filtered_docs = result.get('filtered_docs', [])
        print(f"   - After Filtering: {len(filtered_docs)}")
        for i, doc in enumerate(filtered_docs):
            print(f"   - Doc {i+1}: {doc.get('source', 'unknown')}")
            print(f"     Preview: {doc.get('content', '')[:100]}...")
        
        print(f"\n6. Coverage Classification:")
        print(f"   - Is Coverage Question: {result.get('is_coverage_question', False)}")
        
        print(f"\n7. Final Response:")
        print(f"   - Response: {result.get('final_response', 'No response')}")
        print(f"   - Faithfulness Score: {result.get('faithfulness_score', 0.0):.2f}")
        print(f"   - Is Grounded: {result.get('is_grounded', False)}")
        print(f"   - Is Fallback: {result.get('is_fallback', False)}")
        
        if result.get('faithfulness_violations'):
            print(f"\n8. Faithfulness Violations:")
            for violation in result.get('faithfulness_violations', []):
                print(f"   - {violation}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def _run_single_debug(test):
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = debug_web_dev_query(test['query'], test['description'])
    output = buf.getvalue()
    return {
        "test": test['description'],
        "query": test['query'],
        "result": result,
        "output": output,
    }

def run_web_dev_debug(parallel: bool = False, workers: int = 4):
    """Run focused Web Development debugging tests."""
    print("\n" + "="*80)
    print("WEB DEVELOPMENT QUERY DEBUGGING")
    print("="*80)
    
    # Focus on Web Development queries that are failing
    web_dev_tests = [
        {
            "query": "What programming languages are taught in Web Development?",
            "description": "Programming Languages Query - Should find JavaScript, React, Node.js"
        },
        {
            "query": "Does Web Development teach JavaScript?",
            "description": "Coverage Question - Should find JavaScript content"
        },
        {
            "query": "What technologies are used in the Web Development bootcamp?",
            "description": "Technology Stack Query - Should find React, Node.js, MongoDB"
        },
        {
            "query": "What do you learn in Web Development?",
            "description": "General Learning Query - Should find comprehensive curriculum"
        }
    ]
    
    results = []

    if parallel:
        futures = []
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            for test in web_dev_tests:
                futures.append(executor.submit(_run_single_debug, test))
            for fut in as_completed(futures):
                res = fut.result()
                # Print each captured output as it completes to keep logs readable
                print(res["output"], end="")
                results.append({k: v for k, v in res.items() if k != "output"})
    else:
        for test in web_dev_tests:
            res = _run_single_debug(test)
            print(res["output"], end="")
            results.append({k: v for k, v in res.items() if k != "output"})
            print("\n" + "-"*80 + "\n")
    
    # Analysis summary
    print("\n" + "="*80)
    print("WEB DEV DEBUGGING SUMMARY")
    print("="*80)
    
    for idx, test_result in enumerate(results, 1):
        result = test_result['result']
        if result:
            retrieved_count = len(result.get('retrieved_docs', []))
            filtered_count = len(result.get('filtered_docs', []))
            relevance_scores = result.get('relevance_scores', [])
            avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
            
            print(f"\n{idx}. {test_result['test']}")
            print(f"   Query: {test_result['query']}")
            print(f"   Retrieved: {retrieved_count} | Filtered: {filtered_count}")
            print(f"   Avg Relevance: {avg_relevance:.2f}")
            print(f"   Grounded: {'✅' if result.get('is_grounded', False) else '❌'}")
            print(f"   Fallback: {'❌' if result.get('is_fallback', False) else '✅'}")
            
            if result.get('rejection_reasons'):
                print(f"   Rejection Reasons: {result.get('rejection_reasons', [])}")
        else:
            print(f"\n{idx}. {test_result['test']} - FAILED")
    
    print("\n" + "="*80)
    print("KEY ISSUES TO INVESTIGATE:")
    print("1. Are Web Dev docs being retrieved at all?")
    print("2. Are they being flagged as 'wrong_topic' in relevance assessment?")
    print("3. Are they being filtered out in document filtering?")
    print("4. What are the specific rejection reasons?")
    print("="*80 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Web Development Query Debugging")
    parser.add_argument("--parallel", action="store_true", help="Run debug tests in parallel")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
    args = parser.parse_args()
    run_web_dev_debug(parallel=args.parallel, workers=args.workers)
