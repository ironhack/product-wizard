#!/usr/bin/env python3
"""
Manual assistant test - ask question and get response for human evaluation
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
    print("🤖 MANUAL ASSISTANT TEST")
    print("=" * 60)
    
    questions = [
        "What tools and technologies are covered in the DevOps bootcamp?",
        "What programming languages are taught in the AI Engineering bootcamp?"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n📝 QUESTION {i}: {question}")
        print("-" * 60)
        
        answer = ask_assistant(question)
        
        if answer:
            print(f"🤖 ASSISTANT ANSWER:")
            print(answer)
        else:
            print("❌ No answer received")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
