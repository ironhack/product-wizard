"""
Flask Application Initialization and Main Entry Point
Initializes the Flask app, Slack Bolt app, and HTTP route handlers.
"""

import os
import logging
from flask import Flask, request as flask_request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

# ---------------- Configuration ----------------
from src.config import (
    SLACK_BOT_TOKEN,
    SLACK_SIGNING_SECRET,
    VECTOR_STORE_ID,
)

# ---------------- Slack Integration ----------------
from src.slack_integration import handle_mention, handle_message

# ---------------- Logging ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- Flask App Initialization ----------------

# Initialize Flask app first
flask_app = Flask(__name__)

# Initialize Slack app with error handling
try:
    slack_app = App(
        token=SLACK_BOT_TOKEN,
        signing_secret=SLACK_SIGNING_SECRET
    )

    # Register Slack event handlers
    slack_app.event("app_mention")(handle_mention)
    slack_app.event("message")(handle_message)

    slack_handler = SlackRequestHandler(slack_app)
    logger.info("Slack app initialized successfully")

except Exception as e:
    logger.warning(f"Failed to initialize Slack app: {e}")
    # Create a dummy handler for when Slack is not available
    slack_app = None
    slack_handler = None

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle Slack events."""
    if slack_handler:
        return slack_handler.handle(flask_request)
    else:
        return {"error": "Slack integration not available"}, 503

@flask_app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "rag-v2",
        "vector_store_id": VECTOR_STORE_ID
    }

# ---------------- Main ----------------

if __name__ == "__main__":
    # Start the server
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting RAG v2 application on port {port}")
    flask_app.run(host="0.0.0.0", port=port)
