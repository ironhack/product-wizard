import os
import sys
import time

# Set dummy Slack env to bypass initialization errors during import
os.environ.setdefault("SLACK_BOT_TOKEN", "xapp-1-dummy")
os.environ.setdefault("SLACK_SIGNING_SECRET", "dummy")

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from app_langgraph_rag import create_rag_graph  # type: ignore
from langchain_core.messages import HumanMessage


def run_three_turn_scenario():
    graph = create_rag_graph()

    thread_id = f"adhoc-{int(time.time())}"

    # Turn 1: Data Analytics question (Tableau vs Power BI)
    state = {
        "query": "In the Data analytics bootcamp, do we teach Tableau or Power BI, or both?",
        "conversation_id": thread_id,
        "messages": [HumanMessage(content="In the Data analytics bootcamp, do we teach Tableau or Power BI, or both?")],
        "processing_time": 0.0,
        "slack_mode": False,
    }
    # Provide configurables for checkpointer
    state = graph.invoke(state, config={"configurable": {"thread_id": thread_id}})
    print("TURN 1 RESPONSE:\n", state.get("response"))
    print("TURN 1 SOURCES:", state.get("final_sources") or state.get("sources"))

    # Build state for second turn including prior messages and response
    messages = list(state.get("messages", []))

    # Turn 2: Follow-up: "which are all the tools that they will use?"
    q2 = "Which are all the tools that they will use?"
    state2 = {
        "query": q2,
        "conversation_id": thread_id,
        "messages": messages + [HumanMessage(content=q2)],
        "processing_time": 0.0,
        "slack_mode": False,
    }
    state2 = graph.invoke(state2, config={"configurable": {"thread_id": thread_id}})
    print("\nTURN 2 RESPONSE:\n", state2.get("response"))
    print("TURN 2 SOURCES:", state2.get("final_sources") or state2.get("sources"))

    # Turn 3: Follow-up: "is the data real?"
    messages2 = list(state2.get("messages", []))
    q3 = "Is the data that we use in the bootcamp to practice real data?"
    state3 = {
        "query": q3,
        "conversation_id": thread_id,
        "messages": messages2 + [HumanMessage(content=q3)],
        "processing_time": 0.0,
        "slack_mode": False,
    }
    state3 = graph.invoke(state3, config={"configurable": {"thread_id": thread_id}})
    print("\nTURN 3 RESPONSE:\n", state3.get("response"))
    print("TURN 3 SOURCES:", state3.get("final_sources") or state3.get("sources"))


if __name__ == "__main__":
    # Ensure OpenAI key exists or use a placeholder that will cause retrieval to remain deterministic
    if not os.environ.get("OPENAI_API_KEY"):
        print("WARNING: OPENAI_API_KEY not set. The test may fail on AI calls.")
    run_three_turn_scenario()
