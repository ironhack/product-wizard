#!/usr/bin/env python3

"""
Master Test for LangGraph RAG Pipeline

Features:
1. Select specific tests to run (source_citation, conversation_context, fabrication_detection, completeness, manual)
2. Manual question test for ad-hoc queries
3. Detailed response analysis with timing
4. Enhanced judge feedback

Usage:
    python tests/flexible_regression_test.py --tests source_citation manual
    python tests/flexible_regression_test.py --tests all
    python tests/flexible_regression_test.py --manual "What is the duration of Web Development bootcamp?"
    python tests/flexible_regression_test.py --tests fabrication_detection --manual "Custom question"
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment
load_dotenv()

# Set mock Slack environment variables before importing
os.environ['SLACK_BOT_TOKEN'] = 'xoxb-test-token-for-testing'
os.environ['SLACK_SIGNING_SECRET'] = 'test-signing-secret-for-testing'

import openai
from langchain_core.messages import HumanMessage, AIMessage

class FlexibleLangGraphAdapter:
    """Adapter with detailed timing and conversation context"""
    
    def __init__(self, langgraph_pipeline):
        self.rag_graph = langgraph_pipeline
        self.conversation_contexts = {}
    
    def process_query(self, query, conversation_context=None, conversation_id=None):
        """Process a query with detailed timing and logging"""
        if not conversation_id:
            conversation_id = f"test_{hash(query)}_{int(time.time())}"
        
        # Build messages with conversation context if provided
        messages = []
        if conversation_context:
            for ctx in conversation_context:
                if ctx['role'] == 'user':
                    messages.append(HumanMessage(content=ctx['content']))
                elif ctx['role'] == 'assistant':
                    messages.append(AIMessage(content=ctx['content']))
        
        # Add current query
        messages.append(HumanMessage(content=query))
        
        # Create initial state
        initial_state = {
            "query": query,
            "conversation_id": conversation_id,
            "messages": messages,
            "processing_time": 0.0
        }
        
        # Run with timing
        start_time = time.time()
        config = {"configurable": {"thread_id": conversation_id}}
        result = self.rag_graph.invoke(initial_state, config=config)
        end_time = time.time()
        
        # Add timing to result
        result["query_processing_time"] = end_time - start_time
        
        return {
            "response": result.get("response", ""),
            "sources": result.get("sources", []),
            "selected_file_ids": result.get("selected_file_ids", []),
            "evidence_chunks": result.get("evidence_chunks", []),
            "validation": result.get("validation_result", {}),
            "confidence": result.get("confidence", 0.0),
            "processing_time": result.get("processing_time", 0.0),
            "query_processing_time": result["query_processing_time"]
        }

def initialize_pipeline():
    """Initialize the Simplified LangGraph RAG Pipeline"""
    try:
        from src.app_langgraph_rag import rag_graph
        adapter = FlexibleLangGraphAdapter(rag_graph)
        return adapter
    except Exception as e:
        raise Exception(f"Failed to initialize LangGraph pipeline: {e}")

def judge_response_detailed(response, test_type, criteria, expected_elements=None):
    """Enhanced judge with detailed feedback"""
    try:
        client = openai.OpenAI()
        
        eval_prompt = f"""
Evaluate this response for a {test_type} test.

RESPONSE TO EVALUATE:
{response}

EVALUATION CRITERIA:
{criteria}

{f"EXPECTED ELEMENTS: {expected_elements}" if expected_elements else ""}

CITATION FORMAT CONTEXT:
Our system uses this citation format: "Sources: - Document Name YYYY MM" 
This format is acceptable and should NOT be penalized for being "vague" or "improperly formatted".

