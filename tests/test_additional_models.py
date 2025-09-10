#!/usr/bin/env python3
"""
Test additional models that are compatible with Assistants API
"""

import openai
import time
import json

# API Configuration
from test_config import OPENAI_API_KEY
ASSISTANT_ID = "asst_Zm6nYxM5dhXKDgwzz3yVgYdy"

def test_specific_models():
    """Test specific models that might be better for our use case"""
    
    # Models to test that should be compatible with Assistants API
    models_to_test = [
        "gpt-4o",
        "gpt-4o-2024-11-20",  # Latest gpt-4o
        "gpt-4.1-2025-04-14",  # Specific gpt-4.1 version
        "gpt-4-0125-preview",  # Latest gpt-4 preview
        "gpt-4o-mini"  # Smaller but potentially more focused
    ]
    
    print("🧪 Testing Additional Models for Fabrication Resistance")
    print("=" * 60)
    
    # Load V4 prompt
    try:
        with open('MASTER_PROMPT_V4.md', 'r') as f:
            v4_prompt = f.read()
    except:
        print("❌ Could not load V4 prompt")
        return
    
    # Test questions - including the problematic Data Analytics one
    test_questions = [
        {
            "question": "Can you give me the full list of tools used in the DevOps bootcamp? grouped into four categories.",
            "name": "DevOps Tools",
            "fabrication_traps": ["gcp", "google cloud platform", "jenkins"]
        },
        {
            "question": "How long is the Data Analytics bootcamp?",
            "name": "Data Analytics Duration", 
            "fabrication_traps": ["9 weeks", "weeks", "monday", "friday", "cet"]
        }
    ]
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    results = []
    
    for model in models_to_test:
        print(f"\n🔬 Testing: {model}")
        print("-" * 40)
        
        try:
            # Update assistant to this model
            assistant = client.beta.assistants.update(
                assistant_id=ASSISTANT_ID,
                model=model,
                instructions=v4_prompt
            )
            
            print(f"✅ Updated assistant to {model}")
            time.sleep(3)
            
            model_results = {"model": model, "tests": []}
            
            # Test each question
            for test_case in test_questions:
                print(f"\n  📝 Testing: {test_case['name']}")
                
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
                    
                    # Wait for completion
                    start_time = time.time()
                    while run.status in ["queued", "in_progress"]:
                        if time.time() - start_time > 60:
                            print(f"    ⏰ Timeout")
                            break
                        time.sleep(2)
                        run = client.beta.threads.runs.retrieve(
                            thread_id=thread.id,
                            run_id=run.id
                        )
                    
                    if run.status == "completed":
                        messages = client.beta.threads.messages.list(thread_id=thread.id)
                        response = messages.data[0].content[0].text.value
                        
                        # Check for fabrications
                        fabrications = []
                        response_lower = response.lower()
                        
                        for trap in test_case["fabrication_traps"]:
                            if trap in response_lower:
                                fabrications.append(trap)
                        
                        # Check for "not available" (good)
                        says_not_available = "not available" in response_lower
                        
                        test_result = {
                            "question": test_case["name"],
                            "response_length": len(response),
                            "fabrications": fabrications,
                            "says_not_available": says_not_available,
                            "response_preview": response[:200] + "..." if len(response) > 200 else response
                        }
                        
                        model_results["tests"].append(test_result)
                        
                        print(f"    ✅ Response: {len(response)} chars")
                        if fabrications:
                            print(f"    ❌ Fabrications: {fabrications}")
                        else:
                            print(f"    ✅ No fabrications detected")
                        
                        if says_not_available:
                            print(f"    ✅ Says 'not available' appropriately")
                    
                    else:
                        print(f"    ❌ Run failed: {run.status}")
                    
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"    ❌ Error: {e}")
            
            results.append(model_results)
            
        except Exception as e:
            print(f"❌ Failed to test {model}: {e}")
        
        print(f"\n⏳ Waiting before next model...")
        time.sleep(5)
    
    # Generate report
    generate_detailed_report(results)
    
    # Save results
    with open('additional_models_test.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return results

def generate_detailed_report(results):
    """Generate detailed comparison report"""
    print(f"\n{'='*60}")
    print("📊 DETAILED MODEL COMPARISON REPORT")
    print("=" * 60)
    
    if not results:
        print("❌ No results to compare")
        return
    
    # Calculate scores for each model
    model_scores = []
    
    for model_result in results:
        model = model_result["model"]
        total_fabrications = 0
        total_tests = len(model_result["tests"])
        
        for test in model_result["tests"]:
            total_fabrications += len(test["fabrications"])
        
        fabrication_rate = total_fabrications / total_tests if total_tests > 0 else 0
        
        model_scores.append({
            "model": model,
            "total_fabrications": total_fabrications,
            "fabrication_rate": fabrication_rate,
            "total_tests": total_tests,
            "details": model_result["tests"]
        })
    
    # Sort by fabrication rate (lower is better)
    model_scores.sort(key=lambda x: x["fabrication_rate"])
    
    print(f"🏆 RANKING (Best to Worst):")
    print()
    
    for i, score in enumerate(model_scores, 1):
        model = score["model"]
        fabrications = score["total_fabrications"]
        rate = score["fabrication_rate"]
        
        print(f"{i}. {model}")
        print(f"   📊 Total Fabrications: {fabrications}")
        print(f"   📈 Fabrication Rate: {rate:.2f} per test")
        
        # Show details for each test
        for test in score["details"]:
            status = "✅" if len(test["fabrications"]) == 0 else "❌"
            print(f"   {status} {test['question']}: {len(test['fabrications'])} fabrications")
            if test["fabrications"]:
                print(f"      Fabrications: {test['fabrications']}")
        
        print()
    
    # Final recommendation
    best_model = model_scores[0]
    print(f"🎯 FINAL RECOMMENDATION:")
    print(f"   Best Model: {best_model['model']}")
    print(f"   Total Fabrications: {best_model['total_fabrications']}")
    
    if best_model['total_fabrications'] == 0:
        print(f"   🎉 PERFECT: Zero fabrications across all tests!")
    elif best_model['total_fabrications'] <= 2:
        print(f"   ✅ EXCELLENT: Minimal fabrications")
    else:
        print(f"   ⚠️ GOOD: Some fabrications detected, but best available")
    
    print(f"\n📈 PERFORMANCE COMPARISON:")
    print(f"   Best performing: {model_scores[0]['model']} ({model_scores[0]['total_fabrications']} fabrications)")
    print(f"   Worst performing: {model_scores[-1]['model']} ({model_scores[-1]['total_fabrications']} fabrications)")

def main():
    print("🔬 Additional Models Fabrication Test")
    print("=" * 40)
    
    results = test_specific_models()
    
    if results:
        print(f"\n💾 Results saved to: additional_models_test.json")
    
    print(f"\n✅ Testing complete!")

if __name__ == "__main__":
    main()
