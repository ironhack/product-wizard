#!/usr/bin/env python3
"""
Simple test script to check if the assistant is working with file search.
Run this after setting up your environment variables.
"""

import openai
import os
import time

def test_assistant():
    """Test the assistant with a simple question about courses"""
    
    # Setup (same as in app.py)
    openai.api_key = os.environ["OPENAI_API_KEY"]
    ASSISTANT_ID = os.environ["OPENAI_ASSISTANT_ID"]
    
    print(f"Testing Assistant ID: {ASSISTANT_ID}")
    
    try:
        # Create a new thread
        thread = openai.beta.threads.create()
        print(f"Created thread: {thread.id}")
        
        # Add a test message
        test_question = "What technologies are covered in the Web Development bootcamp?"
        print(f"Asking: {test_question}")
        
        message = openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=test_question
        )
        
        # Run the assistant
        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
        
        print(f"Created run: {run.id}")
        
        # Wait for completion
        while run.status in ["queued", "in_progress"]:
            print(f"Status: {run.status}")
            time.sleep(1)
            run = openai.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
        
        print(f"Final status: {run.status}")
        
        if run.status == "completed":
            # Get the response
            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            response = messages.data[0].content[0].text.value
            annotations = messages.data[0].content[0].text.annotations
            
            print("\n" + "="*60)
            print("RESPONSE:")
            print("="*60)
            print(response)
            print("\n" + "="*60)
            print(f"Citations found: {len(annotations)}")
            
            for i, annotation in enumerate(annotations):
                print(f"Citation {i+1}: {annotation}")
                
        elif run.status == "failed":
            print(f"Run failed: {run.last_error}")
            
        else:
            print(f"Unexpected status: {run.status}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_assistant()
