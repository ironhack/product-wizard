#!/usr/bin/env python3

"""
Ambiguity Test Suite for Custom RAG Pipeline

This test suite validates the system's ability to handle ambiguous queries and distinguish between:
1. Data-related courses (Data Analytics, Data Science & ML, AI Engineering, 1-year program)
2. Location-based curriculum differences (Web Dev Remote vs Berlin onsite)

The test ensures the system provides specific, accurate responses without confusion between similar programs.
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

def judge_ambiguity_response(response, test_type, criteria, expected_specificity):
    """
    Use GPT-4o to judge how well the response handles ambiguity and provides specific information
    """
    try:
        import openai
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        judge_prompt = f"""
You are evaluating a response from an educational chatbot for its ability to handle ambiguous queries and provide specific, accurate information.

TEST TYPE: {test_type}
CRITERIA: {criteria}

RESPONSE TO EVALUATE:
{response}

EXPECTED SPECIFICITY: {expected_specificity}

Your task is to evaluate how well the response:
1. CLARITY: Does it clearly distinguish between similar programs/courses?
2. SPECIFICITY: Does it provide specific information about the requested program?
3. ACCURACY: Is the information accurate and not mixed up between programs?
4. COMPLETENESS: Does it address the specific question asked?
5. DISAMBIGUATION: Does it help clarify any potential confusion?

Provide your evaluation in the following JSON format:
{{
    "score": <1-10>,
    "passed": <true/false>,
    "clarity_score": <1-10>,
    "specificity_score": <1-10>,
    "accuracy_score": <1-10>,
    "disambiguation_quality": <1-10>,
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "explanation": "Detailed explanation of the evaluation"
}}

Scoring Guidelines:
- 9-10: Excellent disambiguation, highly specific and accurate
- 7-8: Good disambiguation, mostly specific with minor issues
- 5-6: Adequate disambiguation, some confusion or lack of specificity
- 3-4: Poor disambiguation, significant confusion between programs
- 1-2: Very poor disambiguation, major confusion or inaccuracy
"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a strict educational content evaluator specializing in ambiguity handling. Always respond in valid JSON format."},
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
            "clarity_score": 0,
            "specificity_score": 0,
            "accuracy_score": 0,
            "disambiguation_quality": 0,
            "strengths": [],
            "weaknesses": [f"Judge evaluation failed: {str(e)}"],
            "explanation": f"Error during evaluation: {str(e)}"
        }

