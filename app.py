from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request
import openai
import os

slack_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)
handler = SlackRequestHandler(slack_app)
openai.api_key = os.environ["OPENAI_API_KEY"]
ASSISTANT_ID = os.environ["OPENAI_ASSISTANT_ID"]

@slack_app.event("app_mention")
def handle_mention(event, say):
    user_message = event['text']
    # Send to OpenAI Assistant API
    thread = openai.beta.threads.create(messages=[{"role": "user", "content": user_message}])
    response = openai.beta.assistants.messages.create(
        assistant_id=ASSISTANT_ID,
        thread_id=thread.id,
        messages=[{"role": "user", "content": user_message}]
    )
    answer = response.data[0]['content']
    say(answer)

flask_app = Flask(__name__)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    flask_app.run(port=3000)