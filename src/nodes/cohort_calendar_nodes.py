"""
Cohort Calendar Nodes

Nodes for detecting cohort/calendar questions and answering them from the
RMT Bootcamps Tracker Google Sheet (who teaches, whether a cohort exists, who is PM).
"""

import logging
import re
from datetime import date, datetime

from src.state import RAGState
from src.config import (
    COHORT_CALENDAR_CLASSIFICATION_PROMPT,
    COHORT_CALENDAR_FILTER_EXTRACTION_PROMPT,
    PROGRAM_SYNONYMS,
    cohort_calendar_sheet_edit_url,
)
from src.utils import call_openai_json
from src.slack_helpers import send_slack_update

logger = logging.getLogger(__name__)


def cohort_calendar_classification_node(state: RAGState) -> RAGState:
    """
    Detect if the query asks about cohort/calendar info (who teaches, cohort exists, who is PM).
    """
    logger.info("=== Cohort Calendar Classification Node ===")
    send_slack_update(state, "Checking if this is a cohort/calendar question")

    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    query = state.get("query", "")

    user_prompt = f"""
Query: "{query}"
Enhanced query: "{enhanced_query}"

Does this question ask about who teaches a specific cohort, whether a specific cohort exists (by track/type/month), or who is the PM for a specific cohort?
Return JSON: {{"is_cohort_calendar_question": true/false, "reason": "brief explanation"}}
"""

    result = call_openai_json(
        COHORT_CALENDAR_CLASSIFICATION_PROMPT or "You classify whether the user question is about cohort/calendar (teachers, PM, schedule). Return JSON with is_cohort_calendar_question (boolean) and reason (string).",
        user_prompt,
        model="gpt-4o-mini",
        timeout=15,
    )
    is_cohort = result.get("is_cohort_calendar_question", False)
    reason = result.get("reason", "")

    logger.info(f"Cohort/calendar question: {is_cohort} | reason: {reason}")

    return {
        **state,
        "is_cohort_calendar_question": is_cohort,
    }


def cohort_calendar_response_node(state: RAGState) -> RAGState:
    """
    Fetch cohort calendar from Google Sheet, parse, and answer the question via LLM.
    On failure, set a safe final_response and still go to END.
    """
    logger.info("=== Cohort Calendar Response Node ===")
    from src.cohort_calendar.sheets_client import fetch_cohort_calendar_data
    from src.cohort_calendar.parser import parse_cohort_rows
    from src.utils import call_openai_text, convert_markdown_to_slack

    query = state.get("query", "")
    send_slack_update(state, "Fetching cohort calendar...")

    try:
        raw_rows = fetch_cohort_calendar_data()
        if not raw_rows:
            send_slack_update(state, "Calendar unavailable")
            _sheet = cohort_calendar_sheet_edit_url()
            return {
                **state,
                "final_response": convert_markdown_to_slack(
                    f"I couldn't load the cohort calendar right now. Please try again.\n\n"
                    f"You can double-check the live Bootcamps Tracker here: {_sheet}"
                ),
                "metadata": {**(state.get("metadata") or {}), "cohort_calendar_used": False},
            }
        send_slack_update(state, "Filtering matching cohorts...")
        rows = parse_cohort_rows(raw_rows)
        filters = _extract_cohort_filters_from_query(query)
        rows = _filter_cohorts_for_query(rows, query, filters)

        if not rows:
            send_slack_update(state, "No matching cohorts found")
            _sheet = cohort_calendar_sheet_edit_url()
            if filters.get("future_only"):
                no_match_line = (
                    f"There are no upcoming cohorts (starting after {date.today().strftime('%B %d, %Y')}) "
                    "matching that criteria in the current calendar."
                )
            else:
                no_match_line = "There are no cohorts matching that criteria in the current calendar."
            return {
                **state,
                "final_response": convert_markdown_to_slack(
                    f"{no_match_line}\n\n"
                    "Please double-check the live Bootcamps Tracker in case the sheet was updated or the cohort is listed under a different name:\n"
                    f"{_sheet}"
                ),
                "metadata": {**(state.get("metadata") or {}), "cohort_calendar_used": True},
            }

        send_slack_update(state, "Answering from cohort calendar...")
        context = _format_cohort_context(rows)
        today_str = date.today().strftime("%A, %B %d, %Y")
        system = (
            f"You answer questions about Ironhack cohorts/calendar using only the provided table. "
            f"Today is {today_str}. "
            f"When the user asks about the 'next' or 'upcoming' cohort/start date, only consider cohorts "
            f"starting AFTER today - never present a past start date as 'next'. "
            f"If the user asks about a specific month or year, answer for that month/year only. "
            f"If no cohort in the table matches (e.g. all matching cohorts already started), say so explicitly "
            f"instead of substituting a past or different cohort. "
            f"If a cohort is marked as canceled, say so. Be concise and cite the data. "
            f"Do not make up information. "
            f"When the question is about who teaches: always give both Lead Teacher and Co-Teacher when present, and clearly label who is who (e.g. 'Lead teacher: X. Co-teacher: Y.')."
        )
        user_content = f"Cohort calendar data (canceled cohorts are marked):\n\n{context}\n\nUser question: {query}"
        answer = call_openai_text(system, user_content, model="gpt-4o-mini", timeout=30)
        if not answer:
            answer = "I couldn't generate an answer from the calendar. Please try again."
        final_response = convert_markdown_to_slack(answer)
    except Exception as e:
        logger.exception("Cohort calendar response failed: %s", e)
        _sheet = cohort_calendar_sheet_edit_url()
        final_response = convert_markdown_to_slack(
            f"I couldn't load the cohort calendar right now. Please try again.\n\n"
            f"You can double-check the live Bootcamps Tracker here: {_sheet}"
        )

    return {
        **state,
        "final_response": final_response,
        "metadata": {**(state.get("metadata") or {}), "cohort_calendar_used": True},
    }


