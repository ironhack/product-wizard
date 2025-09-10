"""
Test configuration utilities for loading environment variables
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get required environment variables with fallbacks for testing
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID")

# Validate required variables
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

if not OPENAI_ASSISTANT_ID:
    raise ValueError("OPENAI_ASSISTANT_ID environment variable is required")
