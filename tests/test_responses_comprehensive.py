#!/usr/bin/env python3
"""
Comprehensive test suite for Responses API migration
Tests various scenarios including conversation management, different course types, and edge cases
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
COMPREHENSIVE_TESTS = [
    {
        "category": "Course Tools",
        "tests": [
            {
                "question": "What tools are covered in the DevOps bootcamp?",
                "expected_keywords": ["AWS", "Docker", "Kubernetes", "Terraform", "Ansible", "Prometheus", "Grafana"],
                "test_name": "devops_tools_comprehensive"
            },
            {
                "question": "What programming languages are taught in the Data Science bootcamp?",
                "expected_keywords": ["Python", "SQL"],
                "test_name": "data_science_languages"
            },
            {
                "question": "What design tools are used in the UX/UI course?",
                "expected_keywords": ["Figma", "Adobe"],
                "test_name": "uxui_tools"
            }
        ]
    },
    {
        "category": "Course Duration & Variants",
        "tests": [
            {
                "question": "How long is the Web Development bootcamp?",
                "expected_keywords": ["360 hours", "600 hours", "Remote", "Berlin"],
                "test_name": "web_dev_duration_variants"
            },
            {
                "question": "What's the difference between Remote and Berlin Data Analytics?",
                "expected_keywords": ["Remote", "Berlin", "hours", "variant"],
                "test_name": "data_analytics_variants"
            }
        ]
    },
    {
        "category": "Specific Features",
        "tests": [
            {
                "question": "Does the Web Development course include SQL?",
                "expected_keywords": ["Berlin variant", "Remote variant", "Unit 6"],
                "test_name": "web_dev_sql_handling"
            },
            {
                "question": "Is Machine Learning covered in the Data Science bootcamp?",
                "expected_keywords": ["Machine Learning", "Data Science"],
                "test_name": "data_science_ml"
            }
        ]
    },
    {
        "category": "Edge Cases",
        "tests": [
            {
                "question": "What programming language should I learn for blockchain development?",
                "expected_keywords": ["I don't have that specific information", "curriculum documentation"],
                "test_name": "unknown_topic_handling"
            },
            {
                "question": "How much does the bootcamp cost?",
                "expected_keywords": ["I don't have that specific information", "admissions team"],
                "test_name": "pricing_information"
            }
        ]
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

def test_conversation_continuity():
    """Test conversation continuity with previous_response_id"""
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    vector_store_id = os.environ.get("OPENAI_VECTOR_STORE_ID", "vs_68c14625e8d88191a27acb8a3845a706")
    master_prompt = load_master_prompt()
    
    print("\n🔄 TESTING CONVERSATION CONTINUITY")
    print("=" * 50)
    
    try:
        # First message
        print("Sending first message...")
        response1 = client.responses.create(
            model="gpt-4o",
            input="What tools are covered in DevOps?",
            instructions=master_prompt,
            tools=[{
                "type": "file_search",
                "vector_store_ids": [vector_store_id]
            }]
        )
        
        # Extract first response
        first_message = ""
        for output_item in response1.output:
            if hasattr(output_item, 'type') and output_item.type == 'message':
                if hasattr(output_item, 'content') and len(output_item.content) > 0:
                    first_message = output_item.content[0].text
                    break
        
        print(f"✅ First response received (ID: {response1.id})")
        print(f"Preview: {first_message[:100]}...")
        
        # Second message with context
        print("\nSending follow-up message...")
        response2 = client.responses.create(
            model="gpt-4o",
            input="What about the monitoring tools specifically?",
            instructions=master_prompt,
            previous_response_id=response1.id,
            tools=[{
                "type": "file_search",
                "vector_store_ids": [vector_store_id]
            }]
        )
        
        # Extract second response
        second_message = ""
        for output_item in response2.output:
            if hasattr(output_item, 'type') and output_item.type == 'message':
                if hasattr(output_item, 'content') and len(output_item.content) > 0:
                    second_message = output_item.content[0].text
                    break
        
        print(f"✅ Follow-up response received (ID: {response2.id})")
        print(f"Preview: {second_message[:100]}...")
        
        # Check if the follow-up response is contextually relevant
        monitoring_keywords = ["Prometheus", "Grafana", "monitoring", "observability"]
        found_monitoring = any(keyword.lower() in second_message.lower() for keyword in monitoring_keywords)
        
        print(f"Context awareness: {'✅ PASS' if found_monitoring else '❌ FAIL'}")
        return found_monitoring
        
    except Exception as e:
        print(f"❌ Conversation continuity test failed: {e}")
        return False

def run_comprehensive_tests():
    """Run the comprehensive test suite"""
    
    # Initialize OpenAI client
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    
    # Vector Store ID
    vector_store_id = os.environ.get("OPENAI_VECTOR_STORE_ID", "vs_68c14625e8d88191a27acb8a3845a706")
    
    # Load master prompt
    master_prompt = load_master_prompt()
    
    print("=== COMPREHENSIVE RESPONSES API TEST SUITE ===")
    print(f"Vector Store ID: {vector_store_id}")
    print(f"Master Prompt Length: {len(master_prompt)} characters")
    
    # Calculate total tests
    total_tests = sum(len(category["tests"]) for category in COMPREHENSIVE_TESTS)
    print(f"Total Tests: {total_tests}")
    print("=" * 50)
    
    all_results = []
    category_results = {}
    
    for category_info in COMPREHENSIVE_TESTS:
        category_name = category_info["category"]
        category_tests = category_info["tests"]
        
        print(f"\n📁 CATEGORY: {category_name}")
        print("-" * 30)
        
        category_results[category_name] = []
        
        for i, test_case in enumerate(category_tests, 1):
            print(f"\n[{category_name} {i}/{len(category_tests)}] {test_case['test_name']}")
            print(f"Question: {test_case['question']}")
            
            try:
                # Prepare the Responses API request
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
                has_citations = ("curriculum" in assistant_message.lower() or 
                               "documentation" in assistant_message.lower() or
                               "bootcamp" in assistant_message.lower())
                citation_score = 1.0 if has_citations else 0.0
                
                print(f"Has proper citations: {'✅' if has_citations else '❌'}")
                
                # Overall score
                overall_score = (keyword_score + citation_score) / 2
                
                # Store result
                test_result = {
                    "category": category_name,
                    "test_name": test_case['test_name'],
                    "question": test_case['question'],
                    "response": assistant_message,
                    "response_time": response_time,
                    "keyword_score": keyword_score,
                    "citation_score": citation_score,
                    "overall_score": overall_score,
                    "found_keywords": found_keywords,
                    "missing_keywords": missing_keywords,
                    "response_id": response.id
                }
                
                all_results.append(test_result)
                category_results[category_name].append(test_result)
                
                print(f"Overall score: {overall_score:.2%}")
                print(f"Status: {'✅ PASS' if overall_score >= 0.7 else '❌ FAIL'}")
                
                # Show first 150 characters of response
                print(f"Response preview: {assistant_message[:150]}...")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                test_result = {
                    "category": category_name,
                    "test_name": test_case['test_name'],
                    "question": test_case['question'],
                    "error": str(e),
                    "response_time": 0,
                    "keyword_score": 0,
                    "citation_score": 0,
                    "overall_score": 0
                }
                all_results.append(test_result)
                category_results[category_name].append(test_result)
    
    # Test conversation continuity
    conversation_test_passed = test_conversation_continuity()
    
    # Summary by category
    print("\n" + "=" * 50)
    print("=== CATEGORY SUMMARY ===")
    
    for category_name, results in category_results.items():
        if not results:
            continue
            
        category_passed = sum(1 for r in results if r.get('overall_score', 0) >= 0.7)
        category_total = len(results)
        category_avg_score = sum(r.get('overall_score', 0) for r in results) / category_total
        category_avg_time = sum(r.get('response_time', 0) for r in results) / category_total
        
        print(f"\n📁 {category_name}:")
        print(f"   Tests: {category_passed}/{category_total} passed ({category_passed/category_total:.1%})")
        print(f"   Avg Score: {category_avg_score:.1%}")
        print(f"   Avg Time: {category_avg_time:.2f}s")
    
    # Overall Summary
    print("\n" + "=" * 50)
    print("=== OVERALL SUMMARY ===")
    
    total_tests = len(all_results)
    passed_tests = sum(1 for r in all_results if r.get('overall_score', 0) >= 0.7)
    avg_score = sum(r.get('overall_score', 0) for r in all_results) / total_tests if total_tests > 0 else 0
    avg_response_time = sum(r.get('response_time', 0) for r in all_results) / total_tests if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed Tests: {passed_tests}")
    print(f"Pass Rate: {passed_tests/total_tests:.2%}")
    print(f"Average Score: {avg_score:.2%}")
    print(f"Average Response Time: {avg_response_time:.2f}s")
    print(f"Conversation Continuity: {'✅ PASS' if conversation_test_passed else '❌ FAIL'}")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"results/comprehensive_responses_test_{timestamp}.json"
    
    os.makedirs("results", exist_ok=True)
    
    final_results = {
        "timestamp": timestamp,
        "api_type": "Responses API",
        "model": "gpt-4o",
        "vector_store_id": vector_store_id,
        "conversation_continuity_passed": conversation_test_passed,
        "summary": {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "pass_rate": passed_tests/total_tests,
            "average_score": avg_score,
            "average_response_time": avg_response_time
        },
        "category_results": category_results,
        "all_test_results": all_results
    }
    
    with open(results_file, 'w') as f:
        json.dump(final_results, f, indent=2)
    
    print(f"\nDetailed results saved to: {results_file}")
    
    # Final verdict
    overall_success = (passed_tests >= total_tests * 0.8 and conversation_test_passed)
    
    if overall_success:
        print("\n🎉 COMPREHENSIVE TESTS PASSED - Responses API ready for deployment!")
        return True
    else:
        print("\n⚠️ SOME TESTS FAILED - Review results before deployment")
        return False

if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
