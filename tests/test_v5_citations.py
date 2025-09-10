#!/usr/bin/env python3
"""
Test V5 prompt specifically for citation quality improvements
"""

import openai
import time

from test_config import OPENAI_API_KEY
ASSISTANT_ID = "asst_Zm6nYxM5dhXKDgwzz3yVgYdy"

def test_v5_citations():
    """Test V5 prompt for improved citations"""
    
    print("🔬 Testing V5 Prompt - Enhanced Citations")
    print("=" * 50)
    
    # Update to V5
    try:
        with open('MASTER_PROMPT_V5_CITATIONS.md', 'r') as f:
            v5_prompt = f.read()
            
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        assistant = client.beta.assistants.update(
            assistant_id=ASSISTANT_ID,
            instructions=v5_prompt
        )
        
        print("✅ Updated to V5 prompt with enhanced citations")
        time.sleep(5)
        
    except Exception as e:
        print(f"❌ Error updating prompt: {e}")
        return
    
    # Test questions focusing on citation quality
    test_cases = [
        {
            "question": "What technologies are covered in the Web Development bootcamp?",
            "focus": "Should cite Web_Dev_Remote curriculum specifically"
        },
        {
            "question": "What's the difference in duration between Data Analytics Remote and Berlin?",
            "focus": "Should cite both Remote (360+30) and Berlin (600+50) curricula"
        },
        {
            "question": "What tools are used in DevOps bootcamp?",
            "focus": "Should cite DevOps curriculum specifically"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*20} Citation Test {i}/3 {'='*20}")
        print(f"📝 Question: {test_case['question']}")
        print(f"🎯 Focus: {test_case['focus']}")
        print("-" * 60)
        
        try:
            # Create thread
            thread = client.beta.threads.create()
            
            # Add message
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=test_case["question"]
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
                annotations = messages.data[0].content[0].text.annotations
                
                print(f"✅ Response: {len(response)} chars")
                print(f"📎 Citations: {len(annotations)}")
                
                # Analyze citation quality
                citation_quality = analyze_citation_improvements(response, annotations)
                
                print(f"🎯 Citation Quality Score: {citation_quality['score']}/10")
                
                if citation_quality["course_specific_references"]:
                    print(f"✅ Course-specific references: {citation_quality['course_specific_references']}")
                else:
                    print(f"❌ No course-specific references found")
                
                if citation_quality["document_names_mentioned"]:
                    print(f"✅ Document names mentioned: {citation_quality['document_names_mentioned']}")
                
                # Show response
                print(f"\n📄 Response:")
                print("-" * 40)
                print(response)
                print("-" * 40)
                
                # Show annotations
                if annotations:
                    print(f"\n📎 Citations:")
                    for j, ann in enumerate(annotations, 1):
                        print(f"   {j}. {ann.text}")
                
            else:
                print(f"❌ Run failed: {run.status}")
            
            time.sleep(3)
            
        except Exception as e:
            print(f"❌ Error: {e}")

def analyze_citation_improvements(response, annotations):
    """Analyze if citations have improved with V5 prompt"""
    
    analysis = {
        "score": 0,
        "course_specific_references": [],
        "document_names_mentioned": [],
        "issues": []
    }
    
    response_lower = response.lower()
    
    # Check for course-specific language (worth 3 points)
    course_references = [
        "web development curriculum", "devops curriculum", "data analytics curriculum",
        "ux/ui curriculum", "ai engineering curriculum", "remote curriculum", 
        "berlin curriculum", "bootcamp curriculum", "syllabus"
    ]
    
    found_references = [ref for ref in course_references if ref in response_lower]
    analysis["course_specific_references"] = found_references
    
    if found_references:
        analysis["score"] += 3
    
    # Check for document name mentions (worth 3 points)
    document_patterns = [
        "web_dev_remote", "web_dev_berlin", "data_analytics_remote", "data_analytics_berlin",
        "uxui_remote", "uxui_berlin", "devops_bootcamp", "ai_engineering"
    ]
    
    found_docs = [doc for doc in document_patterns if doc.replace("_", " ") in response_lower]
    analysis["document_names_mentioned"] = found_docs
    
    if found_docs:
        analysis["score"] += 3
    
    # Check citation quality (worth 2 points)
    if annotations:
        analysis["score"] += 2
        
        # Check if citations show actual filenames vs just "source"
        meaningful_citations = []
        for ann in annotations:
            if hasattr(ann, 'text') and ann.text:
                if "source" not in ann.text.lower() or len(ann.text) > 15:
                    meaningful_citations.append(ann.text)
        
        if meaningful_citations:
            analysis["score"] += 2
    
    # Check for variant awareness (worth 2 points)
    variant_awareness = ["remote", "berlin", "variant", "differs", "different"]
    if any(variant in response_lower for variant in variant_awareness):
        analysis["score"] += 2
    
    return analysis

def main():
    print("🧪 V5 Citation Enhancement Test")
    print("=" * 35)
    
    test_v5_citations()
    
    print(f"\n✅ Citation testing complete!")
    print(f"\n💡 Key improvements to look for:")
    print(f"   - Specific curriculum document references")
    print(f"   - Course-specific language in responses")
    print(f"   - Meaningful citations (not just 'source')")
    print(f"   - Variant awareness (Remote vs Berlin)")

if __name__ == "__main__":
    main()
