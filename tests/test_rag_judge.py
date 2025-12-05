"""
Judge-driven regression harness for the RAG v2 pipeline.

Loads canonical Q&A pairs, executes the RAG workflow, and asks GPT-4o to
score each answer against the expected outcome. Designed for parallel
execution and structured reporting.
"""

import argparse
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Ensure src/ is on the path
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = WORKSPACE_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

# Set mock Slack credentials to avoid auth errors on import
os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test-token-for-testing")
os.environ.setdefault("SLACK_SIGNING_SECRET", "test-signing-secret-for-testing")

from app_rag_v2 import rag_workflow, call_openai_json  # noqa: E402
from langchain_core.messages import HumanMessage, AIMessage  # noqa: E402

DEFAULT_FIXTURE_PATH = WORKSPACE_ROOT / "tests" / "fixtures" / "rag_judge_fixtures.json"
RESULTS_DIR = WORKSPACE_ROOT / "tests" / "results"

JUDGE_SYSTEM_PROMPT = """
You are a meticulous evaluator for a sales-enablement RAG system. Score each answer on a 0-10 scale.
- Base accuracy on the provided expected_answer and evidence.
- Verify that citations reference the expected documents and support the claims. Accept citations in any format (raw strings, structured objects, inline references) as long as they correctly identify the source documents.
- Focus on answer accuracy and content quality, not citation format structure.
- Penalize hallucinations, missing required details, or tone that contradicts expectations.
- Accept paraphrasing and different wording as long as the core information is accurate.
- For multi-turn conversations: Evaluate whether the assistant correctly uses conversation context to answer follow-up questions. The assistant should understand references to previous messages (e.g., "that program", "the bootcamp we discussed").
- Return a JSON object: {"score": float 0-10, "verdict": "pass|fail", "feedback": str, "missing_items": [str], "hallucination_flags": [str]}.
- Use score >= 8 to mark verdict "pass"; otherwise "fail".
"""


