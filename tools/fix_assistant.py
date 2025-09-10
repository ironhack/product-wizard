#!/usr/bin/env python3
"""
Script to diagnose and fix the assistant configuration issues
"""

import openai
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration from environment
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID")

if not OPENAI_API_KEY or not ASSISTANT_ID:
    raise ValueError("Please set OPENAI_API_KEY and OPENAI_ASSISTANT_ID in your .env file")

openai.api_key = OPENAI_API_KEY

def check_vector_stores():
    """Check all vector stores available"""
    print("🔍 Checking all Vector Stores...")
    print("=" * 50)
    
    try:
        # Try the newer client approach
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        vector_stores = client.beta.vector_stores.list()
        
        print(f"Found {len(vector_stores.data)} vector stores:")
        
        for vs in vector_stores.data:
            print(f"\n📦 Vector Store: {vs.id}")
            print(f"   Name: {vs.name}")
            print(f"   Status: {vs.status}")
            print(f"   File counts: {vs.file_counts}")
            print(f"   Created: {vs.created_at}")
            
            # Check files in this vector store
            try:
                files = client.beta.vector_stores.files.list(vector_store_id=vs.id)
                print(f"   Files ({len(files.data)}):")
                
                for file in files.data[:10]:  # Show first 10
                    try:
                        file_details = client.files.retrieve(file.id)
                        print(f"      - {file_details.filename} ({file.status})")
                    except Exception as e:
                        print(f"      - {file.id} ({file.status}) - Error getting details: {e}")
                        
            except Exception as e:
                print(f"   ❌ Error listing files: {e}")
        
        return vector_stores.data
        
    except Exception as e:
        print(f"❌ Error listing vector stores: {e}")
        return []

def check_assistant_detailed():
    """Check assistant configuration in detail"""
    print("\n🤖 Checking Assistant Configuration...")
    print("=" * 50)
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        assistant = client.beta.assistants.retrieve(assistant_id=ASSISTANT_ID)
        
        print(f"✅ Assistant ID: {assistant.id}")
        print(f"✅ Name: {assistant.name}")
        print(f"✅ Model: {assistant.model}")
        print(f"✅ Created: {assistant.created_at}")
        
        print(f"\n🛠️ Tools ({len(assistant.tools)}):")
        for i, tool in enumerate(assistant.tools):
            print(f"   {i+1}. {tool.type}")
        
        print(f"\n🔧 Tool Resources:")
        if assistant.tool_resources:
            print(json.dumps(assistant.tool_resources, indent=4, default=str))
        else:
            print("   ❌ No tool resources found!")
        
        print(f"\n📝 Instructions Preview:")
        print(assistant.instructions[:500] + "..." if len(assistant.instructions) > 500 else assistant.instructions)
        
        return assistant
        
    except Exception as e:
        print(f"❌ Error retrieving assistant: {e}")
        return None

def update_assistant_instructions():
    """Update assistant instructions to force citations"""
    print("\n🔄 Updating Assistant Instructions...")
    print("=" * 50)
    
    # Read the current MASTER_PROMPT
    try:
        with open('MASTER_PROMPT.md', 'r') as f:
            new_instructions = f.read()
    except Exception as e:
        print(f"❌ Error reading MASTER_PROMPT.md: {e}")
        return False
    
    # Add explicit citation instructions
    citation_instructions = """

## CRITICAL: Citation Requirements
- ALWAYS include citations in the format 【source_reference】 when using information from files
- Every fact from documents MUST have a citation
- Use the exact file names and section references
- Never provide information without proper citations when available in files
"""
    
    updated_instructions = new_instructions + citation_instructions
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        assistant = client.beta.assistants.update(
            assistant_id=ASSISTANT_ID,
            instructions=updated_instructions
        )
        
        print("✅ Assistant instructions updated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error updating assistant: {e}")
        return False

def test_with_updated_prompt():
    """Test the assistant with updated prompt"""
    print("\n🧪 Testing Updated Assistant...")
    print("=" * 50)
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Create thread
        thread = client.beta.threads.create()
        
        # Test question
        test_question = "What technologies are taught in the Web Development bootcamp? Please include citations."
        print(f"Question: {test_question}")
        
        # Add message
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=test_question
        )
        
        # Run assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
        
        # Wait for completion
        import time
        while run.status in ["queued", "in_progress"]:
            time.sleep(2)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            print(f"Status: {run.status}")
        
        if run.status == "completed":
            # Get response
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            response = messages.data[0].content[0].text.value
            annotations = messages.data[0].content[0].text.annotations
            
            print(f"\n📝 Response ({len(response)} chars):")
            print("-" * 30)
            print(response)
            print("-" * 30)
            print(f"📎 Citations: {len(annotations)}")
            
            for i, annotation in enumerate(annotations):
                print(f"   {i+1}. {annotation}")
            
            return len(annotations) > 0
            
        else:
            print(f"❌ Run failed: {run.status}")
            if hasattr(run, 'last_error'):
                print(f"Error: {run.last_error}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing: {e}")
        return False

def main():
    print("🚀 Assistant Diagnostics and Fix Tool")
    print("=" * 60)
    
    # Step 1: Check vector stores
    vector_stores = check_vector_stores()
    
    # Step 2: Check assistant config
    assistant = check_assistant_detailed()
    
    if not assistant:
        print("❌ Cannot proceed without assistant access")
        return
    
    # Step 3: Update instructions
    if update_assistant_instructions():
        # Step 4: Test
        citations_working = test_with_updated_prompt()
        
        if citations_working:
            print("\n✅ SUCCESS: Citations are now working!")
        else:
            print("\n❌ ISSUE: Still no citations after update")
    else:
        print("\n❌ Failed to update assistant instructions")

if __name__ == "__main__":
    main()