Please provide a detailed evaluation in JSON format with:
{{
    "score": <number 1-10>,
    "meets_criteria": <boolean>,
    "feedback": "<detailed explanation of scoring>",
    "strengths": ["<strength 1>", "<strength 2>", ...],
    "improvements": ["<improvement 1>", "<improvement 2>", ...],
    "specific_issues": ["<issue 1>", "<issue 2>", ...],
    "citation_quality": "<assessment of source citations>",
    "accuracy_assessment": "<assessment of factual accuracy>"
}}
"""
        
        response_obj = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert evaluator. Provide detailed, constructive feedback in valid JSON format."},
                {"role": "user", "content": eval_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response_obj.choices[0].message.content)
        return result
        
    except Exception as e:
        return {
            "score": 0,
            "feedback": f"Error in evaluation: {str(e)}",
            "meets_criteria": False,
            "strengths": [],
            "improvements": ["Evaluation system error"],
            "specific_issues": [str(e)],
            "citation_quality": "Error",
            "accuracy_assessment": "Error"
        }

def display_response_analysis(response, sources, query_time, validation, test_case_info):
    """Display comprehensive response analysis"""
    print(f"\n📝 FULL RESPONSE ({len(response)} chars, ⏱️ {query_time:.2f}s):")
    print("┌" + "─" * 78 + "┐")
    for line in response.split('\n'):
        print(f"│ {line:<76} │")
    print("└" + "─" * 78 + "┘")
    
    # Display sources
    print(f"\n📚 SOURCES FOUND ({len(sources)} total):")
    if sources:
        for j, source in enumerate(sources, 1):
            print(f"   {j}. {source}")
    else:
        print("   ❌ No sources found!")
    
    # Validation info
    has_sources_section = "Sources:" in response or "sources:" in response.lower()
    print(f"\n🔍 VALIDATION:")
    print(f"   Confidence: {validation.get('confidence', 0):.2f}")
    print(f"   Contains only retrieved info: {validation.get('contains_only_retrieved_info', False)}")
    print(f"   Sources section present: {has_sources_section}")
    
    return has_sources_section

def display_judge_results(judge_result):
    """Display detailed judge evaluation results"""
    print(f"\n⚖️ JUDGE EVALUATION (Score: {judge_result.get('score', 0)}/10):")
    print(f"   ✅ Criteria Met: {judge_result.get('meets_criteria', False)}")
    print(f"   💬 Feedback: {judge_result.get('feedback', 'No feedback')}")
    print(f"   📊 Citation Quality: {judge_result.get('citation_quality', 'Not assessed')}")
    print(f"   🎯 Accuracy: {judge_result.get('accuracy_assessment', 'Not assessed')}")
    
    if judge_result.get('strengths'):
        print(f"   💪 Strengths:")
        for strength in judge_result.get('strengths', []):
            print(f"      • {strength}")
    
    if judge_result.get('improvements'):
        print(f"   🔧 Improvements:")
        for improvement in judge_result.get('improvements', []):
            print(f"      • {improvement}")
    
    if judge_result.get('specific_issues'):
        print(f"   ⚠️ Specific Issues:")
        for issue in judge_result.get('specific_issues', []):
            print(f"      • {issue}")

def test_source_citation():
    """Test source citation quality"""
    print("\n" + "="*80)
    print("TEST: SOURCE CITATION")
    print("="*80)
    
    pipeline = initialize_pipeline()
    
    test_cases = [
        {
            "query": "What programming languages are taught in Data Analytics?",
            "description": "Programming languages in Data Analytics curriculum",
            "expected": "Should cite specific curriculum documents and mention Python, SQL, etc."
        },
        {
            "query": "What are the minimum computer requirements for the bootcamps?",
            "description": "Hardware requirements query",
            "expected": "Should cite computer specs document with specific requirements"
        },
        {
            "query": "What certifications are available for Web Development graduates?",
            "description": "Certification information",
            "expected": "Should cite certification document and list specific certifications"
        }
    ]
    
    return run_test_cases(pipeline, test_cases, "source citation", """
