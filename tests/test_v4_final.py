#!/usr/bin/env python3
"""
Final test of V4 prompt with zero-tolerance fabrication policy
"""

import openai
import time
import json

# API Configuration
from test_config import OPENAI_API_KEY
ASSISTANT_ID = "asst_Zm6nYxM5dhXKDgwzz3yVgYdy"

def update_to_v4():
    """Update assistant with V4 prompt"""
    print("🚀 Updating Assistant to V4 (Zero Fabrication Policy)...")
    
    try:
        with open('MASTER_PROMPT_V4.md', 'r') as f:
            new_instructions = f.read()
            
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        assistant = client.beta.assistants.update(
            assistant_id=ASSISTANT_ID,
            instructions=new_instructions
        )
        
        print("✅ Assistant updated to V4")
        return True
        
    except Exception as e:
        print(f"❌ Error updating assistant: {e}")
        return False

def test_fabrication_prone_questions():
    """Test questions that previously caused fabrications"""
    
    # Questions that revealed specific fabrication issues
    critical_tests = [
        {
            "question": "Can you give me the full list of tools used in the DevOps bootcamp? grouped into four categories.",
            "fabrication_traps": ["GCP", "Google Cloud Platform", "Jenkins"],
            "expected_accurate": ["AWS", "Azure", "Terraform", "Docker", "Kubernetes", "GitHub Actions", "Prometheus", "Grafana", "Ansible"]
        },
        {
            "question": "How long is the Data Analytics bootcamp?",
            "fabrication_traps": ["9 weeks", "weeks", "Monday to Friday", "9:00-18:00", "CET"],
            "expected_accurate": ["360 hours", "30 hours of prework"]
        },
        {
            "question": "What schedule does the Data Analytics program follow?",
            "fabrication_traps": ["Monday to Friday", "9:00", "18:00", "CET", "weekdays"],
            "should_say_not_available": True
        },
        {
            "question": "Which coding tool is used in UX/UI remote course?",
            "fabrication_traps": ["Visual Studio Code", "Sublime", "Atom", "WebStorm"],
            "expected_accurate": ["Figma"]
        },
        {
            "question": "What certifications are available for AI Engineering students after they finish the bootcamp?",
            "fabrication_traps": ["AWS", "Google Cloud", "Microsoft Azure", "CompTIA", "Coursera"],
            "should_say_not_available": True
        }
    ]
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    results = []
    
    for i, test_case in enumerate(critical_tests, 1):
        print(f"\n{'='*25} Critical Test {i}/5 {'='*25}")
        print(f"🎯 Testing: {test_case['question']}")
        print(f"🚫 Fabrication Traps: {test_case['fabrication_traps']}")
        print("-" * 70)
        
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
                
                # Critical analysis for fabrications
                analysis = analyze_for_fabrications(response, test_case)
                
                result = {
                    "question": test_case["question"],
                    "response": response,
                    "analysis": analysis,
                    "test_case": test_case,
                    "status": "success"
                }
                
                results.append(result)
                
                # Display critical results
                print(f"📝 Response Length: {len(response)} chars")
                
                if analysis["fabrications_found"]:
                    print(f"❌ FABRICATIONS DETECTED: {analysis['fabrications_found']}")
                else:
                    print(f"✅ NO FABRICATIONS DETECTED")
                
                if analysis["accurate_content_found"]:
                    print(f"✅ Accurate Content: {analysis['accurate_content_found']}")
                
                if analysis["says_not_available"]:
                    print(f"✅ Correctly says 'not available'")
                
                # Show response
                print(f"\n📄 Full Response:")
                print("-" * 50)
                print(response)
                print("-" * 50)
                
                # Overall verdict
                if analysis["is_safe_for_sales"]:
                    print(f"🎯 VERDICT: ✅ SAFE FOR SALES CALLS")
                else:
                    print(f"🎯 VERDICT: ❌ NOT SAFE - Contains fabrications or issues")
                
            else:
                print(f"❌ Run failed: {run.status}")
                
            time.sleep(3)  # Rate limiting
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Generate final report
    generate_fabrication_report(results)
    
    return results