def test_data_course_ambiguity(pipeline):
    """Test 1: Data-related Course Ambiguity"""
    print("\n🧪 TEST 1: DATA COURSE AMBIGUITY")
    print("=" * 50)
    
    test_cases = [
        {
            "query": "What is the difference between Data Analytics and Data Science bootcamps?",
            "description": "Should clearly distinguish between Data Analytics and Data Science programs",
            "expected_specificity": "Should mention duration differences (360h vs 400h), curriculum focus, and specific technologies",
            "criteria": "Must clearly distinguish between Data Analytics (360h) and Data Science & ML (400h) programs, highlighting key differences in curriculum and focus"
        },
        {
            "query": "Does the Data Analytics course cover machine learning?",
            "description": "Should be specific about Data Analytics ML coverage without confusing with Data Science",
            "expected_specificity": "Should mention Data Analytics includes basic ML (40 hours) but is different from the comprehensive Data Science program",
            "criteria": "Must be specific to Data Analytics program and mention its ML unit (40 hours) without confusing with the more comprehensive Data Science program"
        },
        {
            "query": "What's the difference between AI Engineering and Data Science programs?",
            "description": "Should clearly distinguish between AI Engineering and Data Science programs",
            "expected_specificity": "Should highlight AI Engineering focuses on AI applications and deployment, while Data Science focuses on data analysis and ML",
            "criteria": "Must clearly distinguish between AI Engineering (AI applications, deployment) and Data Science (data analysis, ML) programs"
        },
        {
            "query": "How long is the 1-year Data Science program?",
            "description": "Should be specific about the 1-year program duration and distinguish from bootcamps",
            "expected_specificity": "Should mention 1,582 hours over 1 year, distinguishing from 400-hour bootcamp",
            "criteria": "Must be specific about the 1-year program (1,582 hours) and distinguish it from the 400-hour Data Science bootcamp"
        },
        {
            "query": "Which program is better for someone wanting to work with AI models?",
            "description": "Should distinguish between AI Engineering and Data Science programs for AI work",
            "expected_specificity": "Should recommend AI Engineering for AI model work, explaining the difference from Data Science",
            "criteria": "Must recommend AI Engineering for AI model work and explain why it's better suited than Data Science for this specific goal"
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
            
            # Judge the response for ambiguity handling
            judge_result = judge_ambiguity_response(
                response,
                "Data Course Ambiguity",
                case['criteria'],
                case['expected_specificity']
            )
            
            test_result = {
                "test": f"1.{i}",
                "query": case['query'],
                "response": response,
                "sources": sources,
                "processing_time": processing_time,
                "clarity_score": judge_result['clarity_score'],
                "specificity_score": judge_result['specificity_score'],
                "accuracy_score": judge_result['accuracy_score'],
                "disambiguation_quality": judge_result['disambiguation_quality'],
                "judge_score": judge_result['score'],
                "judge_passed": judge_result['passed'],
                "judge_feedback": judge_result
            }
            
            results.append(test_result)
            
            print(f"🎯 Judge Score: {judge_result['score']}/10")
            print(f"📊 Clarity: {judge_result['clarity_score']}/10")
            print(f"🎯 Specificity: {judge_result['specificity_score']}/10")
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

def test_location_curriculum_ambiguity(pipeline):
    """Test 2: Location-based Curriculum Ambiguity"""
    print("\n🧪 TEST 2: LOCATION CURRICULUM AMBIGUITY")
    print("=" * 50)
    
    test_cases = [
        {
            "query": "Does Web Development cover SQL?",
            "description": "Should distinguish between Remote (no SQL) and Berlin onsite (includes SQL) programs",
            "expected_specificity": "Should clarify that Remote doesn't include SQL, but Berlin onsite does",
            "criteria": "Must distinguish between Web Dev Remote (no SQL) and Berlin onsite (includes SQL in Unit 6)"
        },
        {
            "query": "What's the difference between Web Development Remote and Berlin programs?",
            "description": "Should clearly explain the differences between Remote and Berlin onsite programs",
            "expected_specificity": "Should mention duration (360h vs 600h), technologies (SQL, TypeScript, Next.js in Berlin), and format differences",
            "criteria": "Must clearly distinguish duration (360h vs 600h), technologies (SQL, TypeScript, Next.js in Berlin), and format (remote vs onsite)"
        },
        {
            "query": "How long is the Web Development bootcamp?",
            "description": "Should clarify there are two different durations for Remote vs Berlin",
            "expected_specificity": "Should mention both durations: 360h for Remote, 600h for Berlin onsite",
            "criteria": "Must mention both durations: 360 hours for Remote, 600 hours for Berlin onsite"
        },
        {
            "query": "Does Web Development include TypeScript?",
            "description": "Should distinguish between Remote (no TypeScript) and Berlin (includes TypeScript)",
            "expected_specificity": "Should clarify that TypeScript is only in Berlin onsite program, not in Remote",
            "criteria": "Must clarify that TypeScript is only in Berlin onsite program (Unit 6), not in Remote program"
        },
        {
            "query": "What technologies are covered in Web Development?",
            "description": "Should specify which program (Remote vs Berlin) or mention both have different tech stacks",
            "expected_specificity": "Should either specify which program or clearly explain the different tech stacks for each",
            "criteria": "Must either specify which program or clearly explain different tech stacks: Remote (HTML, CSS, JS, React, Node.js, MongoDB) vs Berlin (all Remote tech + SQL, TypeScript, Next.js, PostgreSQL, Prisma)"
        }
    ]
    
    results = []
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n[Test 2.{i}] {case['description']}")
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
            
            # Judge the response for ambiguity handling
            judge_result = judge_ambiguity_response(
                response,
                "Location Curriculum Ambiguity",
                case['criteria'],
                case['expected_specificity']
            )
            
            test_result = {
                "test": f"2.{i}",
                "query": case['query'],
                "response": response,
                "sources": sources,
                "processing_time": processing_time,
                "clarity_score": judge_result['clarity_score'],
                "specificity_score": judge_result['specificity_score'],
                "accuracy_score": judge_result['accuracy_score'],
                "disambiguation_quality": judge_result['disambiguation_quality'],
                "judge_score": judge_result['score'],
                "judge_passed": judge_result['passed'],
                "judge_feedback": judge_result
            }
            
            results.append(test_result)
            
            print(f"🎯 Judge Score: {judge_result['score']}/10")
            print(f"📊 Clarity: {judge_result['clarity_score']}/10")
            print(f"🎯 Specificity: {judge_result['specificity_score']}/10")
            print(f"✅ Passed: {judge_result['passed']}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            results.append({
                "test": f"2.{i}",
                "query": case['query'],
                "error": str(e),
                "judge_score": 0,
                "judge_passed": False
            })
    
    return results

def test_cross_program_ambiguity(pipeline):
    """Test 3: Cross-Program Ambiguity (mixing different program types)"""
    print("\n🧪 TEST 3: CROSS-PROGRAM AMBIGUITY")
    print("=" * 50)
    
    test_cases = [
        {
            "query": "What's the difference between the Data Science bootcamp and the 1-year Data Science program?",
            "description": "Should clearly distinguish between bootcamp (400h) and 1-year program (1,582h)",
            "expected_specificity": "Should highlight duration, depth, and scope differences between bootcamp and 1-year program",
            "criteria": "Must clearly distinguish between Data Science bootcamp (400h) and 1-year program (1,582h), highlighting duration, depth, and scope differences"
        },
        {
            "query": "Which program covers both data analysis and AI?",
            "description": "Should distinguish between programs that cover both areas vs those that focus on one",
            "expected_specificity": "Should mention AI Engineering covers AI, Data Science covers data analysis, and 1-year program covers both",
            "criteria": "Must distinguish between programs: AI Engineering (AI focus), Data Science (data analysis focus), and 1-year program (comprehensive coverage of both)"
        },
        {
            "query": "What's the shortest program for learning data skills?",
            "description": "Should identify the shortest data-related program without confusion",
            "expected_specificity": "Should identify Data Analytics Remote (360h) as shortest, distinguishing from other data programs",
            "criteria": "Must identify Data Analytics Remote (360h) as the shortest data program, distinguishing from Data Science (400h) and 1-year program (1,582h)"
        },
        {
            "query": "Do any programs cover both web development and data science?",
            "description": "Should clarify that these are separate program tracks",
            "expected_specificity": "Should clarify these are separate tracks, but mention 1-year program covers data science comprehensively",
            "criteria": "Must clarify that Web Development and Data Science are separate tracks, but mention 1-year program covers data science comprehensively"
        }
    ]
    
    results = []
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n[Test 3.{i}] {case['description']}")
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
            
            # Judge the response for ambiguity handling
            judge_result = judge_ambiguity_response(
                response,
                "Cross-Program Ambiguity",
                case['criteria'],
                case['expected_specificity']
            )
            
            test_result = {
                "test": f"3.{i}",
                "query": case['query'],
                "response": response,
                "sources": sources,
                "processing_time": processing_time,
                "clarity_score": judge_result['clarity_score'],
                "specificity_score": judge_result['specificity_score'],
                "accuracy_score": judge_result['accuracy_score'],
                "disambiguation_quality": judge_result['disambiguation_quality'],
                "judge_score": judge_result['score'],
                "judge_passed": judge_result['passed'],
                "judge_feedback": judge_result
            }
            
            results.append(test_result)
            
            print(f"🎯 Judge Score: {judge_result['score']}/10")
            print(f"📊 Clarity: {judge_result['clarity_score']}/10")
            print(f"🎯 Specificity: {judge_result['specificity_score']}/10")
            print(f"✅ Passed: {judge_result['passed']}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            results.append({
                "test": f"3.{i}",
                "query": case['query'],
                "error": str(e),
                "judge_score": 0,
                "judge_passed": False
            })
    
    return results