1. Response includes a "Sources:" section at the end
2. Sources are present and identify the document used (format: "- Document Name YYYY MM")
3. Information is accurately cited and attributed to retrieved documents
4. No fabricated information is present
5. Response directly answers the question asked with specific details from the source
""")

def test_conversation_context():
    """Test conversation context retention"""
    print("\n" + "="*80)
    print("TEST: CONVERSATION CONTEXT")
    print("="*80)
    
    pipeline = initialize_pipeline()
    results = []
    
    # Conversation 1: Web Development Follow-up
    print(f"\n{'='*30} CONVERSATION 1 {'='*30}")
    print("🗣️ Conversation: Web Development Follow-up")
    
    conv_id = "test_conversation_1"
    
    # First message
    print("\n👤 User: Tell me about the Web Development bootcamp technologies")
    result1 = pipeline.process_query(
        "Tell me about the Web Development bootcamp technologies",
        conversation_id=conv_id
    )
    print(f"🤖 Assistant: {result1['response'][:100]}...")
    
    # Follow-up message
    print("\n👤 User: How long is this program?")
    start_time = time.time()
    result2 = pipeline.process_query(
        "How long is this program?",
        conversation_id=conv_id
    )
    query_time = time.time() - start_time
    
    # Analyze follow-up response
    has_sources = display_response_analysis(
        result2['response'], 
        result2.get('sources', []), 
        query_time,
        result2.get('validation', {}),
        {"description": "Follow-up question about program duration"}
    )
    
    # Judge context awareness
    judge_result = judge_response_detailed(
        result2['response'],
        "conversation context",
        """
1. Response should reference "Web Development" program specifically
2. Should provide duration information for Web Development
3. Should maintain context from previous question about Web Development
4. Should not ask which program the user is referring to
""",
        "Should specify Web Development program duration without asking for clarification"
    )
    
    display_judge_results(judge_result)
    
    results.append({
        'conversation': 1,
        'description': 'Web Development Follow-up',
        'context_query': 'Tell me about the Web Development bootcamp technologies',
        'follow_up_query': 'How long is this program?',
        'response': result2['response'],
        'query_time': query_time,
        'sources': result2.get('sources', []),
        'validation': result2.get('validation', {}),
        'judge_score': judge_result.get('score', 0),
        'judge_feedback': judge_result.get('feedback', ''),
        'meets_criteria': judge_result.get('meets_criteria', False)
    })
    
    return results

def test_fabrication_detection():
    """Test fabrication detection and safe fallbacks"""
    print("\n" + "="*80)
    print("TEST: FABRICATION DETECTION")
    print("="*80)
    
    pipeline = initialize_pipeline()
    
    test_cases = [
        {
            "query": "What specific companies partner with Ironhack for job placement in the AI Engineering program?",
            "description": "Specific partnerships (likely not documented)",
            "expected": "Should use safe fallback rather than fabricating company names",
            "fabrication_risk": "high"
        },
        {
            "query": "What is the exact salary range graduates can expect from Data Science bootcamp?",
            "description": "Specific salary information (likely not documented)",
            "expected": "Should avoid providing specific salary figures",
            "fabrication_risk": "high"
        },
        {
            "query": "How many hours per week do students typically study in the UX/UI program?",
            "description": "Specific time commitments (may not be documented)",
            "expected": "Should provide general guidance or safe fallback",
            "fabrication_risk": "medium"
        }
    ]
    
    return run_test_cases(pipeline, test_cases, "fabrication detection", """
1. No fabricated specific details (company names, exact numbers, etc.)
2. Uses safe fallback when information is not available
3. Avoids making claims not supported by retrieved documents
4. Directs users to appropriate resources when needed
5. Maintains honesty about information limitations
""")

def test_response_completeness():
    """Test response completeness and comprehensiveness"""
    print("\n" + "="*80)
    print("TEST: RESPONSE COMPLETENESS")
    print("="*80)
    
    pipeline = initialize_pipeline()
    
    test_cases = [
        {
            "query": "What tools and technologies are covered in the Web Development bootcamp?",
            "description": "Comprehensive technology overview",
            "expected": "Should provide comprehensive list of technologies, tools, and frameworks"
        },
        {
            "query": "What are the different Data Analytics bootcamp options and their differences?",
            "description": "Program variant comparison",
            "expected": "Should explain Data Analytics bootcamp options (now remote only)"
        },
        {
            "query": "What certification opportunities are available for bootcamp graduates?",
            "description": "Certification overview",
            "expected": "Should cover multiple programs and certification types available"
        }
    ]
    
    return run_test_cases(pipeline, test_cases, "response completeness", """
