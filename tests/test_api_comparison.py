#!/usr/bin/env python3
"""
Side-by-side comparison test between Assistants API and Responses API
Tests the same questions with both APIs to compare performance, accuracy, and response quality
"""

import os
import sys
import openai
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test questions for comparison
COMPARISON_TESTS = [
    {
        "question": "What tools are covered in the DevOps bootcamp?",
        "expected_keywords": ["AWS", "Docker", "Kubernetes", "Terraform", "Ansible"],
        "test_name": "devops_tools"
    },
    {
        "question": "How long is the Web Development bootcamp?",
        "expected_keywords": ["360 hours", "600 hours", "Remote", "Berlin"],
        "test_name": "web_dev_duration"
    },
    {
        "question": "Does the Web Development course include SQL?",
        "expected_keywords": ["Berlin variant", "Remote variant", "Unit 6"],
        "test_name": "web_dev_sql"
    }
]

def load_master_prompt():
    """Load the master prompt from the assistant config"""
    try:
        with open('../assistant_config/MASTER_PROMPT.md', 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading master prompt: {e}")
        return "You are a helpful assistant for Ironhack course information."

def test_assistants_api(question, test_name):
    """Test using the original Assistants API"""
    try:
        client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        assistant_id = os.environ["OPENAI_ASSISTANT_ID"]
        
        print(f"    🔄 Testing Assistants API...")
        start_time = time.time()
        
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
            assistant_id=assistant_id
        )
        
        # Wait for completion
        while run.status == "queued" or run.status == "in_progress":
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            time.sleep(0.5)
        
        # Get response
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        assistant_message = messages.data[0].content[0].text.value
        
        end_time = time.time()
        response_time = end_time - start_time
        
        return {
            "api_type": "Assistants API",
            "success": True,
            "response": assistant_message,
            "response_time": response_time,
            "thread_id": thread.id,
            "run_id": run.id
        }
        
    except Exception as e:
        return {
            "api_type": "Assistants API",
            "success": False,
            "error": str(e),
            "response_time": 0
        }

def test_responses_api(question, test_name):
    """Test using the new Responses API"""
    try:
        client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        vector_store_id = os.environ.get("OPENAI_VECTOR_STORE_ID", "vs_68c14625e8d88191a27acb8a3845a706")
        master_prompt = load_master_prompt()
        
        print(f"    🔄 Testing Responses API...")
        start_time = time.time()
        
        # Make Responses API call
        response = client.responses.create(
            model="gpt-4o",
            input=question,
            instructions=master_prompt,
            tools=[{
                "type": "file_search",
                "vector_store_ids": [vector_store_id]
            }]
        )
        
        # Extract response
        assistant_message = "No response found"
        
        if response.output and len(response.output) > 0:
            for output_item in response.output:
                if hasattr(output_item, 'type') and output_item.type == 'message':
                    if hasattr(output_item, 'content') and len(output_item.content) > 0:
                        content = output_item.content[0]
                        if hasattr(content, 'text'):
                            assistant_message = content.text
                            break
        
        end_time = time.time()
        response_time = end_time - start_time
        
        return {
            "api_type": "Responses API",
            "success": True,
            "response": assistant_message,
            "response_time": response_time,
            "response_id": response.id
        }
        
    except Exception as e:
        return {
            "api_type": "Responses API",
            "success": False,
            "error": str(e),
            "response_time": 0
        }

def evaluate_response(response_text, expected_keywords):
    """Evaluate response quality"""
    if not response_text or response_text == "No response found":
        return {
            "keyword_score": 0,
            "citation_score": 0,
            "length": 0,
            "found_keywords": [],
            "missing_keywords": expected_keywords
        }
    
    # Check keywords
    found_keywords = []
    missing_keywords = []
    
    for keyword in expected_keywords:
        if keyword.lower() in response_text.lower():
            found_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)
    
    keyword_score = len(found_keywords) / len(expected_keywords) if expected_keywords else 0
    
    # Check citations
    has_citations = ("curriculum" in response_text.lower() or 
                    "documentation" in response_text.lower() or
                    "bootcamp" in response_text.lower())
    citation_score = 1.0 if has_citations else 0.0
    
    return {
        "keyword_score": keyword_score,
        "citation_score": citation_score,
        "length": len(response_text),
        "found_keywords": found_keywords,
        "missing_keywords": missing_keywords
    }

