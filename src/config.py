"""
Configuration module for RAG v2 Application.
Loads environment variables and configuration files.
"""

import os
import logging
import json

import openai

# ---------------- Logging ----------------
logger = logging.getLogger(__name__)

# ---------------- Environment Setup ----------------
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
VECTOR_STORE_ID = os.environ.get("OPENAI_VECTOR_STORE_ID", "vs_xxx")

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

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

# Load program synonyms
PROGRAM_SYNONYMS_TEXT = load_config_file('PROGRAM_SYNONYMS.json') or '{}'
try:
    PROGRAM_SYNONYMS = json.loads(PROGRAM_SYNONYMS_TEXT)
except Exception:
    PROGRAM_SYNONYMS = {}
