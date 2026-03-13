"""
Google Sheets client for RMT Bootcamps Tracker.
Fetches the first tab using a service account (env: GOOGLE_SHEETS_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS).
"""

import json
import logging
import os
from typing import Any, List, Optional

from src.config import COHORT_CALENDAR_SHEET_ID, COHORT_CALENDAR_SHEET_GID

logger = logging.getLogger(__name__)


def fetch_cohort_calendar_data() -> List[List[Any]]:
    """
    Fetch all values from the first tab of the cohort calendar sheet.
    Returns list of rows (each row is a list of cell values), or empty list on failure.
    """
    credentials = _get_credentials()
    if not credentials:
        logger.warning("No Google Sheets credentials; cohort calendar path will return fallback message.")
        return []

    try:
        import gspread
        gc = gspread.service_account_from_dict(credentials)
        sh = gc.open_by_key(COHORT_CALENDAR_SHEET_ID)
        try:
            wks = sh.get_worksheet_by_id(COHORT_CALENDAR_SHEET_GID)
        except Exception:
            wks = sh.get_worksheet(0)
        rows = wks.get_all_values()
        return rows
    except Exception as e:
        logger.exception("Failed to fetch cohort calendar sheet: %s", e)
        return []


def _get_credentials() -> Optional[dict]:
    """Load service account credentials from env (JSON string or path to JSON file)."""
    raw = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON", "").strip()
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("Invalid GOOGLE_SHEETS_CREDENTIALS_JSON: %s", e)
            return None
    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if path and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to read credentials file %s: %s", path, e)
            return None
    return None
