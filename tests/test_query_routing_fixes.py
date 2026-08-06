"""
Regression tests for query routing and response fixes driven by real failures
observed in #edu-product-admissions (2026-03 .. 2026-08):

1. Breakdown/overview requests were misrouted into the coverage path and answered
   with "*the requested topic* is not mentioned ... part of ml" (broken template).
2. "Next start date" questions returned past cohorts (no date awareness).
3. Program names rendered as raw codes ("ce", "de", "ml") in negative answers.
4. DSML syllabus chunks were dropped because PROGRAM_SYNONYMS pinned an old
   filename version (2025_07 vs 2026_02 in the knowledge base).
5. Portfolio-wide questions ("which course have linux in?") were scoped to a
   single program.

These tests are offline: no OpenAI or Slack calls.
"""

import os
import sys
from datetime import date, timedelta

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("SLACK_BOT_TOKEN", "")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils import (  # noqa: E402
    docs_for_program_syllabi,
    is_breakdown_request,
    is_portfolio_wide_query,
    is_valid_coverage_topic,
    load_full_syllabus_docs,
    local_topic_index,
    program_display_name,
    program_for_source,
    strip_doc_version,
)
from src.config import PROGRAM_SYNONYMS  # noqa: E402
from src.routes import (  # noqa: E402
    route_after_coverage_classification,
    route_after_coverage_verification,
)
from src.nodes.cohort_calendar_nodes import (  # noqa: E402
    _filter_cohorts_for_query,
    _parse_start_date,
)


# ---------------- Breakdown request detection ----------------

BREAKDOWN_QUERIES = [
    # Verbatim failing queries from Slack
    "can you generate a detailed week by week overview of what will be covered in the Data Engineering Full Time bootcamp?",
    "can you generate a detailed Unit breakdown of the topics covered in the Data Science & Machine Learning Part Time bootcamp?",
    "provide a curriculum overview of the topics covered in the Data Engineering Full Time bootcamp.",
    "Can you do a breakdown week by week?",
    "Can you do a breakdown module by module of the Data Science & Machine Learning bootcamp?",
    "how the AI product Manager Full time Bootcamp looks like week by week?",
    "can you generate a detailed overview of what will be covered in the Cybersecurity Part Time bootcamp?",
]

NOT_BREAKDOWN_QUERIES = [
    "does Cloud Engineering cover kubernetes?",
    "Is Linux covered in the DevOps & Cloud computing course?",
    "what is the laptop requirement for the AI consulting bootcamp?",
    "When are the next start dates for AI Engineering?",
    "Does the AI Engineering bootcamp cover Spring Boot?",
]


def test_breakdown_queries_detected():
    for q in BREAKDOWN_QUERIES:
        assert is_breakdown_request(q), f"should be breakdown: {q}"


def test_non_breakdown_queries_not_detected():
    for q in NOT_BREAKDOWN_QUERIES:
        assert not is_breakdown_request(q), f"should NOT be breakdown: {q}"


# ---------------- Portfolio-wide detection ----------------

def test_portfolio_wide_detected():
    assert is_portfolio_wide_query("which course have linux in?")
    assert is_portfolio_wide_query("What bootcamp includes tooks such as AWS, Heroku, Kubernetes and Docker?")
    assert is_portfolio_wide_query("which courses teach Python")


def test_single_program_not_portfolio_wide():
    assert not is_portfolio_wide_query("does Cloud Engineering cover kubernetes?")
    assert not is_portfolio_wide_query("what is the laptop requirement for the AI consulting bootcamp?")


# ---------------- Coverage topic validity & routing ----------------

def test_invalid_topics_rejected():
    assert not is_valid_coverage_topic("")
    assert not is_valid_coverage_topic("the requested topic")
    assert not is_valid_coverage_topic("multiple_topics")
    assert not is_valid_coverage_topic("x" * 150)


def test_valid_topic_accepted():
    assert is_valid_coverage_topic("Kubernetes")


def test_invalid_topic_routes_to_standard_generation():
    state = {"coverage_verification": {"is_present": False, "topic": "multiple_topics"}}
    assert route_after_coverage_verification(state) == "generate_response"


def test_valid_negative_topic_routes_to_negative_coverage():
    state = {"coverage_verification": {"is_present": False, "topic": "Kubernetes"}}
    assert route_after_coverage_verification(state) == "generate_negative_coverage"


def test_portfolio_wide_skips_coverage_verification():
    state = {"is_portfolio_wide": True, "is_coverage_question": True}
    assert route_after_coverage_classification(state) == "generate_response"


# ---------------- Display names (no raw codes in user-facing text) ----------------

def test_display_names_are_not_codes():
    for pid in PROGRAM_SYNONYMS:
        name = program_display_name(pid, PROGRAM_SYNONYMS)
        assert len(name) > 3, f"{pid} renders as code-like name: {name!r}"


# ---------------- Version-tolerant filename matching ----------------

