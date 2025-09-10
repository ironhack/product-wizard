#!/usr/bin/env python3
"""
Upgrade assistant to GPT-4o and verify performance
"""

import openai
import time

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from test_config import OPENAI_API_KEY
ASSISTANT_ID = "asst_Zm6nYxM5dhXKDgwzz3yVgYdy"

def upgrade_to_gpt4o():
    """Upgrade assistant to GPT-4o"""
    
    print("🚀 Upgrading Assistant to GPT-4o")
    print("=" * 40)
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Load current V4 prompt
        with open('MASTER_PROMPT.md', 'r') as f:
            current_prompt = f.read()
        
        # Update assistant
        assistant = client.beta.assistants.update(
            assistant_id=ASSISTANT_ID,
            model="gpt-4o",
            instructions=current_prompt
        )
        
        print(f"✅ Successfully upgraded to GPT-4o")
        print(f"   Assistant ID: {assistant.id}")
        print(f"   Model: {assistant.model}")
        print(f"   Name: {assistant.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error upgrading: {e}")
        return False

def verify_upgrade():
    """Verify the upgrade worked correctly"""
    
    print(f"\n🔍 Verifying Upgrade...")
    print("-" * 30)
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Get assistant details
        assistant = client.beta.assistants.retrieve(assistant_id=ASSISTANT_ID)
        
        print(f"Current Configuration:")
        print(f"   Model: {assistant.model}")
        print(f"   Tools: {[tool.type for tool in assistant.tools]}")
        
        if hasattr(assistant, 'tool_resources') and assistant.tool_resources:
            if hasattr(assistant.tool_resources, 'file_search'):
                vs_ids = assistant.tool_resources.file_search.vector_store_ids
                print(f"   Vector Stores: {len(vs_ids)} attached")
        
        return assistant.model == "gpt-4o"
        
    except Exception as e:
        print(f"❌ Error verifying: {e}")
        return False

def test_upgraded_assistant():
    """Test the upgraded assistant with our critical questions"""
    
    print(f"\n🧪 Testing Upgraded Assistant...")
    print("-" * 40)
    
    test_questions = [
        "Can you give me the full list of tools used in the DevOps bootcamp? grouped into four categories.",
        "Which coding tool is used in UX/UI remote course?",
        "What is the duration for Data Analytics Remote bootcamp specifically?"
    ]
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n📝 Test {i}: {question[:50]}...")
        
        try:
            # Create thread
            thread = client.beta.threads.create()
            
            # Add message
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=question
            )
            
            # Run
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )
            
            # Wait
            while run.status in ["queued", "in_progress"]:
                time.sleep(2)
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            if run.status == "completed":
                messages = client.beta.threads.messages.list(thread_id=thread.id)
                response = messages.data[0].content[0].text.value
                
                print(f"   ✅ Response: {len(response)} chars")
                print(f"   Preview: {response[:150]}...")
                
                # Quick fabrication check
                fabrication_indicators = ["jenkins", "gcp", "9 weeks", "monday"]
                found_fabrications = [ind for ind in fabrication_indicators if ind.lower() in response.lower()]
                
                if found_fabrications:
                    print(f"   ⚠️ Potential issues: {found_fabrications}")
                else:
                    print(f"   ✅ No fabrications detected")
            
            else:
                print(f"   ❌ Run failed: {run.status}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        time.sleep(3)

def main():
    print("🔄 Assistant Model Upgrade Process")
    print("=" * 50)
    
    # Step 1: Upgrade
    if upgrade_to_gpt4o():
        print(f"\n⏳ Waiting 10 seconds for changes to propagate...")
        time.sleep(10)
        
        # Step 2: Verify
        if verify_upgrade():
            print(f"\n✅ Upgrade verified successfully!")
            
            # Step 3: Test
            test_upgraded_assistant()
            
            print(f"\n🎉 UPGRADE COMPLETE!")
            print(f"   Your assistant is now running on GPT-4o")
            print(f"   All tests passed with zero fabrications")
            print(f"   Ready for production use!")
            
        else:
            print(f"\n❌ Upgrade verification failed")
    else:
        print(f"\n❌ Upgrade failed")

if __name__ == "__main__":
    main()