def run_api_comparison():
    """Run side-by-side API comparison"""
    
    print("=== API COMPARISON TEST SUITE ===")
    print("Comparing Assistants API vs Responses API")
    print(f"Total Tests: {len(COMPARISON_TESTS)}")
    print("=" * 50)
    
    all_results = []
    
    for i, test_case in enumerate(COMPARISON_TESTS, 1):
        print(f"\n📋 TEST {i}/{len(COMPARISON_TESTS)}: {test_case['test_name']}")
        print(f"Question: {test_case['question']}")
        print("-" * 40)
        
        # Test both APIs
        assistants_result = test_assistants_api(test_case['question'], test_case['test_name'])
        responses_result = test_responses_api(test_case['question'], test_case['test_name'])
        
        # Evaluate responses
        if assistants_result['success']:
            assistants_eval = evaluate_response(assistants_result['response'], test_case['expected_keywords'])
            assistants_result.update(assistants_eval)
            print(f"    ✅ Assistants API: {assistants_result['response_time']:.2f}s, Score: {(assistants_eval['keyword_score'] + assistants_eval['citation_score'])/2:.2%}")
        else:
            print(f"    ❌ Assistants API: FAILED - {assistants_result.get('error', 'Unknown error')}")
        
        if responses_result['success']:
            responses_eval = evaluate_response(responses_result['response'], test_case['expected_keywords'])
            responses_result.update(responses_eval)
            print(f"    ✅ Responses API: {responses_result['response_time']:.2f}s, Score: {(responses_eval['keyword_score'] + responses_eval['citation_score'])/2:.2%}")
        else:
            print(f"    ❌ Responses API: FAILED - {responses_result.get('error', 'Unknown error')}")
        
        # Store combined result
        test_result = {
            "test_name": test_case['test_name'],
            "question": test_case['question'],
            "expected_keywords": test_case['expected_keywords'],
            "assistants_api": assistants_result,
            "responses_api": responses_result
        }
        
        all_results.append(test_result)
        
        # Show brief comparison
        if assistants_result['success'] and responses_result['success']:
            time_diff = responses_result['response_time'] - assistants_result['response_time']
            time_comparison = f"{'🏃‍♂️ Responses faster' if time_diff < 0 else '🐌 Assistants faster'} by {abs(time_diff):.2f}s"
            print(f"    ⏱️  {time_comparison}")
            
            length_diff = responses_result['length'] - assistants_result['length'] 
            length_comparison = f"{'📝 Responses longer' if length_diff > 0 else '📝 Assistants longer'} by {abs(length_diff)} chars"
            print(f"    📏 {length_comparison}")
    
    # Overall Summary
    print("\n" + "=" * 50)
    print("=== OVERALL COMPARISON SUMMARY ===")
    
    # Calculate aggregated stats
    successful_assistants = [r for r in all_results if r['assistants_api']['success']]
    successful_responses = [r for r in all_results if r['responses_api']['success']]
    
    if successful_assistants:
        assistants_avg_time = sum(r['assistants_api']['response_time'] for r in successful_assistants) / len(successful_assistants)
        assistants_avg_score = sum((r['assistants_api']['keyword_score'] + r['assistants_api']['citation_score'])/2 for r in successful_assistants) / len(successful_assistants)
        assistants_avg_length = sum(r['assistants_api']['length'] for r in successful_assistants) / len(successful_assistants)
    else:
        assistants_avg_time = assistants_avg_score = assistants_avg_length = 0
    
    if successful_responses:
        responses_avg_time = sum(r['responses_api']['response_time'] for r in successful_responses) / len(successful_responses)
        responses_avg_score = sum((r['responses_api']['keyword_score'] + r['responses_api']['citation_score'])/2 for r in successful_responses) / len(successful_responses)
        responses_avg_length = sum(r['responses_api']['length'] for r in successful_responses) / len(successful_responses)
    else:
        responses_avg_time = responses_avg_score = responses_avg_length = 0
    
    print(f"\n🤖 ASSISTANTS API:")
    print(f"   Success Rate: {len(successful_assistants)}/{len(all_results)} ({len(successful_assistants)/len(all_results):.1%})")
    print(f"   Avg Response Time: {assistants_avg_time:.2f}s")
    print(f"   Avg Quality Score: {assistants_avg_score:.1%}")
    print(f"   Avg Response Length: {assistants_avg_length:.0f} chars")
    
    print(f"\n⚡ RESPONSES API:")
    print(f"   Success Rate: {len(successful_responses)}/{len(all_results)} ({len(successful_responses)/len(all_results):.1%})")
    print(f"   Avg Response Time: {responses_avg_time:.2f}s")
    print(f"   Avg Quality Score: {responses_avg_score:.1%}")
    print(f"   Avg Response Length: {responses_avg_length:.0f} chars")
    
    # Winner determination
    print(f"\n🏆 COMPARISON RESULTS:")
    if len(successful_responses) > len(successful_assistants):
        print("   🥇 Responses API wins on reliability")
    elif len(successful_assistants) > len(successful_responses):
        print("   🥇 Assistants API wins on reliability")
    else:
        print("   🤝 Both APIs equally reliable")
    
    if responses_avg_time < assistants_avg_time:
        print(f"   ⚡ Responses API is faster by {assistants_avg_time - responses_avg_time:.2f}s")
    elif assistants_avg_time < responses_avg_time:
        print(f"   ⚡ Assistants API is faster by {responses_avg_time - assistants_avg_time:.2f}s")
    else:
        print("   ⚡ Both APIs have similar speed")
    
    if responses_avg_score > assistants_avg_score:
        print(f"   🎯 Responses API has better quality (+{(responses_avg_score - assistants_avg_score)*100:.1f} points)")
    elif assistants_avg_score > responses_avg_score:
        print(f"   🎯 Assistants API has better quality (+{(assistants_avg_score - responses_avg_score)*100:.1f} points)")
    else:
        print("   🎯 Both APIs have similar quality")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"results/api_comparison_{timestamp}.json"
    
    os.makedirs("results", exist_ok=True)
    
    comparison_summary = {
        "timestamp": timestamp,
        "assistants_api_summary": {
            "success_rate": len(successful_assistants)/len(all_results),
            "avg_response_time": assistants_avg_time,
            "avg_quality_score": assistants_avg_score,
            "avg_response_length": assistants_avg_length
        },
        "responses_api_summary": {
            "success_rate": len(successful_responses)/len(all_results),
            "avg_response_time": responses_avg_time,
            "avg_quality_score": responses_avg_score,
            "avg_response_length": responses_avg_length
        },
        "detailed_results": all_results
    }
    
    with open(results_file, 'w') as f:
        json.dump(comparison_summary, f, indent=2)
    
    print(f"\nDetailed comparison saved to: {results_file}")
    
    # Recommendation
    if (len(successful_responses) == len(all_results) and 
        responses_avg_score >= assistants_avg_score * 0.95):  # Within 5% quality
        print(f"\n✅ RECOMMENDATION: Safe to migrate to Responses API")
        print(f"   Both APIs perform well, Responses API is future-proof")
        return True
    else:
        print(f"\n⚠️ RECOMMENDATION: Review results before migration")
        return False

if __name__ == "__main__":
    success = run_api_comparison()
    sys.exit(0 if success else 1)
