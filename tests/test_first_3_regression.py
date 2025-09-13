#!/usr/bin/env python3

"""
Run only the first 3 tests from the regression test suite
Focuses on Source Citation tests (1.1, 1.2, 1.3)
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment
load_dotenv()

# Set mock Slack environment variables before importing to avoid Slack initialization errors
os.environ['SLACK_BOT_TOKEN'] = 'xoxb-test-token-for-testing'
os.environ['SLACK_SIGNING_SECRET'] = 'test-signing-secret-for-testing'

def initialize_pipeline():
    """Initialize the Custom RAG Pipeline"""
    try:
        import openai
        from src.app_custom_rag import CustomRAGPipeline
        
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        vector_store_id = os.getenv('OPENAI_VECTOR_STORE_ID')
        
        with open('assistant_config/MASTER_PROMPT.md', 'r') as f:
            master_prompt = f.read()
        
        return CustomRAGPipeline(client, vector_store_id, master_prompt)
    except Exception as e:
        raise Exception(f"Failed to initialize pipeline: {e}")

def judge_response(response, test_type, criteria, expected_elements=None):
    """
    Use GPT-4o to judge the quality of a response based on specific criteria
    """
    try:
        import openai
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        judge_prompt = f"""
You are evaluating a response from an educational chatbot. Rate the response on a scale of 1-10 and provide detailed feedback.

TEST TYPE: {test_type}
CRITERIA: {criteria}

RESPONSE TO EVALUATE:
{response}

Expected elements (if applicable): {expected_elements or 'None specified'}

Provide your evaluation in the following JSON format:
{{
    "score": <1-10>,
    "passed": <true/false>,
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "explanation": "Detailed explanation of the score"
}}

Scoring Guidelines:
- 8-10: Excellent, meets all criteria
- 6-7: Good, meets most criteria with minor issues
- 4-5: Acceptable, meets basic criteria but has notable issues
- 1-3: Poor, fails to meet important criteria
"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a strict educational content evaluator. Always respond in valid JSON format."},
                {"role": "user", "content": judge_prompt}
            ],
            temperature=0.1
        )
        
        judge_result = response.choices[0].message.content.strip()
        
        # Clean up JSON response
        if judge_result.startswith('```json'):
            judge_result = judge_result.replace('```json', '').replace('```', '').strip()
        
        return json.loads(judge_result)
        
    except Exception as e:
        return {
            "score": 0,
            "passed": False,
            "strengths": [],
            "weaknesses": [f"Judge evaluation failed: {str(e)}"],
            "explanation": f"Error during evaluation: {str(e)}"
        }

def test_source_citation(pipeline):
    """Test 1: Source Citation Accuracy - First 3 tests only"""
    print("\n🧪 TEST 1: SOURCE CITATION (First 3 Tests)")
    print("=" * 50)
    
    test_cases = [
        {
            "query": "What certifications does Ironhack offer for Data Analytics?",
            "expected_source_keywords": ["certification", "data analytics"],
            "description": "Should cite Certifications document"
        },
        {
            "query": "How long is the Web Development Remote bootcamp?",
            "expected_source_keywords": ["web development", "remote"],
            "description": "Should cite Web Dev Remote document"
        },
        {
            "query": "What tools are used in the DevOps bootcamp?",
            "expected_source_keywords": ["devops", "tools"],
            "description": "Should cite DevOps document"
        }
    ]
    
    results = []
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n[Test 1.{i}] {case['description']}")
        print(f"Query: {case['query']}")
        print("-" * 40)
        
        try:
            # Get response from pipeline
            result = pipeline.process_query(case['query'])
            response = result['response']
            sources = result['sources']
            processing_time = result['processing_time']
            
            print(f"📊 Sources: {sources}")
            print(f"⏱️  Time: {processing_time:.2f}s")
            
            # Check if source is cited in response
            has_source_citation = "Sources:" in response
            print(f"📝 Source Citation: {'✅ Present' if has_source_citation else '❌ Missing'}")
            
            # Judge the response
            criteria = f"""
            1. Response should contain factual information about {case['description'].lower()}
            2. Response MUST end with 'Sources:' followed by document references
            3. Source citation should use file names (e.g., "Certifications_2025_07.txt")
            4. No fabricated information should be present
            5. Response should be professional and helpful for sales team
            """
            
            judge_result = judge_response(
                response, 
                "Source Citation", 
                criteria,
                case['expected_source_keywords']
            )
            
            test_result = {
                "test": f"1.{i}",
                "query": case['query'],
                "response": response,
                "sources": sources,
                "processing_time": processing_time,
                "has_source_citation": has_source_citation,
                "judge_score": judge_result['score'],
                "judge_passed": judge_result['passed'],
                "judge_feedback": judge_result
            }
            
            results.append(test_result)
            
            print(f"🎯 Judge Score: {judge_result['score']}/10")
            print(f"✅ Passed: {judge_result['passed']}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            results.append({
                "test": f"1.{i}",
                "query": case['query'],
                "error": str(e),
                "judge_score": 0,
                "judge_passed": False
            })
    
    return results

