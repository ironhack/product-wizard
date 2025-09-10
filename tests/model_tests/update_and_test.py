#!/usr/bin/env python3
"""
Update assistant with new prompt and test
"""

import openai
import time

# API Configuration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from test_config import OPENAI_API_KEY
ASSISTANT_ID = "asst_Zm6nYxM5dhXKDgwzz3yVgYdy"

def update_assistant_with_v2():
    """Update assistant with V2 prompt"""
    print("🔄 Updating Assistant with MASTER_PROMPT V2...")
    
    try:
        with open('MASTER_PROMPT_V2.md', 'r') as f:
            new_instructions = f.read()
            
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        assistant = client.beta.assistants.update(
            assistant_id=ASSISTANT_ID,
            instructions=new_instructions
        )
        
        print("✅ Assistant updated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error updating assistant: {e}")
        return False

def test_multiple_questions():
    """Test with multiple questions to see improvement"""
    test_questions = [
        "What technologies are taught in the Web Development bootcamp?",
        "How long is the Data Analytics program and what's included?",
        "What's the difference between Remote and Berlin UX/UI variants?",
        "Tell me about prerequisites for the Data Science program.",
        "What tools are used in the AI Engineering bootcamp?"
    ]
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    results = []
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*20} Test {i}/5 {'='*20}")
        print(f"Question: {question}")
        print("-" * 50)
        
        try:
            # Create thread
            thread = client.beta.threads.create()
            
            # Add message
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=question
            )
            
            # Run assistant
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )
            
            # Wait for completion
            while run.status in ["queued", "in_progress"]:
                time.sleep(1)
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            if run.status == "completed":
                # Get response
                messages = client.beta.threads.messages.list(thread_id=thread.id)
                response = messages.data[0].content[0].text.value
                annotations = messages.data[0].content[0].text.annotations
                
                # Analyze response
                has_sources = "### Sources" in response or "Source:" in response
                has_structure = "##" in response and "**Duration:**" in response
                mentions_documents = any(doc in response.lower() for doc in [".md", ".pdf", "curriculum", "documentation"])
                
                result = {
                    "question": question,
                    "response_length": len(response),
                    "has_citations": len(annotations) > 0,
                    "has_sources_section": has_sources,
                    "follows_structure": has_structure,
                    "mentions_documents": mentions_documents,
                    "response": response[:300] + "..." if len(response) > 300 else response
                }
                
                results.append(result)
                
                print(f"✅ Response: {len(response)} chars")
                print(f"📎 Citations: {len(annotations)}")
                print(f"📋 Has Sources Section: {has_sources}")
                print(f"🏗️ Follows Structure: {has_structure}")
                print(f"📄 Mentions Documents: {mentions_documents}")
                
                # Show first part of response
                print(f"\n📝 Response Preview:")
                print(response[:400] + "..." if len(response) > 400 else response)
                
            else:
                print(f"❌ Run failed: {run.status}")
                
            time.sleep(2)  # Rate limiting
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Generate summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    total = len(results)
    with_sources = sum(1 for r in results if r["has_sources_section"])
    with_structure = sum(1 for r in results if r["follows_structure"])
    mentions_docs = sum(1 for r in results if r["mentions_documents"])
    
    print(f"Total Tests: {total}")
    print(f"With Sources Section: {with_sources}/{total} ({with_sources/total*100:.1f}%)")
    print(f"Follows Structure: {with_structure}/{total} ({with_structure/total*100:.1f}%)")
    print(f"Mentions Documents: {mentions_docs}/{total} ({mentions_docs/total*100:.1f}%)")
    
    # Assessment
    if with_sources >= total * 0.8 and with_structure >= total * 0.8:
        print("\n✅ EXCELLENT: Assistant is following the new format well!")
    elif with_sources >= total * 0.6:
        print("\n⚠️ GOOD: Some improvement, but could be better")
    else:
        print("\n❌ NEEDS WORK: Assistant not following the new format")
    
    return results

def main():
    print("🚀 Assistant Update and Test Tool")
    print("=" * 60)
    
    # Update assistant
    if update_assistant_with_v2():
        print("\n⏳ Waiting 5 seconds for changes to propagate...")
        time.sleep(5)
        
        # Test
        results = test_multiple_questions()
        
        # Save results
        import json
        with open('v2_test_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Detailed results saved to: v2_test_results.json")
        
    else:
        print("❌ Failed to update assistant, skipping tests")

if __name__ == "__main__":
    main()
