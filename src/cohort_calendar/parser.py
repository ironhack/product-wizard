"""
Parse RMT Bootcamps Tracker sheet rows into structured cohort records.
Marks rows as canceled when Cohort Start Date is missing or row contains "Cancelled".
"""

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# Column indices (0-based) for the first data row in the sheet.
# CSV layout: col0 empty, col1 Campus ID, col2 Bootcamp Name (e.g. WD-FT-EN-JAN26), col3 Track, col4 Type, col5 Language, ...
# then col9 Cohort Start Date, col10 End, col13 Program, col14 Lead Teacher, col15 Co-Teacher
BOOTCAMP_NAME_COL = 2
TRACK_COL = 3
TYPE_COL = 4
LANGUAGE_COL = 5
START_DATE_COL = 9
END_DATE_COL = 10
PROGRAM_COL = 13
LEAD_TEACHER_COL = 14
CO_TEACHER_COL = 15

# First row index that contains data (skip header rows; sheet has ~5 header lines)
FIRST_DATA_ROW = 5

# Header labels we look for to detect column indices (case-insensitive)
_HEADER_BOOTCAMP = "bootcamp name"
_HEADER_TRACK = "track"
_HEADER_TYPE = "type"
_HEADER_LANGUAGE = "language"
_HEADER_START = "cohort start date"
_HEADER_END = "cohort end date"
_HEADER_PROGRAM = "program"
_HEADER_LEAD = "lead teacher"
_HEADER_CO = "co-teacher"


def _detect_column_indices(raw_rows: List[List[Any]]) -> Tuple[int, Dict[str, int]]:
    """
    Find header row containing 'Bootcamp Name' / 'Cohort Start Date' / 'Lead Teacher',
    return (first_data_row_index, {col_name: index}).
    If not found, return (FIRST_DATA_ROW, {}) and caller uses fixed constants.
    """
    for row_idx, row in enumerate(raw_rows[:30]):
        if not row:
            continue
        row_lower = [str(c).strip().lower() for c in row]
        bootcamp_col = next((i for i, c in enumerate(row_lower) if _HEADER_BOOTCAMP in c), None)
        start_col = next((i for i, c in enumerate(row_lower) if _HEADER_START in c), None)
        # Lead Teacher: cell must contain "lead teacher" and NOT "co-teacher" (so we never match "Co-Teacher (if it applies)")
        lead_col = next((i for i, c in enumerate(row_lower) if _HEADER_LEAD in c and "co-teacher" not in c), None)
        co_col = next((i for i, c in enumerate(row_lower) if _HEADER_CO in c or "co-teacher" in c), None)
        if bootcamp_col is None or (start_col is None and lead_col is None):
            continue
        cols = {
            "bootcamp_name": bootcamp_col,
            "track": next((i for i, c in enumerate(row_lower) if _HEADER_TRACK in c and (c == "track" or "track" in c)), bootcamp_col + 1),
            "type": next((i for i, c in enumerate(row_lower) if _HEADER_TYPE in c and (c == "type" or "type" in c)), bootcamp_col + 2),
            "language": next((i for i, c in enumerate(row_lower) if _HEADER_LANGUAGE in c), bootcamp_col + 3),
            "start_date": start_col or 9,
            "end_date": next((i for i, c in enumerate(row_lower) if _HEADER_END in c), start_col + 1 if start_col is not None else 10),
            "program": next((i for i, c in enumerate(row_lower) if _HEADER_PROGRAM in c and "program" in c), 13),
            "lead_teacher": lead_col if lead_col is not None else 14,
            "co_teacher": co_col if co_col is not None else (lead_col + 1 if lead_col is not None else 15),
        }
        # Find first row that looks like cohort data (skip merged/continuation header rows)
        first_data = row_idx + 1
        for j in range(row_idx + 1, min(row_idx + 20, len(raw_rows))):
            row_j = raw_rows[j]
            if not row_j or _is_empty_row(row_j):
                continue
            padded_j = (row_j + [""] * (cols["co_teacher"] + 1))[: cols["co_teacher"] + 1]
            bc = _cell(padded_j, bootcamp_col)
            if _looks_like_cohort_code(bc):
                first_data = j
                break
        return (first_data, cols)
    return (FIRST_DATA_ROW, {})
    

