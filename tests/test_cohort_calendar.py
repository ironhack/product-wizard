#!/usr/bin/env python3
"""
Tests for cohort/calendar path: parser (canceled logic, column mapping) and optional pipeline integration.

Run with: python tests/test_cohort_calendar.py
  --save   save results to tests/results/
  --live   fetch real sheet + run full cohort path (single question)
  --real   run 3 real-case questions and assert expected content (WD March teacher, ML Feb PM, UX April start dates)
"""

import json
import os
import sys
from pathlib import Path

# Load .env if present
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

os.environ.setdefault("OPENAI_API_KEY", "sk-fake-for-parser-tests")
os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test")
os.environ.setdefault("SLACK_SIGNING_SECRET", "test-secret")

from src.cohort_calendar.parser import parse_cohort_rows, FIRST_DATA_ROW


def _make_header_rows():
    return [[""] * 20 for _ in range(FIRST_DATA_ROW)]


def test_parser_single_active_cohort():
    """Parser extracts bootcamp name, track, type, dates, teachers, program; canceled=False when start date present."""
    rows = _make_header_rows()
    # Cols: 0 empty, 1 campus id, 2 bootcamp name, 3 track, 4 type, 5 lang, ... 9 start, 10 end, 13 program, 14 lead, 15 co
    rows.append([
        "", "46034WDFTRMTEUEN",
        "WD-FT-EN-JAN26", "WD", "FT", "EN",
        "", "", "", "1/12/2026", "3/13/2026",
        "", "", "PM Name", "Rocio Diaz", "Jorge Berrizbeitia",
    ])
    parsed = parse_cohort_rows(rows)
    assert len(parsed) == 1
    r = parsed[0]
    assert r["bootcamp_name"] == "WD-FT-EN-JAN26"
    assert r["track"] == "WD"
    assert r["type"] == "FT"
    assert r["language"] == "EN"
    assert r["start_date"] == "1/12/2026"
    assert r["end_date"] == "3/13/2026"
    assert r["lead_teacher"] == "Rocio Diaz"
    assert r["co_teacher"] == "Jorge Berrizbeitia"
    assert r["program"] == "PM Name"
    assert r["canceled"] is False


def test_parser_canceled_no_start_date():
    """Row with missing Cohort Start Date is marked canceled."""
    rows = _make_header_rows()
    rows.append([
        "", "46098DAPTRMTEUES",
        "DA-PT-ES-MAR26", "DA", "PT", "ES",
        "", "", "", "", "",
        "", "", "", "Juliette Tayar", "Valentin Silvestri",
    ])
    parsed = parse_cohort_rows(rows)
    assert len(parsed) == 1
    assert parsed[0]["canceled"] is True
    assert parsed[0]["start_date"] == ""


def test_parser_canceled_keyword():
    """Row containing 'Cancelled' in any cell is marked canceled."""
    rows = _make_header_rows()
    rows.append([
        "", "46098MLPTRMTEUES",
        "ML-PT-ES-MAR26", "ML", "PT", "ES",
        "", "", "3/17/2026", "9/12/2026",
        "", "", "", "Juliette Tayar", "Carlos Danino",
        "", "", "", "", "Cancelled",
    ])
    parsed = parse_cohort_rows(rows)
    assert len(parsed) == 1
    assert parsed[0]["canceled"] is True


def test_parser_empty_rows_skipped():
    """Empty rows and rows without bootcamp name are skipped."""
    rows = _make_header_rows()
    rows.append([""] * 20)
    rows.append(["", "", "AI-PT-EN-MAR26", "AI", "PT", "EN", "", "", "", "3/17/2026", "9/12/2026", "", "", "", "Zeynep", ""])
    rows.append([""] * 20)
    parsed = parse_cohort_rows(rows)
    assert len(parsed) == 1
    assert parsed[0]["bootcamp_name"] == "AI-PT-EN-MAR26"


def test_parser_multiple_cohorts():
    """Multiple data rows produce multiple parsed records."""
    rows = _make_header_rows()
    rows.append(["", "46034WDFTRMTEUEN", "WD-FT-EN-JAN26", "WD", "FT", "EN", "", "", "", "1/12/2026", "3/13/2026", "", "", "", "Rocio", "Jorge"])
    rows.append(["", "46034DAFTRMTEUEN", "DA-FT-EN-JAN26", "DA", "FT", "EN", "", "", "", "1/12/2026", "3/13/2026", "", "", "", "Juliette", "Frederico"])
    parsed = parse_cohort_rows(rows)
    assert len(parsed) == 2
    assert parsed[0]["bootcamp_name"] == "WD-FT-EN-JAN26" and parsed[0]["lead_teacher"] == "Rocio"
    assert parsed[1]["bootcamp_name"] == "DA-FT-EN-JAN26" and parsed[1]["lead_teacher"] == "Juliette"


def run_tests(save_results: bool = False):
    """Run all parser tests and optionally save results to tests/results/."""
    tests = [
        test_parser_single_active_cohort,
        test_parser_canceled_no_start_date,
        test_parser_canceled_keyword,
        test_parser_empty_rows_skipped,
        test_parser_multiple_cohorts,
    ]
    results = {"passed": 0, "failed": 0, "errors": []}
    for t in tests:
        try:
            t()
            results["passed"] += 1
            print(f"  OK: {t.__name__}")
        except AssertionError as e:
            results["failed"] += 1
            results["errors"].append({"test": t.__name__, "error": str(e)})
            print(f"  FAIL: {t.__name__} - {e}")
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({"test": t.__name__, "error": str(e)})
            print(f"  ERROR: {t.__name__} - {e}")
    if save_results:
        out_dir = WORKSPACE_ROOT / "tests" / "results"
        out_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        path = out_dir / f"cohort_calendar_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {path}")
    return results["failed"] == 0


