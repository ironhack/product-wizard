"""
Configuration module for RAG v2 Application.
Loads environment variables and configuration files.
"""

import os
import logging
import json

import openai
import slack_sdk

# ---------------- Logging ----------------
logger = logging.getLogger(__name__)

# ---------------- Environment Setup ----------------
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
VECTOR_STORE_ID = os.environ.get("OPENAI_VECTOR_STORE_ID", "vs_xxx")

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Initialize Slack WebClient singleton for thread-safe reuse
slack_web_client = slack_sdk.WebClient(token=SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None

# ---------------- Config Loaders ----------------
def load_config_file(filename):
    """Load configuration file from assistant_config directory."""
    try:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(script_dir, 'assistant_config', filename)
        with open(file_path, 'r', encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.info(f"Config {filename} not found. Using defaults. Detail: {e}")
        return ""

# Load all configuration files
MASTER_PROMPT = load_config_file('MASTER_PROMPT.md') or "You are a helpful assistant for Ironhack course information."
GENERATION_INSTRUCTIONS = load_config_file('GENERATION_INSTRUCTIONS.md')
COMPARISON_INSTRUCTIONS = load_config_file('COMPARISON_INSTRUCTIONS.md')
DOCUMENT_FILTERING_INSTRUCTIONS = load_config_file('DOCUMENT_FILTERING_INSTRUCTIONS.md')
COVERAGE_CLASSIFICATION_PROMPT = load_config_file('COVERAGE_CLASSIFICATION.md')
COVERAGE_VERIFICATION_PROMPT = load_config_file('COVERAGE_VERIFICATION.md')
FUN_FALLBACK_GENERATION = load_config_file('FUN_FALLBACK_GENERATION.md')

# New configuration files
QUERY_ENHANCEMENT_PROMPT = load_config_file('QUERY_ENHANCEMENT.md')
PROGRAM_DETECTION_PROMPT = load_config_file('PROGRAM_DETECTION.md')
RELEVANCE_ASSESSMENT_PROMPT = load_config_file('RELEVANCE_ASSESSMENT.md')
FAITHFULNESS_VERIFICATION_PROMPT = load_config_file('FAITHFULNESS_VERIFICATION.md')
REFINEMENT_STRATEGIES_PROMPT = load_config_file('REFINEMENT_STRATEGIES.md')
COHORT_CALENDAR_CLASSIFICATION_PROMPT = load_config_file('COHORT_CALENDAR_CLASSIFICATION.md')
COHORT_CALENDAR_FILTER_EXTRACTION_PROMPT = load_config_file('COHORT_CALENDAR_FILTER_EXTRACTION.md')

# Cohort calendar sheet (optional; if not set, cohort path is disabled)
COHORT_CALENDAR_SHEET_ID = os.environ.get("COHORT_CALENDAR_SHEET_ID", "1QEDMqp71oRPJ3CRr7f_DP7l6_uNE_lSjV5OJ3BlHRcA")
# Tab gid from URL (Bootcamps Tracker); we use this tab so layout matches the CSV export
COHORT_CALENDAR_SHEET_GID = int(os.environ["COHORT_CALENDAR_SHEET_GID"]) if os.environ.get("COHORT_CALENDAR_SHEET_GID", "").strip().isdigit() else 1379215013


def cohort_calendar_sheet_edit_url() -> str:
    """Direct link to the Bootcamps Tracker tab (for user-facing messages)."""
    return (
        f"https://docs.google.com/spreadsheets/d/{COHORT_CALENDAR_SHEET_ID}/edit"
        f"?gid={COHORT_CALENDAR_SHEET_GID}#gid={COHORT_CALENDAR_SHEET_GID}"
    )


# Load program synonyms
PROGRAM_SYNONYMS_TEXT = load_config_file('PROGRAM_SYNONYMS.json') or '{}'
try:
    PROGRAM_SYNONYMS = json.loads(PROGRAM_SYNONYMS_TEXT)
except Exception:
    PROGRAM_SYNONYMS = {}