def generate_report(all_results):
    """Generate comprehensive ambiguity test report"""
    print("\n" + "=" * 60)
    print("🏆 AMBIGUITY TEST REPORT")
    print("=" * 60)
    
    # Calculate overall statistics
    total_tests = len(all_results)
    passed_tests = sum(1 for result in all_results if result.get('judge_passed', False))
    avg_score = sum(result.get('judge_score', 0) for result in all_results) / total_tests if total_tests > 0 else 0
    avg_clarity = sum(result.get('clarity_score', 0) for result in all_results) / total_tests if total_tests > 0 else 0
    avg_specificity = sum(result.get('specificity_score', 0) for result in all_results) / total_tests if total_tests > 0 else 0
    avg_disambiguation = sum(result.get('disambiguation_quality', 0) for result in all_results) / total_tests if total_tests > 0 else 0
    avg_time = sum(result.get('processing_time', 0) for result in all_results if 'processing_time' in result) / total_tests if total_tests > 0 else 0
    
    print(f"📊 OVERALL RESULTS:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
    print(f"   Average Score: {avg_score:.1f}/10")
    print(f"   Average Clarity: {avg_clarity:.1f}/10")
    print(f"   Average Specificity: {avg_specificity:.1f}/10")
    print(f"   Average Disambiguation: {avg_disambiguation:.1f}/10")
    print(f"   Average Processing Time: {avg_time:.2f}s")
    
    # Test category breakdown
    categories = {
        "Data Course Ambiguity": [r for r in all_results if r.get('test', '').startswith('1.')],
        "Location Curriculum Ambiguity": [r for r in all_results if r.get('test', '').startswith('2.')],
        "Cross-Program Ambiguity": [r for r in all_results if r.get('test', '').startswith('3.')]
    }
    
    print(f"\n📋 CATEGORY BREAKDOWN:")
    for category, results in categories.items():
        if results:
            category_passed = sum(1 for r in results if r.get('judge_passed', False))
            category_avg = sum(r.get('judge_score', 0) for r in results) / len(results)
            category_clarity = sum(r.get('clarity_score', 0) for r in results) / len(results)
            category_specificity = sum(r.get('specificity_score', 0) for r in results) / len(results)
            print(f"   {category}:")
            print(f"     Passed: {category_passed}/{len(results)} ({category_passed/len(results)*100:.1f}%)")
            print(f"     Avg Score: {category_avg:.1f}/10")
            print(f"     Avg Clarity: {category_clarity:.1f}/10")
            print(f"     Avg Specificity: {category_specificity:.1f}/10")
    
    # Quality gates
    print(f"\n🚦 QUALITY GATES:")
    print(f"   ✅ Passing Rate > 80%: {'PASS' if (passed_tests/total_tests) > 0.8 else 'FAIL'}")
    print(f"   ✅ Average Score > 7.0: {'PASS' if avg_score > 7.0 else 'FAIL'}")
    print(f"   ✅ Average Clarity > 7.0: {'PASS' if avg_clarity > 7.0 else 'FAIL'}")
    print(f"   ✅ Average Specificity > 7.0: {'PASS' if avg_specificity > 7.0 else 'FAIL'}")
    print(f"   ✅ Average Disambiguation > 7.0: {'PASS' if avg_disambiguation > 7.0 else 'FAIL'}")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"tests/results/ambiguity_test_{timestamp}.json"
    
    os.makedirs("tests/results", exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "pass_rate": passed_tests/total_tests,
                "average_score": avg_score,
                "average_clarity": avg_clarity,
                "average_specificity": avg_specificity,
                "average_disambiguation": avg_disambiguation,
                "average_processing_time": avg_time
            },
            "categories": {name: len(results) for name, results in categories.items()},
            "results": all_results
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    
    return {
        "pass_rate": passed_tests/total_tests,
        "average_score": avg_score,
        "average_clarity": avg_clarity,
        "average_specificity": avg_specificity,
        "average_disambiguation": avg_disambiguation,
        "results_file": results_file
    }

def main():
    """Run the complete ambiguity test suite"""
    print("🚀 CUSTOM RAG AMBIGUITY TEST SUITE")
    print("=" * 60)
    print("Testing: Data Course Ambiguity, Location Curriculum Ambiguity, Cross-Program Ambiguity")
    print("With automatic judge evaluation for each test case")
    print()
    
    try:
        # Initialize pipeline
        print("🔧 Initializing Custom RAG Pipeline...")
        pipeline = initialize_pipeline()
        print("✅ Pipeline initialized successfully")
        
        # Run all tests
        all_results = []
        
        # Test 1: Data Course Ambiguity
        data_results = test_data_course_ambiguity(pipeline)
        all_results.extend(data_results)
        
        # Test 2: Location Curriculum Ambiguity
        location_results = test_location_curriculum_ambiguity(pipeline)
        all_results.extend(location_results)
        
        # Test 3: Cross-Program Ambiguity
        cross_results = test_cross_program_ambiguity(pipeline)
        all_results.extend(cross_results)
        
        # Generate report
        report = generate_report(all_results)
        
        # Exit with appropriate code
        if (report['pass_rate'] > 0.8 and 
            report['average_score'] > 7.0 and 
            report['average_clarity'] > 7.0 and 
            report['average_specificity'] > 7.0 and 
            report['average_disambiguation'] > 7.0):
            print("\n🎉 ALL AMBIGUITY TESTS PASSED - System handles ambiguity well!")
            return 0
        else:
            print("\n⚠️  SOME AMBIGUITY TESTS FAILED - Review results for improvement")
            return 1
            
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