def load_fixtures(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("Fixture file must contain a list of test cases.")
    return data


def summarize_citations(citations: Any) -> List[Dict[str, Any]]:
    summary: List[Dict[str, Any]] = []
    if not citations:
        return summary
    for item in citations:
        if isinstance(item, dict):
            summary.append(
                {
                    "document_id": item.get("document_id") or item.get("source_id") or item.get("id"),
                    "label": item.get("label")
                    or item.get("document_name")
                    or item.get("source_title"),
                    "snippet": item.get("snippet") or item.get("text") or item.get("content"),
                    "score": item.get("score"),
                }
            )
        else:
            summary.append({"raw": str(item)})
    return summary


def summarize_documents(documents: Any) -> List[Dict[str, Any]]:
    summary: List[Dict[str, Any]] = []
    if not documents:
        return summary
    for doc in documents:
        if isinstance(doc, dict):
            meta = doc.get("metadata") or {}
            summary.append(
                {
                    "id": doc.get("id") or meta.get("id"),
                    "score": doc.get("score") or meta.get("score"),
                    "namespace": meta.get("namespace"),
                    "title": meta.get("title") or meta.get("document_name"),
                }
            )
        else:
            summary.append({"raw": str(doc)})
    return summary


def judge_answer(payload: Dict[str, Any]) -> Dict[str, Any]:
    user_prompt = json.dumps(payload, ensure_ascii=False, indent=2)
    return call_openai_json(JUDGE_SYSTEM_PROMPT, user_prompt, model="gpt-4o")


def run_case(test_case: Dict[str, Any], min_score: float) -> Dict[str, Any]:
    test_id = test_case["id"]
    query = test_case["query"]
    conversation_turns = test_case.get("conversation_turns", None)

    # Handle multi-turn conversation tests
    if conversation_turns:
        return run_conversation_case(test_case, min_score)

    # Single-turn test (original logic)
    config = {"configurable": {"thread_id": f"judge_{uuid.uuid4()}"}, "recursion_limit": 50}
    initial_state = {
        "query": query,
        "conversation_history": [],
        "iteration_count": 0,
        "metadata": {"test_id": test_id},
    }

    start = time.time()
    result = rag_workflow.invoke(initial_state, config)
    elapsed = time.time() - start

    final_response = result.get("final_response", "")
    citations = summarize_citations(result.get("source_citations"))
    retrieved_docs = summarize_documents(result.get("retrieved_docs"))
    filtered_docs = summarize_documents(result.get("filtered_docs"))

    judge_payload = {
        "test_id": test_id,
        "question": query,
        "expected_answer": test_case.get("expected_answer"),
        "expected_citations": test_case.get("expected_citations", []),
        "judge_criteria": test_case.get("judge_criteria", []),
        "actual_answer": final_response,
        "actual_citations": citations,
        "retrieved_documents": retrieved_docs,
        "filtered_documents": filtered_docs,
        "metadata": result.get("metadata", {}),
    }

    judge_result = judge_answer(judge_payload)
    score = float(judge_result.get("score", 0.0))
    verdict = judge_result.get("verdict") or ("pass" if score >= min_score else "fail")

    return {
        "id": test_id,
        "query": query,
        "elapsed_seconds": round(elapsed, 2),
        "final_response": final_response,
        "citations": citations,
        "retrieved_documents": retrieved_docs,
        "judge_payload": judge_payload,
        "judge_result": judge_result,
        "score": score,
        "verdict": verdict,
        "passed": verdict == "pass" and score >= min_score,
    }


def run_conversation_case(test_case: Dict[str, Any], min_score: float) -> Dict[str, Any]:
    """Run a multi-turn conversation test."""
    test_id = test_case["id"]
    conversation_turns = test_case["conversation_turns"]
    
    # Use same thread_id for all turns to maintain conversation context
    thread_id = f"judge_conv_{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}
    
    conversation_history = []
    all_responses = []
    total_elapsed = 0
    
    # Process each turn in the conversation
    for turn_idx, turn in enumerate(conversation_turns):
        user_query = turn["user_query"]
        expected_answer = turn.get("expected_answer")
        
        initial_state = {
            "query": user_query,
            "conversation_history": conversation_history.copy(),
            "is_follow_up": turn_idx > 0,
            "conversation_stage": "follow_up" if turn_idx > 0 else "initial",
            "iteration_count": 0,
            "metadata": {
                "test_id": test_id,
                "turn": turn_idx + 1,
                "total_turns": len(conversation_turns)
            },
        }
        
        start = time.time()
        result = rag_workflow.invoke(initial_state, config)
        elapsed = time.time() - start
        total_elapsed += elapsed
        
        final_response = result.get("final_response", "")
        all_responses.append({
            "turn": turn_idx + 1,
            "user_query": user_query,
            "response": final_response,
            "elapsed_seconds": round(elapsed, 2)
        })
        
        # Update conversation history for next turn
        conversation_history.append(HumanMessage(content=user_query))
        conversation_history.append(AIMessage(content=final_response))
    
    # Judge the final turn (or all turns if specified)
    final_turn = conversation_turns[-1]
    judge_turn_idx = final_turn.get("judge_this_turn", len(conversation_turns)) - 1
    judge_turn = conversation_turns[judge_turn_idx]
    judge_response = all_responses[judge_turn_idx]
    
    citations = summarize_citations(result.get("source_citations"))
    retrieved_docs = summarize_documents(result.get("retrieved_docs"))
    filtered_docs = summarize_documents(result.get("filtered_docs"))
    
    judge_payload = {
        "test_id": test_id,
        "question": judge_turn["user_query"],
        "expected_answer": judge_turn.get("expected_answer"),
        "expected_citations": judge_turn.get("expected_citations", []),
        "judge_criteria": judge_turn.get("judge_criteria", []),
        "conversation_context": [
            {"turn": r["turn"], "user": r["user_query"], "assistant": r["response"]}
            for r in all_responses[:judge_turn_idx]
        ],
        "actual_answer": judge_response["response"],
        "actual_citations": citations,
        "retrieved_documents": retrieved_docs,
        "filtered_documents": filtered_docs,
        "metadata": result.get("metadata", {}),
    }
    
    judge_result = judge_answer(judge_payload)
    score = float(judge_result.get("score", 0.0))
    verdict = judge_result.get("verdict") or ("pass" if score >= min_score else "fail")
    
    return {
        "id": test_id,
        "query": f"Multi-turn conversation ({len(conversation_turns)} turns)",
        "elapsed_seconds": round(total_elapsed, 2),
        "final_response": judge_response["response"],
        "citations": citations,
        "retrieved_documents": retrieved_docs,
        "conversation_turns": all_responses,
        "judge_payload": judge_payload,
        "judge_result": judge_result,
        "score": score,
        "verdict": verdict,
        "passed": verdict == "pass" and score >= min_score,
    }


def execute_tests(
    fixtures: List[Dict[str, Any]],
    parallel: bool,
    workers: int,
    min_score: float,
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    if parallel:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            future_map = {
                executor.submit(run_case, test_case, min_score): test_case["id"]
                for test_case in fixtures
            }
            for future in as_completed(future_map):
                results.append(future.result())
    else:
        for test_case in fixtures:
            results.append(run_case(test_case, min_score))
    return results


def save_report(results: List[Dict[str, Any]], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "model": "gpt-4o",
                "results": results,
            },
            handle,
            ensure_ascii=False,
            indent=2,
        )


def print_summary(results: List[Dict[str, Any]], min_score: float) -> None:
    print("\n" + "=" * 80)
    print("RAG v2 GPT-4o Judge Results")
    print("=" * 80)
    for record in results:
        status = "✅" if record["passed"] else "❌"
        print(
            f"{status} {record['id']:>24} | score: {record['score']:>4.1f} "
            f"| verdict: {record['verdict']:<4} | time: {record['elapsed_seconds']:>5.2f}s"
        )
        if not record["passed"]:
            feedback = record["judge_result"].get("feedback") or "No feedback provided."
            print(f"    Feedback: {feedback}")
            missing = record["judge_result"].get("missing_items") or []
            if missing:
                print(f"    Missing: {missing}")
            hallucinations = record["judge_result"].get("hallucination_flags") or []
            if hallucinations:
                print(f"    Hallucinations: {hallucinations}")
    print("-" * 80)
    passed_count = sum(1 for r in results if r["passed"])
    print(f"Passed {passed_count}/{len(results)} (min score {min_score})")
    print("=" * 80 + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Judge-driven regression tests for RAG v2.")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=DEFAULT_FIXTURE_PATH,
        help="Path to the fixture JSON file.",
    )
    parser.add_argument(
        "--test-id",
        type=str,
        help="Run only the test case with this ID (e.g., 'coverage_da_python').",
    )
    parser.add_argument("--parallel", action="store_true", help="Run test cases in parallel.")
    parser.add_argument(
        "--workers", type=int, default=4, help="Number of worker threads when running in parallel."
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=8.0,
        help="Minimum judge score required to mark a test as pass.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional path for saving the results report. Defaults to tests/results/ with timestamp.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    fixtures = load_fixtures(args.fixtures)
    
    # Filter by test ID if specified
    if args.test_id:
        fixtures = [f for f in fixtures if f.get("id") == args.test_id]
        if not fixtures:
            print(f"❌ No test found with ID: {args.test_id}")
            print(f"Available test IDs:")
            all_fixtures = load_fixtures(args.fixtures)
            for f in all_fixtures:
                print(f"  - {f.get('id')}")
            raise SystemExit(1)
        print(f"🎯 Running single test: {args.test_id}")
        print(f"   Query: {fixtures[0].get('query', 'N/A')}")
        print()

    results = execute_tests(fixtures, parallel=args.parallel, workers=args.workers, min_score=args.min_score)
    print_summary(results, args.min_score)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_path = (
        args.report
        if args.report
        else RESULTS_DIR / f"rag_judge_results_{timestamp}.json"
    )
    save_report(results, report_path)
    print(f"Saved detailed report to {report_path}")

    # Non-zero exit when any test fails (for CI usage)
    if any(not record["passed"] for record in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