# Max rows to send to LLM (avoid context overflow; ~128k token limit)
_MAX_COHORT_ROWS_FOR_LLM = 250

# Track codes from PROGRAM_SYNONYMS (single source of truth); fallback for bootcamp cohort sheet
def _get_track_codes():
    codes = []
    for prog_info in (PROGRAM_SYNONYMS or {}).values():
        if isinstance(prog_info, dict) and prog_info.get("code"):
            c = str(prog_info["code"]).strip().upper()
            if c and c not in codes:
                codes.append(c)
    return tuple(codes) if codes else ("WD", "DA", "UX", "ML", "AI", "DV", "CY", "MK", "PM", "AC", "CE", "DE")

_TRACK_CODES = _get_track_codes()
_MONTH_NAMES = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december")


def _extract_cohort_filters_from_query(query: str) -> dict:
    """
    Extract track, type (PT/FT), month, year, and future-only intent from the user query via LLM.
    Returns {"track": "AI"|null, "type": "PT"|"FT"|null, "month": "may"|null,
             "year": 2026|null, "future_only": true|false}.
    """
    if not (query or "").strip():
        return {}
    prompt = (
        COHORT_CALENDAR_FILTER_EXTRACTION_PROMPT
        or "Extract from the user question: track (WD, DA, UX, ML, AI, DV, CY, MK, PM, AC, CE, DE), type (PT or FT), month (lowercase), year (4-digit), future_only (true if asking about next/upcoming cohorts). Return JSON: {\"track\": null or code, \"type\": null or \"PT\" or \"FT\", \"month\": null or \"may\", \"year\": null or 2026, \"future_only\": true or false}"
    )
    result = call_openai_json(prompt, f'User question: "{query}"', model="gpt-4o-mini", timeout=10)
    out = {}
    if result.get("track"):
        t = str(result["track"]).upper().strip()
        if t in _TRACK_CODES:
            out["track"] = t
    if result.get("type"):
        typ = str(result["type"]).upper().strip()
        if typ in ("PT", "FT"):
            out["type"] = typ
    if result.get("month"):
        m = str(result["month"]).lower().strip()
        if m in _MONTH_NAMES:
            out["month"] = m
    if result.get("year"):
        y = str(result["year"]).strip()
        if re.fullmatch(r"20\d{2}", y):
            out["year"] = int(y)
    if result.get("future_only"):
        out["future_only"] = True
    # Deterministic backstop: "next"/"upcoming" wording always means future cohorts
    if re.search(r"\b(next|upcoming|soonest|from now)\b", (query or "").lower()):
        out["future_only"] = True
    # Deterministic backstop: explicit year in the query
    if "year" not in out:
        m = re.search(r"\b(20\d{2})\b", query or "")
        if m:
            out["year"] = int(m.group(1))
    logger.info("Cohort filters extracted: %s", out)
    return out


