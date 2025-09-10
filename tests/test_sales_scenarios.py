#!/usr/bin/env python3
"""
Test real sales scenarios with the V3 prompt
"""

import openai
import time
import json

# API Configuration
from test_config import OPENAI_API_KEY
ASSISTANT_ID = "asst_Zm6nYxM5dhXKDgwzz3yVgYdy"

def update_to_v3():
    """Update assistant with V3 prompt"""
    print("🔄 Updating Assistant to V3...")
    
    try:
        with open('MASTER_PROMPT_V3.md', 'r') as f:
            new_instructions = f.read()
            
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        assistant = client.beta.assistants.update(
            assistant_id=ASSISTANT_ID,
            instructions=new_instructions
        )
        
        print("✅ Assistant updated to V3")
        return True
        
    except Exception as e:
        print(f"❌ Error updating assistant: {e}")
        return False

def test_sales_questions():
    """Test the exact sales scenarios provided"""
    
    # Real sales questions from the user
    sales_questions = [
        {
            "question": "Can you give me the full list of tools used in the DevOps bootcamp? grouped into four categories.",
            "expected_content": ["tools", "devops", "categories"],
            "check_for_fabrication": ["docker", "kubernetes", "jenkins"]  # Common tools that might be invented
        },
        {
            "question": "Which coding tool is used in UX/UI remote course?",
            "expected_content": ["ux/ui", "coding", "tool"],
            "check_for_fabrication": ["visual studio", "sublime", "atom"]  # Common editors that might be invented
        },
        {
            "question": "What is the course that uses most Python?",
            "expected_content": ["python", "course"],
            "check_for_fabrication": ["data science", "ai engineering"]  # Should verify which actually uses most Python
        },
        {
            "question": "What projects will students be working on in Web Development bootcamp Full time Berlin?",
            "expected_content": ["projects", "web development", "berlin"],
            "check_for_fabrication": ["portfolio", "e-commerce", "social media"]  # Common project types that might be invented
        },
        {
            "question": "What certifications are available for AI Engineering students after they finish the bootcamp?",
            "expected_content": ["certifications", "ai engineering"],
            "check_for_fabrication": ["aws", "google cloud", "microsoft azure"]  # Certifications that might be invented
        }
    ]
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    results = []
    
    for i, test_case in enumerate(sales_questions, 1):
        print(f"\n{'='*20} Sales Test {i}/5 {'='*20}")
        print(f"Question: {test_case['question']}")
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
                
                # Analyze response for sales context
                analysis = analyze_sales_response(response, test_case)
                
                result = {
                    "question": test_case["question"],
                    "response": response,
                    "analysis": analysis,
                    "status": "success"
                }
                
                results.append(result)
                
                # Display results
                print(f"✅ Response: {len(response)} chars")
                print(f"📞 Sales-Ready: {analysis['sales_ready']}")
                print(f"❌ Fabrication Risk: {analysis['fabrication_risk']}")
                print(f"📋 Documentation-Based: {analysis['documentation_based']}")
                
                # Show response preview
                print(f"\n📝 Response Preview:")
                print("-" * 30)
                print(response[:500] + "..." if len(response) > 500 else response)
                print("-" * 30)
                
                # Highlight any concerns
                if analysis['concerns']:
                    print(f"⚠️ Concerns: {', '.join(analysis['concerns'])}")
                
            else:
                print(f"❌ Run failed: {run.status}")
                
            time.sleep(2)  # Rate limiting
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Generate sales-focused summary
    generate_sales_summary(results)
    
    return results