def run_live_test():
    """Fetch real sheet, parse, and run pipeline with a cohort question."""
    from src.cohort_calendar.sheets_client import fetch_cohort_calendar_data
    from src.workflow import rag_workflow

    print("\n--- Live: fetch sheet ---")
    raw = fetch_cohort_calendar_data()
    if not raw:
        print("FAIL: No data (check GOOGLE_SHEETS_CREDENTIALS_JSON and that the sheet is shared with the service account email)")
        return False
    print(f"  Fetched {len(raw)} rows")

    parsed = parse_cohort_rows(raw)
    print(f"  Parsed {len(parsed)} cohorts")
    if parsed:
        r = parsed[0]
        print(f"  Sample: {r['bootcamp_name']} | {r['track']} {r['type']} {r['language']} | Lead: {r['lead_teacher']} | canceled={r['canceled']}")

    print("\n--- Live: full pipeline (cohort question) ---")
    initial_state = {
        "query": "Who is teaching the May AI PT course?",
        "conversation_history": [],
        "is_follow_up": False,
        "conversation_stage": "initial",
        "iteration_count": 0,
        "metadata": {},
    }
    config = {"configurable": {"thread_id": "test-live-" + str(os.getpid())}}
    result = rag_workflow.invoke(initial_state, config)
    answer = result.get("final_response", "")
    print(f"  Query: {initial_state['query']}")
    print(f"  Answer: {answer[:500]}{'...' if len(answer) > 500 else ''}")
    if not answer or "couldn't load" in answer.lower():
        print("  FAIL: No answer or fallback message")
        return False
    print("  OK: Got answer from cohort path")
    return True


# Real cases with expected content from the RMT Bootcamps Tracker sheet
REAL_CASES = [
    {
        "query": "Who is the teacher for the Web Dev full-time in March?",
        "expected_in_answer": ["Rocio Diaz", "Jorge Berrizbeitia"],
        "description": "WD-FT-EN-MAR26: Lead Rocio Diaz, Co-Teacher Jorge Berrizbeitia",
        "require_any": True,
    },
    {
        "query": "Who is the program manager for the Machine Learning and Data Science full-time course in February?",
        "expected_in_answer": ["Juliette Tayar"],
        "description": "ML-FT-EN-FEB26: PM/Lead Juliette Tayar",
    },
    {
        "query": "What are the start dates for the UX Bootcamp in April, both part-time and full-time?",
        "expected_in_answer": ["4/", "April", "no cohorts matching", "matching that criteria"],
        "description": "UX in April: start dates for FT and PT cohorts (or fixed no-match message)",
        "require_any": True,
    },
]


def run_real_cases_test():
    """Run the 3 real-case queries and assert each answer contains expected content."""
    from src.workflow import rag_workflow

    print("Cohort calendar REAL CASES (3 queries, assert expected content)\n")
    config = {"configurable": {"thread_id": "test-real-" + str(os.getpid())}}
    all_ok = True
    results = []

    for i, case in enumerate(REAL_CASES, 1):
        query = case["query"]
        expected = case["expected_in_answer"]
        require_any = case.get("require_any", False)
        desc = case.get("description", "")
        print(f"--- Case {i}: {desc} ---")
        print(f"  Query: {query}")

        initial_state = {
            "query": query,
            "conversation_history": [],
            "is_follow_up": False,
            "conversation_stage": "initial",
            "iteration_count": 0,
            "metadata": {},
        }
        result = rag_workflow.invoke(initial_state, config)
        answer = (result.get("final_response") or "").strip()
        print(f"  Answer: {answer[:400]}{'...' if len(answer) > 400 else ''}\n")

        if not answer or "couldn't load" in answer.lower():
            print(f"  FAIL: No answer or fallback (sheet/API issue)\n")
            all_ok = False
            results.append({"query": query, "passed": False, "error": "no answer"})
            continue

        answer_lower = answer.lower()
        if require_any:
            found = any(e.lower() in answer_lower for e in expected)
            if not found:
                print(f"  FAIL: Answer missing any of expected content: {expected}\n")
                all_ok = False
                results.append({"query": query, "passed": False, "missing_any": expected})
            else:
                print(f"  OK: Answer contains expected content\n")
                results.append({"query": query, "passed": True})
        else:
            missing = [e for e in expected if e.lower() not in answer_lower]
            if missing:
                print(f"  FAIL: Answer missing expected content: {missing}\n")
                all_ok = False
                results.append({"query": query, "passed": False, "missing": missing})
            else:
                print(f"  OK: Answer contains expected content\n")
                results.append({"query": query, "passed": True})

    # Save results
    out_dir = WORKSPACE_ROOT / "tests" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    path = out_dir / f"cohort_real_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"all_passed": all_ok, "cases": results}, f, indent=2)
    print(f"Results saved to {path}")
    return all_ok


if __name__ == "__main__":
    save = "--save" in sys.argv
    live = "--live" in sys.argv
    real = "--real" in sys.argv
    if real:
        ok = run_real_cases_test()
        sys.exit(0 if ok else 1)
    if live:
        print("Cohort calendar LIVE test (sheet + pipeline)")
        ok = run_live_test()
        sys.exit(0 if ok else 1)
    print("Cohort calendar parser tests")
    ok = run_tests(save_results=save)
    sys.exit(0 if ok else 1)