def _parse_start_date(start: str):
    """Parse a sheet start date (typically M/D/YYYY) into a date; None if unparseable."""
    s = (start or "").strip()
    if not s:
        return None
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _filter_cohorts_for_query(rows: list, query: str, extracted_filters: dict = None) -> list:
    """
    Filter rows using extracted filters (track, type, month) and keyword fallback from query.
    Keeps only rows matching the criteria and caps at _MAX_COHORT_ROWS_FOR_LLM.
    """
    extracted_filters = extracted_filters or {}
    q = (query or "").upper()
    q_lower = (query or "").lower()

    # Prefer LLM-extracted filters; fall back to keyword detection
    want_tracks = [extracted_filters["track"]] if extracted_filters.get("track") else []
    if not want_tracks:
        want_tracks = [t for t in _TRACK_CODES if t in q or q_lower.find(t.lower()) >= 0]

    if extracted_filters.get("type"):
        want_ft = extracted_filters["type"] == "FT"
        want_pt = extracted_filters["type"] == "PT"
    else:
        want_ft = "FT" in q or " full time" in q_lower or " full-time" in q_lower
        want_pt = "PT" in q or " part time" in q_lower or " part-time" in q_lower

    want_months = [extracted_filters["month"]] if extracted_filters.get("month") else []
    if not want_months:
        want_months = [m for m in _MONTH_NAMES if m in q_lower]

    # For month matching: date is typically M/D/YYYY or MM/DD/YYYY - match month prefix (e.g. "4/" or "04/" for April)
    month_prefixs = []  # e.g. ("4/", "04/") for April
    for i, m in enumerate(_MONTH_NAMES, 1):
        if m in want_months or m in q_lower:
            month_prefixs.append(f"{i}/")
            if i < 10:
                month_prefixs.append(f"0{i}/")

    def _start_date_matches_month(start: str, want_months_list: list, prefixes: list) -> bool:
        if not start:
            return False
        start = start.strip()
        if not start:
            return False
        if any(start.startswith(prefix) for prefix in prefixes):
            return True
        if any(m in start.lower() for m in want_months_list):
            return True
        return False

    want_year = extracted_filters.get("year")
    future_only = bool(extracted_filters.get("future_only"))
    today = date.today()

    def matches(r: dict) -> bool:
        track = (r.get("track") or "").upper()
        typ = (r.get("type") or "").upper()
        name = (r.get("bootcamp_name") or "").upper()
        start = (r.get("start_date") or "").strip()
        if want_tracks and track not in want_tracks and not any(t in name for t in want_tracks):
            return False
        if want_ft and typ != "FT":
            return False
        if want_pt and typ != "PT":
            return False
        if want_months and start:
            if not _start_date_matches_month(start, want_months, month_prefixs):
                return False
        parsed = _parse_start_date(start)
        if want_year:
            # Keep unparseable dates out of year-scoped answers (can't confirm the year)
            if parsed is None or parsed.year != want_year:
                return False
        if future_only:
            # "Next"/"upcoming" means a future, non-canceled cohort - a past January
            # start date must never be presented as the "next" cohort
            if r.get("canceled") or parsed is None or parsed < today:
                return False
        return True

    has_any_filter = want_tracks or want_ft or want_pt or want_months or want_year or future_only
    filtered = [r for r in rows if matches(r)] if has_any_filter else rows

    # For "next cohort" questions, order by start date so the earliest upcoming
    # cohort appears first in the LLM context
    if future_only:
        filtered.sort(key=lambda r: _parse_start_date(r.get("start_date")) or date.max)

    return filtered[:_MAX_COHORT_ROWS_FOR_LLM]


def _format_cohort_context(rows: list) -> str:
    """Format parsed cohort rows for LLM context."""
    lines = []
    for r in rows:
        canceled = " [CANCELED]" if r.get("canceled") else ""
        parts = [
            f"{r.get('bootcamp_name', '')}",
            f"Track: {r.get('track', '')}",
            f"Type: {r.get('type', '')}",
            f"Lang: {r.get('language', '')}",
            f"Start: {r.get('start_date', '')}",
            f"End: {r.get('end_date', '')}",
            f"Lead Teacher: {r.get('lead_teacher', '')}",
            f"Co-Teacher: {r.get('co_teacher', '')}",
            f"Program (PM): {r.get('program', '')}",
        ]
        lines.append(" | ".join(parts) + canceled)
    return "\n".join(lines) if lines else "(No cohort data)"