def analyze_for_fabrications(response, test_case):
    """Detailed analysis for fabrications and accuracy"""
    analysis = {
        "fabrications_found": [],
        "accurate_content_found": [],
        "says_not_available": False,
        "is_safe_for_sales": False,
        "concerns": []
    }
    
    response_lower = response.lower()
    
    # Check for fabrication traps
    for trap in test_case["fabrication_traps"]:
        if trap.lower() in response_lower:
            analysis["fabrications_found"].append(trap)
    
    # Check for accurate content
    if "expected_accurate" in test_case:
        for accurate_item in test_case["expected_accurate"]:
            if accurate_item.lower() in response_lower:
                analysis["accurate_content_found"].append(accurate_item)
    
    # Check if correctly says not available when it should
    not_available_phrases = [
        "i don't have that specific information",
        "not available in the curriculum documentation",
        "connect you with our admissions team"
    ]
    
    analysis["says_not_available"] = any(phrase in response_lower for phrase in not_available_phrases)
    
    # Check for forbidden fabrication words
    fabrication_indicators = [
        "typically", "usually", "generally", "standard", "common",
        "about", "approximately", "should", "likely", "probably"
    ]
    
    found_indicators = [ind for ind in fabrication_indicators if ind in response_lower]
    if found_indicators:
        analysis["concerns"].append(f"Fabrication indicators: {found_indicators}")
    
    # Determine if safe for sales
    if test_case.get("should_say_not_available"):
        # Should say not available
        analysis["is_safe_for_sales"] = (
            analysis["says_not_available"] and 
            len(analysis["fabrications_found"]) == 0
        )
    else:
        # Should provide accurate information
        analysis["is_safe_for_sales"] = (
            len(analysis["fabrications_found"]) == 0 and
            len(analysis["accurate_content_found"]) > 0
        )
    
    return analysis

def generate_fabrication_report(results):
    """Generate detailed fabrication analysis report"""
    print(f"\n{'='*70}")
    print("🔍 FABRICATION ELIMINATION REPORT - V4 PROMPT")
    print("=" * 70)
    
    total_tests = len(results)
    safe_for_sales = sum(1 for r in results if r["analysis"]["is_safe_for_sales"])
    total_fabrications = sum(len(r["analysis"]["fabrications_found"]) for r in results)
    
    print(f"📊 OVERVIEW:")
    print(f"   Total Critical Tests: {total_tests}")
    print(f"   Safe for Sales: {safe_for_sales}/{total_tests} ({safe_for_sales/total_tests*100:.1f}%)")
    print(f"   Total Fabrications Detected: {total_fabrications}")
    
    # Detailed breakdown
    print(f"\n📋 DETAILED RESULTS:")
    
    for i, result in enumerate(results, 1):
        analysis = result["analysis"]
        test_case = result["test_case"]
        
        print(f"\n{i}. {result['question'][:60]}...")
        
        if analysis["is_safe_for_sales"]:
            print(f"   ✅ SAFE FOR SALES")
        else:
            print(f"   ❌ NOT SAFE FOR SALES")
        
        if analysis["fabrications_found"]:
            print(f"   🚫 Fabrications: {', '.join(analysis['fabrications_found'])}")
        
        if analysis["accurate_content_found"]:
            print(f"   ✅ Accurate items: {', '.join(analysis['accurate_content_found'])}")
        
        if test_case.get("should_say_not_available") and analysis["says_not_available"]:
            print(f"   ✅ Correctly said 'not available'")
        elif test_case.get("should_say_not_available") and not analysis["says_not_available"]:
            print(f"   ❌ Should have said 'not available' but didn't")
        
        if analysis["concerns"]:
            print(f"   ⚠️ Concerns: {'; '.join(analysis['concerns'])}")
    
    # Final verdict
    print(f"\n🎯 FINAL VERDICT:")
    
    if total_fabrications == 0 and safe_for_sales == total_tests:
        print(f"✅ PERFECT SCORE - Ready for Production!")
        print(f"   ✓ Zero fabrications detected")
        print(f"   ✓ All responses safe for sales calls")
        print(f"   ✓ Appropriate handling of unavailable information")
    elif total_fabrications == 0:
        print(f"✅ GOOD - No fabrications but some responses need refinement")
        print(f"   ✓ Zero fabrications detected")
        print(f"   ⚠️ Some responses could be more sales-appropriate")
    else:
        print(f"❌ NEEDS MORE WORK - Still contains fabrications")
        print(f"   ❌ {total_fabrications} fabrications detected")
        print(f"   ❌ Prompt needs further refinement")
    
    # Specific improvements needed
    if total_fabrications > 0:
        all_fabrications = []
        for result in results:
            all_fabrications.extend(result["analysis"]["fabrications_found"])
        
        print(f"\n🔧 SPECIFIC FABRICATIONS TO ADDRESS:")
        for fabrication in set(all_fabrications):
            print(f"   - {fabrication}")

def main():
    print("🎯 V4 Final Test - Zero Fabrication Policy")
    print("=" * 70)
    
    # Update to V4
    if update_to_v4():
        print("\n⏳ Waiting 10 seconds for changes to propagate...")
        time.sleep(10)
        
        # Run critical fabrication tests
        results = test_fabrication_prone_questions()
        
        # Save results
        with open('v4_fabrication_test_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Detailed results saved to: v4_fabrication_test_results.json")
        
    else:
        print("❌ Failed to update assistant")

if __name__ == "__main__":
    main()