def analyze_sales_response(response, test_case):
    """Analyze if response is good for sales context"""
    analysis = {
        "sales_ready": False,
        "fabrication_risk": False,
        "documentation_based": False,
        "concerns": []
    }
    
    response_lower = response.lower()
    
    # Check for sales readiness
    sales_indicators = [
        "great question",
        "the program covers",
        "students work on",
        "this gives students",
        "based on the curriculum"
    ]
    
    if any(indicator in response_lower for indicator in sales_indicators):
        analysis["sales_ready"] = True
    
    # Check for fabrication risk
    fabrication_flags = [
        "typically", "usually", "generally", "commonly",
        "standard", "normal", "about", "approximately",
        "should", "likely", "probably"
    ]
    
    found_flags = [flag for flag in fabrication_flags if flag in response_lower]
    if found_flags:
        analysis["fabrication_risk"] = True
        analysis["concerns"].append(f"Fabrication flags: {found_flags}")
    
    # Check for documentation basis
    doc_indicators = [
        "curriculum documentation",
        "according to",
        "from the documentation",
        "i don't have that specific information",
        "not available in the curriculum"
    ]
    
    if any(indicator in response_lower for indicator in doc_indicators):
        analysis["documentation_based"] = True
    
    # Check for potential invented content
    for fabrication_term in test_case.get("check_for_fabrication", []):
        if fabrication_term.lower() in response_lower:
            analysis["concerns"].append(f"Potential fabrication: mentions '{fabrication_term}'")
    
    # Check response length (sales context)
    if len(response) < 100:
        analysis["concerns"].append("Response may be too brief for sales context")
    elif len(response) > 2000:
        analysis["concerns"].append("Response may be too long for phone conversation")
    
    return analysis

def generate_sales_summary(results):
    """Generate summary focused on sales team needs"""
    print(f"\n{'='*60}")
    print("📞 SALES READINESS REPORT")
    print("=" * 60)
    
    total = len(results)
    sales_ready = sum(1 for r in results if r["analysis"]["sales_ready"])
    fabrication_risk = sum(1 for r in results if r["analysis"]["fabrication_risk"])
    doc_based = sum(1 for r in results if r["analysis"]["documentation_based"])
    
    print(f"Total Questions Tested: {total}")
    print(f"Sales-Ready Responses: {sales_ready}/{total} ({sales_ready/total*100:.1f}%)")
    print(f"Documentation-Based: {doc_based}/{total} ({doc_based/total*100:.1f}%)")
    print(f"Fabrication Risk: {fabrication_risk}/{total} ({fabrication_risk/total*100:.1f}%)")
    
    # Detailed feedback for each question
    print(f"\n📋 Detailed Analysis:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['question'][:60]}...")
        analysis = result["analysis"]
        
        status_icon = "✅" if analysis["sales_ready"] and analysis["documentation_based"] and not analysis["fabrication_risk"] else "⚠️"
        print(f"   {status_icon} Status: ", end="")
        
        if analysis["sales_ready"] and analysis["documentation_based"] and not analysis["fabrication_risk"]:
            print("EXCELLENT - Ready for sales calls")
        elif analysis["fabrication_risk"]:
            print("⚠️ CAUTION - May contain fabricated information")
        elif not analysis["documentation_based"]:
            print("⚠️ CAUTION - Not clearly based on documentation")
        else:
            print("GOOD - Minor improvements needed")
        
        if analysis["concerns"]:
            print(f"   Issues: {'; '.join(analysis['concerns'])}")
    
    # Overall recommendation
    print(f"\n🎯 RECOMMENDATION:")
    if fabrication_risk == 0 and doc_based >= total * 0.8:
        print("✅ READY FOR PRODUCTION: Responses are accurate and sales-appropriate")
    elif fabrication_risk > 0:
        print("❌ NOT READY: Fabrication risk detected - needs prompt refinement")
    else:
        print("⚠️ NEEDS IMPROVEMENT: Some responses need better documentation grounding")

def main():
    print("🚀 Sales Scenario Testing with V3")
    print("=" * 60)
    
    # Update to V3
    if update_to_v3():
        print("\n⏳ Waiting 5 seconds for changes to propagate...")
        time.sleep(5)
        
        # Test sales scenarios
        results = test_sales_questions()
        
        # Save results
        with open('sales_test_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Detailed results saved to: sales_test_results.json")
        
    else:
        print("❌ Failed to update assistant")

if __name__ == "__main__":
    main()