def generate_report(results):
    """Generate test report for the first 3 tests"""
    print("\n" + "=" * 60)
    print("🏆 FIRST 3 REGRESSION TESTS REPORT")
    print("=" * 60)
    
    # Calculate overall statistics
    total_tests = len(results)
    passed_tests = sum(1 for result in results if result.get('judge_passed', False))
    avg_score = sum(result.get('judge_score', 0) for result in results) / total_tests if total_tests > 0 else 0
    avg_time = sum(result.get('processing_time', 0) for result in results if 'processing_time' in result) / total_tests if total_tests > 0 else 0
    
    print(f"📊 OVERALL RESULTS:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
    print(f"   Average Score: {avg_score:.1f}/10")
    print(f"   Average Processing Time: {avg_time:.2f}s")
    
    # Individual test results
    print(f"\n📋 INDIVIDUAL TEST RESULTS:")
    for result in results:
        test_id = result.get('test', 'Unknown')
        query = result.get('query', 'Unknown query')
        score = result.get('judge_score', 0)
        passed = result.get('judge_passed', False)
        time_taken = result.get('processing_time', 0)
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_id}: {status} (Score: {score}/10, Time: {time_taken:.2f}s)")
        print(f"      Query: {query}")
        
        if 'error' in result:
            print(f"      Error: {result['error']}")
        else:
            response_preview = result.get('response', '')[:100] + "..." if len(result.get('response', '')) > 100 else result.get('response', '')
            print(f"      Response: {response_preview}")
        print()
    
    # Quality gates
    print(f"🚦 QUALITY GATES:")
    print(f"   ✅ Passing Rate > 80%: {'PASS' if (passed_tests/total_tests) > 0.8 else 'FAIL'}")
    print(f"   ✅ Average Score > 7.0: {'PASS' if avg_score > 7.0 else 'FAIL'}")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"tests/results/first_3_tests_{timestamp}.json"
    
    os.makedirs("tests/results", exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "pass_rate": passed_tests/total_tests,
                "average_score": avg_score,
                "average_processing_time": avg_time
            },
            "results": results
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    
    return {
        "pass_rate": passed_tests/total_tests,
        "average_score": avg_score,
        "results_file": results_file
    }

def main():
    """Run the first 3 regression tests"""
    print("🚀 FIRST 3 REGRESSION TESTS")
    print("=" * 60)
    print("Testing: Source Citation (Tests 1.1, 1.2, 1.3)")
    print("With automatic judge evaluation for each test case")
    print()
    
    try:
        # Initialize pipeline
        print("🔧 Initializing Custom RAG Pipeline...")
        pipeline = initialize_pipeline()
        print("✅ Pipeline initialized successfully")
        
        # Run first 3 tests
        results = test_source_citation(pipeline)
        
        # Generate report
        report = generate_report(results)
        
        # Exit with appropriate code
        if report['pass_rate'] > 0.8 and report['average_score'] > 7.0:
            print("\n🎉 ALL FIRST 3 TESTS PASSED!")
            return 0
        else:
            print("\n⚠️  SOME TESTS FAILED - Review results")
            return 1
            
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
