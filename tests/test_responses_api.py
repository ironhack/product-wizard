#!/usr/bin/env python3
"""
Test script for Responses API migration
Tests the new Responses API implementation against existing test scenarios
"""

import os
import sys
import openai
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Add the src directory to the path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Load environment variables
load_dotenv()

# Test configuration
TEST_QUESTIONS = [
    {
        "question": "What tools are covered in the DevOps bootcamp?",
        "expected_keywords": ["AWS", "Docker", "Kubernetes", "Terraform", "Ansible"],
        "test_name": "devops_tools_comprehensive"
    },
    {
        "question": "How long is the Web Development bootcamp?",
        "expected_keywords": ["360 hours", "600 hours", "Remote", "Berlin"],
        "test_name": "web_dev_duration_variants"
    },
    {
        "question": "Does the Web Development course include SQL?",
        "expected_keywords": ["Berlin variant", "Remote variant", "Unit 6"],
        "test_name": "web_dev_sql_handling"
    },
    {
        "question": "What programming languages are taught in AI Engineering?",
        "expected_keywords": ["Python"],
        "test_name": "ai_engineering_languages"
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

def test_responses_api():
    """Test the Responses API implementation"""
    
    # Initialize OpenAI client
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    
    # Vector Store ID
    vector_store_id = os.environ.get("OPENAI_VECTOR_STORE_ID", "vs_68c14625e8d88191a27acb8a3845a706")
    
    # Load master prompt
    master_prompt = load_master_prompt()
    
    print("=== RESPONSES API MIGRATION TEST ===")
    print(f"Vector Store ID: {vector_store_id}")
    print(f"Master Prompt Length: {len(master_prompt)} characters")
    print(f"Test Questions: {len(TEST_QUESTIONS)}")
    print("=" * 50)
    
    results = []
    
    for i, test_case in enumerate(TEST_QUESTIONS, 1):
        print(f"\n[Test {i}/{len(TEST_QUESTIONS)}] {test_case['test_name']}")
        print(f"Question: {test_case['question']}")
        
        try:
            # Prepare the Responses API request parameters
            request_params = {
                "model": "gpt-4o",
                "input": test_case['question'],
                "instructions": master_prompt,
                "tools": [
                    {
                        "type": "file_search",
                        "vector_store_ids": [vector_store_id]
                    }
                ]
            }
            
            print("Making Responses API call...")
            start_time = time.time()
            
            # Make the Responses API call
            response = client.responses.create(**request_params)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Extract the assistant's response
            assistant_message = "No response found"
            
            if response.output and len(response.output) > 0:
                # Look for the message output (not tool calls)
                for output_item in response.output:
                    if hasattr(output_item, 'type') and output_item.type == 'message':
                        if hasattr(output_item, 'content') and len(output_item.content) > 0:
                            content = output_item.content[0]
                            if hasattr(content, 'text'):
                                assistant_message = content.text
                                break
            
            print(f"✅ Response received in {response_time:.2f}s")
            print(f"Response length: {len(assistant_message)} characters")
            
            # Check for expected keywords
            found_keywords = []
            missing_keywords = []
            
            for keyword in test_case['expected_keywords']:
                if keyword.lower() in assistant_message.lower():
                    found_keywords.append(keyword)
                else:
                    missing_keywords.append(keyword)
            
            # Evaluate the response
            keyword_score = len(found_keywords) / len(test_case['expected_keywords'])
            
            print(f"Keywords found: {found_keywords}")
            if missing_keywords:
                print(f"Keywords missing: {missing_keywords}")
            print(f"Keyword score: {keyword_score:.2%}")
            
            # Check for proper citations
            has_citations = "curriculum" in assistant_message.lower() or "documentation" in assistant_message.lower()
            citation_score = 1.0 if has_citations else 0.0
            
            print(f"Has proper citations: {'✅' if has_citations else '❌'}")
            
            # Overall score
            overall_score = (keyword_score + citation_score) / 2
            
            # Store result
            test_result = {
                "test_name": test_case['test_name'],
                "question": test_case['question'],
                "response": assistant_message,
                "response_time": response_time,
                "keyword_score": keyword_score,
                "citation_score": citation_score,
                "overall_score": overall_score,
                "found_keywords": found_keywords,
                "missing_keywords": missing_keywords,
                "has_response_id": hasattr(response, 'id'),
                "response_id": getattr(response, 'id', None)
            }
            
            results.append(test_result)
            
            print(f"Overall score: {overall_score:.2%}")
            print(f"Status: {'✅ PASS' if overall_score >= 0.7 else '❌ FAIL'}")
            
            # Show first 200 characters of response
            print(f"Response preview: {assistant_message[:200]}...")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            test_result = {
                "test_name": test_case['test_name'],
                "question": test_case['question'],
                "error": str(e),
                "response_time": 0,
                "keyword_score": 0,
                "citation_score": 0,
                "overall_score": 0
            }
            results.append(test_result)
    
    # Summary
    print("\n" + "=" * 50)
    print("=== TEST SUMMARY ===")
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r.get('overall_score', 0) >= 0.7)
    avg_score = sum(r.get('overall_score', 0) for r in results) / total_tests if total_tests > 0 else 0
    avg_response_time = sum(r.get('response_time', 0) for r in results) / total_tests if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed Tests: {passed_tests}")
    print(f"Pass Rate: {passed_tests/total_tests:.2%}")
    print(f"Average Score: {avg_score:.2%}")
    print(f"Average Response Time: {avg_response_time:.2f}s")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"results/responses_api_test_{timestamp}.json"
    
    os.makedirs("results", exist_ok=True)
    
    final_results = {
        "timestamp": timestamp,
        "api_type": "Responses API",
        "model": "gpt-4o",
        "vector_store_id": vector_store_id,
        "summary": {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "pass_rate": passed_tests/total_tests,
            "average_score": avg_score,
            "average_response_time": avg_response_time
        },
        "test_results": results
    }
    
    with open(results_file, 'w') as f:
        json.dump(final_results, f, indent=2)
    
    print(f"Detailed results saved to: {results_file}")
    
    # Final verdict
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED - Responses API migration ready!")
        return True
    elif passed_tests >= total_tests * 0.8:
        print("⚠️  MOSTLY PASSED - Responses API migration mostly ready, minor issues to fix")
        return True
    else:
        print("❌ TESTS FAILED - Responses API migration needs work")
        return False

if __name__ == "__main__":
    success = test_responses_api()
    sys.exit(0 if success else 1)