def test_strip_doc_version():
    assert strip_doc_version("Data_Science_&_Machine_Learning_bootcamp_2026_02.md") == "data_science_&_machine_learning_bootcamp"
    assert strip_doc_version("DevOps_bootcamp_2025_07.txt") == "devops_bootcamp"


def test_dsml_matches_any_version():
    docs = [
        {"source": "Data_Science_&_Machine_Learning_bootcamp_2026_02.md", "content": "x"},
        {"source": "Data_Science_&_Machine_Learning_bootcamp_2025_07.txt", "content": "x"},
        {"source": "DevOps_bootcamp_2025_07.txt", "content": "x"},
    ]
    matched = docs_for_program_syllabi(docs, ["data_science_ml"], PROGRAM_SYNONYMS)
    assert len(matched) == 2


def test_program_for_source():
    assert program_for_source("Cloud_Engineering_bootcamp_2025_12.md", PROGRAM_SYNONYMS) == "cloud_engineering"
    assert program_for_source("Certifications_2025_07.md", PROGRAM_SYNONYMS) is None


# ---------------- Full syllabus loading for breakdown requests ----------------

def test_every_program_has_a_loadable_syllabus():
    for pid in PROGRAM_SYNONYMS:
        docs = load_full_syllabus_docs([pid], PROGRAM_SYNONYMS)
        assert len(docs) == 1, f"no local syllabus found for {pid}"
        assert docs[0]["full_syllabus"] is True
        assert len(docs[0]["content"]) > 1000


# ---------------- Portfolio-wide local term index ----------------

def test_local_topic_index_finds_linux_in_all_three_programs():
    idx = local_topic_index("which course have linux in?", PROGRAM_SYNONYMS)
    programs = {e["program_name"] for e in idx}
    # Ground truth confirmed by education team in Slack (2026-03-24): DV, CE, CY
    assert {"DevOps & Cloud Computing", "Cybersecurity", "Cloud Engineering"} <= programs


def test_local_topic_index_kubernetes_not_in_cloud_engineering():
    idx = local_topic_index("which bootcamps teach kubernetes?", PROGRAM_SYNONYMS)
    k8s_programs = {e["program_name"] for e in idx if e["term"] == "kubernetes"}
    assert "DevOps & Cloud Computing" in k8s_programs
    assert "Cloud Engineering" not in k8s_programs


def test_local_topic_index_ignores_stopwords():
    idx = local_topic_index("which courses have the tools?", PROGRAM_SYNONYMS)
    assert idx == []


# ---------------- Sibling-program suggestion (local phrase scan) ----------------

def test_sibling_check_finds_kubernetes_in_devops_not_ce():
    from src.nodes.generation_nodes import _find_other_programs_covering
    names = _find_other_programs_covering("Kubernetes", ["cloud_engineering"])
    assert "DevOps & Cloud Computing" in names
    assert "Cloud Engineering" not in names


def test_sibling_check_whole_phrase_not_tokens():
    from src.nodes.generation_nodes import _find_other_programs_covering
    # "engineering" alone appears in many syllabi; the full phrase appears in none
    names = _find_other_programs_covering("Site Reliability Engineering", [])
    assert names == []


# ---------------- Cohort calendar date-awareness ----------------

def _fmt(d: date) -> str:
    return f"{d.month}/{d.day}/{d.year}"


def _rows():
    today = date.today()
    return [
        {"bootcamp_name": "AI-PT-EN-PAST", "track": "AI", "type": "PT",
         "start_date": _fmt(today - timedelta(days=60)), "canceled": False},
        {"bootcamp_name": "AI-PT-EN-FUT2", "track": "AI", "type": "PT",
         "start_date": _fmt(today + timedelta(days=90)), "canceled": False},
        {"bootcamp_name": "AI-PT-EN-FUT1", "track": "AI", "type": "PT",
         "start_date": _fmt(today + timedelta(days=30)), "canceled": False},
        {"bootcamp_name": "AI-PT-EN-CANC", "track": "AI", "type": "PT",
         "start_date": _fmt(today + timedelta(days=30)), "canceled": True},
    ]


def test_future_only_excludes_past_and_canceled():
    out = _filter_cohorts_for_query(
        _rows(), "when is the next start date for AI Engineering part time",
        {"track": "AI", "type": "PT", "future_only": True},
    )
    names = [r["bootcamp_name"] for r in out]
    assert "AI-PT-EN-PAST" not in names
    assert "AI-PT-EN-CANC" not in names
    assert names == ["AI-PT-EN-FUT1", "AI-PT-EN-FUT2"]  # earliest upcoming first


def test_year_filter():
    target_year = (date.today() + timedelta(days=90)).year
    out = _filter_cohorts_for_query(
        _rows(), "AI PT cohorts", {"track": "AI", "type": "PT", "year": target_year},
    )
    assert out
    for r in out:
        assert _parse_start_date(r["start_date"]).year == target_year


def test_parse_start_date_formats():
    assert _parse_start_date("1/13/2026") == date(2026, 1, 13)
    assert _parse_start_date("2026-01-13") == date(2026, 1, 13)
    assert _parse_start_date("") is None
    assert _parse_start_date("TBD") is None
