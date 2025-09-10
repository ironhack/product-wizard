#!/usr/bin/env python3
"""
Quick test of AI Engineering question for consistency.
"""
import time
from openai import OpenAI
from test_config import OPENAI_API_KEY, OPENAI_ASSISTANT_ID

def ask_assistant(question):
    """Ask the assistant a question and return the response"""
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(thread_id=thread.id, role="user", content=question)
        
        run = client.beta.threads.runs.create(thread_id=thread.id, assistant_id=OPENAI_ASSISTANT_ID)
        
        while run.status in ['queued', 'in_progress', 'cancelling']:
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        
        if run.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            for message in messages.data:
                if message.role == 'assistant':
                    return message.content[0].text.value
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def main():
    print("🧪 QUICK AI ENGINEERING TEST")
    print("=" * 50)
    
    question = "What programming languages are taught in the AI Engineering bootcamp?"
    print(f"Question: {question}")
    
    answer = ask_assistant(question)
    
    print(f"\n📄 ANSWER:")
    print(answer)
    
    if answer:
        # Check for problematic phrases
        problematic = ["Great question!", "comprehensive", "real-world", "hands-on", "preparing students"]
        found_issues = [p for p in problematic if p.lower() in answer.lower()]
        
        has_citation = "according to" in answer.lower() or "curriculum" in answer.lower()
        mentions_python = "python" in answer.lower()
        
        print(f"\n📊 QUICK ASSESSMENT:")
        print(f"Has citation: {has_citation}")
        print(f"Mentions Python: {mentions_python}")
        print(f"Problematic phrases: {found_issues}")
        
        if has_citation and mentions_python and len(found_issues) <= 1:
            print("✅ LOOKS GOOD!")
            return True
        else:
            print("❌ NEEDS IMPROVEMENT")
            return False
    else:
        print("❌ NO ANSWER RECEIVED")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