1. Provides comprehensive information covering all aspects of the query
2. Includes relevant details from multiple sources when appropriate
3. Addresses different variants/options when they exist
4. Gives actionable, detailed information for sales conversations
5. Maintains accuracy while being thorough
""")

def test_manual_question(question):
    """Test a manual question with detailed analysis"""
    print("\n" + "="*80)
    print("TEST: MANUAL QUESTION")
    print("="*80)
    
    pipeline = initialize_pipeline()
    
    print(f"🔍 MANUAL QUERY: {question}")
    print("-" * 70)
    
    try:
        # Process query with timing
        start_time = time.time()
        result = pipeline.process_query(question)
        query_time = time.time() - start_time
        
        # Display comprehensive analysis
        has_sources = display_response_analysis(
            result['response'], 
            result.get('sources', []), 
            query_time,
            result.get('validation', {}),
            {"description": "Manual question test"}
        )
        
        # Judge evaluation for manual question
        judge_result = judge_response_detailed(
            result['response'],
            "manual question",
            """
1. Response directly answers the question asked
2. Uses appropriate sources and citations
3. Provides accurate, helpful information
4. Maintains professional tone suitable for sales conversations
5. No fabricated information or unsupported claims
""",
            "Should provide accurate, well-sourced answer to the specific question"
        )
        
        display_judge_results(judge_result)
        
        return [{
            'test_type': 'manual_question',
            'query': question,
            'response': result['response'],
            'query_time': query_time,
            'sources': result.get('sources', []),
            'validation': result.get('validation', {}),
            'judge_score': judge_result.get('score', 0),
            'judge_feedback': judge_result.get('feedback', ''),
            'meets_criteria': judge_result.get('meets_criteria', False)
        }]
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return [{
            'test_type': 'manual_question',
            'query': question,
            'error': str(e),
            'judge_score': 0,
            'meets_criteria': False
        }]

def run_test_cases(pipeline, test_cases, test_type, criteria):
    """Generic test case runner with detailed analysis"""
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*20} TEST CASE {i} {'='*20}")
        print(f"🔍 DESCRIPTION: {test_case['description']}")
        print(f"❓ QUERY: {test_case['query']}")
        print(f"📋 EXPECTED: {test_case['expected']}")
        if 'fabrication_risk' in test_case:
            print(f"⚠️ FABRICATION RISK: {test_case['fabrication_risk']}")
        print("-" * 70)
        
        try:
            # Process query with timing
            start_time = time.time()
            result = pipeline.process_query(test_case['query'])
            query_time = time.time() - start_time
            
            # Display comprehensive analysis
            has_sources = display_response_analysis(
                result['response'], 
                result.get('sources', []), 
                query_time,
                result.get('validation', {}),
                test_case
            )
            
            # Judge evaluation
            judge_result = judge_response_detailed(
                result['response'], 
                test_type,
                criteria,
                test_case['expected']
            )
            
            display_judge_results(judge_result)
            
            # Store results
            test_result = {
                'test_case': i,
                'description': test_case['description'],
                'query': test_case['query'],
                'expected': test_case['expected'],
                'response': result['response'],
                'query_time': query_time,
                'sources': result.get('sources', []),
                'validation': result.get('validation', {}),
                'judge_score': judge_result.get('score', 0),
                'judge_feedback': judge_result.get('feedback', ''),
                'meets_criteria': judge_result.get('meets_criteria', False)
            }
            if 'fabrication_risk' in test_case:
                test_result['fabrication_risk'] = test_case['fabrication_risk']
            
            results.append(test_result)
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            results.append({
                'test_case': i,
                'description': test_case['description'],
                'query': test_case['query'],
                'error': str(e),
                'judge_score': 0,
                'meets_criteria': False
            })
    
    return results

def save_results(all_results, selected_tests):
    """Save test results with test selection info"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path("tests/results")
    results_dir.mkdir(exist_ok=True)
    
    test_suffix = "_".join(selected_tests) if selected_tests != ['all'] else "all"
    filename = f"flexible_test_{test_suffix}_{timestamp}.json"
    filepath = results_dir / filename
    
    with open(filepath, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    return str(filepath)

def print_summary(all_results):
    """Print comprehensive test summary"""
    print(f"\n{'='*80}")
    print("📊 TEST RESULTS SUMMARY")
    print("="*80)
    
    total_score = 0
    total_tests = 0
    total_passed = 0
    
    for test_name, test_data in all_results.items():
        if test_name == 'metadata':
            continue
            
        if 'error' in test_data:
            print(f"{test_name}: ❌ ERROR - {test_data['error']}")
            continue
        
        if 'results' in test_data:
            results = test_data['results']
        else:
            results = test_data
        
        if results:
            avg_score = sum(r.get('judge_score', 0) for r in results) / len(results)
            passed = sum(1 for r in results if r.get('meets_criteria', False))
            total = len(results)
            
            total_score += avg_score * total
            total_tests += total
            total_passed += passed
            
            status = '✅ PASS' if avg_score >= 7.0 else '❌ FAIL'
            print(f"{test_name}: Score {avg_score:.1f}/10 | {passed}/{total} passed | {status}")
    
    if total_tests > 0:
        overall_avg = total_score / total_tests
        overall_status = '✅ PASS' if overall_avg >= 7.0 else '❌ FAIL'
        print(f"\nOVERALL: Score {overall_avg:.1f}/10 | {total_passed}/{total_tests} passed | {overall_status}")

def main():
    """Main function with argument parsing for test selection"""
    parser = argparse.ArgumentParser(description='Flexible Regression Test for LangGraph RAG Pipeline')
    parser.add_argument('--tests', nargs='+', 
                       choices=['source_citation', 'conversation_context', 'fabrication_detection', 
                               'response_completeness', 'manual', 'all'],
                       default=['all'],
                       help='Select which tests to run')
    parser.add_argument('--manual', type=str,
                       help='Manual question to test (automatically adds manual to tests)')
    
    args = parser.parse_args()
    
    # Handle manual question
    manual_question = args.manual
    selected_tests = args.tests
    
    # If only manual question is provided (and default 'all' is in tests), just run manual
    if manual_question and args.tests == ['all']:
        selected_tests = ['manual']
    elif manual_question and 'manual' not in selected_tests:
        selected_tests.append('manual')
    elif 'all' in selected_tests:
        selected_tests = ['source_citation', 'conversation_context', 'fabrication_detection', 'response_completeness']
        if manual_question:
            selected_tests.append('manual')
    
    print("🚀 Flexible LangGraph RAG Pipeline - Regression Test")
    print("="*80)
    print(f"🎯 Running tests: {', '.join(selected_tests)}")
    if manual_question:
        print(f"❓ Manual question: {manual_question}")
    print("="*80)
    
    all_results = {}
    start_time = time.time()
    
    # Run selected tests
    test_functions = {
        'source_citation': test_source_citation,
        'conversation_context': test_conversation_context, 
        'fabrication_detection': test_fabrication_detection,
        'response_completeness': test_response_completeness
    }
    
    for test_name in selected_tests:
        if test_name == 'manual':
            if manual_question:
                try:
                    print(f"\n🔍 Running {test_name} test...")
                    results = test_manual_question(manual_question)
                    all_results['manual_question'] = results
                    print(f"✅ {test_name} test completed")
                except KeyboardInterrupt:
                    print(f"\n⏹️ {test_name} test interrupted by user")
                    break
                except Exception as e:
                    print(f"❌ {test_name} test failed: {e}")
                    all_results['manual_question'] = {'error': str(e)}
        elif test_name in test_functions:
            try:
                print(f"\n🔍 Running {test_name} test...")
                results = test_functions[test_name]()
                all_results[test_name] = results
                print(f"✅ {test_name} test completed")
            except KeyboardInterrupt:
                print(f"\n⏹️ {test_name} test interrupted by user")
                break
            except Exception as e:
                print(f"❌ {test_name} test failed: {e}")
                all_results[test_name] = {'error': str(e)}
    
    # Add metadata
    total_runtime = time.time() - start_time
    all_results['metadata'] = {
        'selected_tests': selected_tests,
        'manual_question': manual_question,
        'runtime': total_runtime,
        'timestamp': datetime.now().isoformat()
    }
    
    # Print summary
    print_summary(all_results)
    print(f"Runtime: {total_runtime:.1f} seconds")
    
    # Save results
    filepath = save_results(all_results, selected_tests)
    print(f"\n💾 Results saved to: {filepath}")
    
    print("\n🎉 Flexible regression test complete!")

if __name__ == "__main__":
    main()