def _is_header_label(bootcamp_name: str) -> bool:
    """True if the cell looks like a header label, not cohort data."""
    if not bootcamp_name or not bootcamp_name.strip():
        return True
    u = bootcamp_name.upper().strip()
    if "BOOTCAMP" in u or "TRACK" in u or "TEACHER" in u or "DATE" in u or "PROGRAM" in u or "LANGUAGE" in u or "TYPE" in u:
        return True
    return False


def _looks_like_cohort_code(s: str) -> bool:
    """True if the cell looks like a cohort code (e.g. WD-FT-EN-MAR26, ML-FT-EN-FEB26)."""
    if not s or len(s) < 6:
        return False
    u = s.upper().strip()
    if "-" not in u or ("FT" not in u and "PT" not in u):
        return False
    if _is_header_label(s):
        return False
    return True


def parse_cohort_rows(raw_rows: List[List[Any]]) -> List[Dict[str, Any]]:
    """
    Parse sheet rows into list of cohort dicts with normalized keys.
    Detects header row to set column indices; falls back to fixed indices for known CSV layout.
    Each cohort has: bootcamp_name, track, type, language, start_date, end_date,
    program (PM), lead_teacher, co_teacher, canceled.
    """
    if not raw_rows or len(raw_rows) < 2:
        return []

    first_data_row, detected = _detect_column_indices(raw_rows)
    if detected:
        cols = detected
        logger.info("Parser using detected header: bootcamp_name=%s start_date=%s lead_teacher=%s co_teacher=%s", cols.get("bootcamp_name"), cols.get("start_date"), cols.get("lead_teacher"), cols.get("co_teacher"))
    else:
        cols = {
            "bootcamp_name": BOOTCAMP_NAME_COL,
            "track": TRACK_COL,
            "type": TYPE_COL,
            "language": LANGUAGE_COL,
            "start_date": START_DATE_COL,
            "end_date": END_DATE_COL,
            "program": PROGRAM_COL,
            "lead_teacher": LEAD_TEACHER_COL,
            "co_teacher": CO_TEACHER_COL,
        }

    result = []
    max_col = max(cols.values()) + 1 if cols else CO_TEACHER_COL + 1
    for i in range(first_data_row, len(raw_rows)):
        row = raw_rows[i]
        if not row or _is_empty_row(row):
            continue
        padded = (row + [""] * max_col)[:max_col]
        bootcamp_name = _cell(padded, cols["bootcamp_name"])
        if not bootcamp_name or not bootcamp_name.strip():
            continue
        if _is_header_label(bootcamp_name):
            continue
        start_date = _cell(padded, cols["start_date"])
        end_date = _cell(padded, cols["end_date"])
        raw_text = " ".join(str(c) for c in row).upper()
        canceled = _is_canceled(start_date, raw_text)
        result.append({
            "bootcamp_name": bootcamp_name.strip(),
            "track": _cell(padded, cols["track"]).strip(),
            "type": _cell(padded, cols["type"]).strip(),
            "language": _cell(padded, cols["language"]).strip(),
            "start_date": start_date.strip() if start_date else "",
            "end_date": end_date.strip() if end_date else "",
            "program": _cell(padded, cols["program"]).strip(),
            "lead_teacher": _cell(padded, cols["lead_teacher"]).strip(),
            "co_teacher": _cell(padded, cols["co_teacher"]).strip(),
            "canceled": canceled,
        })
    return result


def _cell(row: List[Any], col: int) -> str:
    if col < 0 or col >= len(row):
        return ""
    v = row[col]
    return str(v).strip() if v is not None else ""


def _is_empty_row(row: List[Any]) -> bool:
    return not any(c and str(c).strip() for c in row)


def _is_canceled(start_date: str, raw_row_text: str) -> bool:
    """True if cohort is canceled: missing start date and/or cell contains 'Cancelled'."""
    no_start = not (start_date and start_date.strip())
    has_cancelled = "CANCELLED" in raw_row_text
    return no_start or has_cancelled
