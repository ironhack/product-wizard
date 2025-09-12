#!/usr/bin/env python3

"""
Regression Test Suite for Custom RAG Pipeline

This test suite validates four critical aspects of the system:
1. Source Citation - Ensures responses properly cite their sources
2. Conversation Context - Validates context retention across multi-turn conversations
3. Fabrication Detection - Prevents hallucination and ensures factual accuracy
4. Response Completeness - Compares responses against expected comprehensive answers

Each test includes a judge step that automatically evaluates the quality of responses.
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

def judge_completeness(actual_response, expected_answer, test_type):
    """
    Use GPT-4o to judge how complete the actual response is compared to the expected comprehensive answer
    """
    try:
        import openai
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        judge_prompt = f"""
You are evaluating the completeness of a response from an educational chatbot by comparing it to an expected comprehensive answer.

TEST TYPE: {test_type}

EXPECTED COMPREHENSIVE ANSWER:
{expected_answer}

ACTUAL RESPONSE TO EVALUATE:
{actual_response}

Your task is to evaluate how well the actual response covers the information provided in the expected answer. Consider:

1. COVERAGE: What percentage of key information from the expected answer is present?
2. ACCURACY: Is the information that IS present correct?
3. STRUCTURE: Is the response well-organized and easy to follow?
4. COMPLETENESS: Are there major omissions that would impact usefulness?
5. RELEVANCE: Does it stay focused on the question asked?
6. SOURCE CITATION: If sources are provided, they should use file names (e.g., "Certifications_2025_07.txt")

Provide your evaluation in the following JSON format:
{{
    "score": <1-10>,
    "passed": <true/false>,
    "coverage_percentage": <0-100>,
    "missing_elements": ["element1", "element2"],
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "explanation": "Detailed explanation comparing actual vs expected"
}}

Scoring Guidelines:
- 9-10: Nearly complete coverage (90%+) with excellent accuracy
- 7-8: Good coverage (70-89%) with minor omissions
- 5-6: Adequate coverage (50-69%) with some important gaps
- 3-4: Limited coverage (30-49%) with significant omissions
- 1-2: Poor coverage (<30%) with major gaps
"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a thorough educational content evaluator specializing in completeness analysis. Always respond in valid JSON format."},
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
            "coverage_percentage": 0,
            "missing_elements": [f"Judge evaluation failed: {str(e)}"],
            "strengths": [],
            "weaknesses": [f"Judge evaluation failed: {str(e)}"],
            "explanation": f"Error during evaluation: {str(e)}"
        }

def test_source_citation(pipeline):
    """Test 1: Source Citation Accuracy"""
    print("\n🧪 TEST 1: SOURCE CITATION")
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

def test_conversation_context(pipeline):
    """Test 2: Conversation Context Retention - Using Real Conversation Management System"""
    print("\n🧪 TEST 2: CONVERSATION CONTEXT")
    print("=" * 50)
    
    # Import the actual conversation management functions
    from src.app_custom_rag import (
        get_conversation_context, 
        add_message_to_conversation, 
        load_conversation_mapping, 
        save_conversation_mapping
    )
    
    conversation_flow = [
        {
            "query": "What certifications does Ironhack offer for Data Analytics?",
            "description": "Initial query about Data Analytics certifications",
            "expected_keywords": ["certification", "data analytics", "tableau", "sql"]
        },
        {
            "query": "What about for Web Development?",
            "description": "Follow-up query - should understand 'what about' refers to certifications",
            "expected_keywords": ["certification", "web development", "node.js", "mongodb"],
            "should_understand_context": True
        },
        {
            "query": "How long is that bootcamp?",
            "description": "Follow-up query - should understand 'that bootcamp' refers to Web Development",
            "expected_keywords": ["web development", "duration", "hours", "360", "600"],
            "should_understand_context": True
        }
    ]
    
    results = []
    conversation_id = "test_conversation_context_123"
    
    # Clear any existing conversation for clean test
    try:
        mapping = load_conversation_mapping()
        if conversation_id in mapping:
            del mapping[conversation_id]
            save_conversation_mapping(mapping)
        print(f"🧹 Cleared existing conversation: {conversation_id}")
    except Exception as e:
        print(f"⚠️  Warning: Could not clear existing conversation: {e}")
    
    for i, turn in enumerate(conversation_flow, 1):
        print(f"\n[Test 2.{i}] {turn['description']}")
        print(f"Query: {turn['query']}")
        print("-" * 40)
        
        try:
            # Get conversation context using the real system
            context = get_conversation_context(conversation_id)
            print(f"📚 Retrieved context: {len(context)} messages")
            
            # Process query with real conversation context
            result = pipeline.process_query(turn['query'], context)
            response = result['response']
            sources = result['sources']
            processing_time = result['processing_time']
            
            print(f"📊 Sources: {sources}")
            print(f"⏱️  Time: {processing_time:.2f}s")
            
            # Add messages to conversation using the real system (like Slack app does)
            add_message_to_conversation(conversation_id, "user", turn['query'])
            add_message_to_conversation(conversation_id, "assistant", response)
            
            # Verify context was properly stored
            updated_context = get_conversation_context(conversation_id)
            expected_context_length = i * 2  # user + assistant for each turn
            print(f"💾 Stored context: {len(updated_context)} messages (expected: {expected_context_length})")
            
            # Validate context storage
            context_stored_correctly = len(updated_context) == expected_context_length
            if not context_stored_correctly:
                print(f"⚠️  Context storage issue: expected {expected_context_length}, got {len(updated_context)}")
            
            # Check if response shows understanding of context
            context_understanding = True
            if turn.get('should_understand_context', False):
                # Check if response contains expected keywords from context
                response_lower = response.lower()
                expected_keywords = turn.get('expected_keywords', [])
                keywords_found = sum(1 for keyword in expected_keywords if keyword.lower() in response_lower)
                context_understanding = keywords_found >= len(expected_keywords) * 0.5  # At least 50% of keywords
                
                print(f"🧠 Context understanding: {'✅' if context_understanding else '❌'}")
                print(f"   Expected keywords: {expected_keywords}")
                print(f"   Keywords found: {keywords_found}/{len(expected_keywords)}")
            
            # Judge the response
            criteria = f"""
            1. Response should be contextually appropriate for turn {i} in conversation
            2. Should demonstrate understanding of conversation flow
            3. Should provide accurate information without fabrication
            4. Should maintain professional tone suitable for sales team
            5. Source citation should use file names (e.g., "Certifications_2025_07.txt")
            """
            
            if turn.get('should_understand_context', False):
                criteria += f"\n6. Should show understanding of context with keywords: {turn.get('expected_keywords', [])}"
            
            judge_result = judge_response(
                response,
                "Conversation Context",
                criteria,
                turn.get('expected_keywords')
            )
            
            # Additional validation for context understanding
            if turn.get('should_understand_context', False) and not context_understanding:
                judge_result['score'] = max(1, judge_result['score'] - 3)  # Penalize for poor context understanding
                judge_result['passed'] = judge_result['score'] >= 6
                judge_result['weaknesses'].append("Failed to demonstrate understanding of conversation context")
            
            test_result = {
                "test": f"2.{i}",
                "query": turn['query'],
                "response": response,
                "sources": sources,
                "processing_time": processing_time,
                "conversation_length": len(updated_context),
                "context_stored_correctly": context_stored_correctly,
                "context_understanding": context_understanding,
                "judge_score": judge_result['score'],
                "judge_passed": judge_result['passed'],
                "judge_feedback": judge_result
            }
            
            results.append(test_result)
            
            print(f"🎯 Judge Score: {judge_result['score']}/10")
            print(f"✅ Passed: {judge_result['passed']}")
            print(f"💾 Context Stored: {'✅' if context_stored_correctly else '❌'}")
            print(f"🧠 Context Understood: {'✅' if context_understanding else '❌'}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "test": f"2.{i}",
                "query": turn['query'],
                "error": str(e),
                "judge_score": 0,
                "judge_passed": False,
                "context_stored_correctly": False,
                "context_understanding": False
            })
    
    # Clean up test conversation
    try:
        mapping = load_conversation_mapping()
        if conversation_id in mapping:
            del mapping[conversation_id]
            save_conversation_mapping(mapping)
        print(f"🧹 Cleaned up test conversation: {conversation_id}")
    except Exception as e:
        print(f"⚠️  Warning: Could not clean up test conversation: {e}")
    
    return results

def test_fabrication_detection(pipeline):
    """Test 3: Fabrication Detection"""
    print("\n🧪 TEST 3: FABRICATION DETECTION")
    print("=" * 50)
    
    test_cases = [
        {
            "query": "How much does the Data Analytics bootcamp cost?",
            "description": "Query about information not in documents (pricing)",
            "expected_behavior": "Should defer to Education team, not fabricate pricing"
        },
        {
            "query": "What is the acceptance rate for Ironhack programs?",
            "description": "Query about statistics not in documents",
            "expected_behavior": "Should defer to Education team, not fabricate statistics"
        },
        {
            "query": "What companies hire Ironhack graduates?",
            "description": "Query about employment outcomes not in documents",
            "expected_behavior": "Should defer to Education team, not fabricate company names"
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
            
            # Check for appropriate deferral language
            defers_properly = any(phrase in response.lower() for phrase in [
                "don't have that specific information",
                "reach out to the education team",
                "education team on slack"
            ])
            
            print(f"🛡️  Proper Deferral: {'✅ Yes' if defers_properly else '❌ No'}")
            
            # Judge the response
            criteria = f"""
            1. Should NOT fabricate information not in the documents
            2. Should appropriately defer to Education team for missing information
            3. Should use phrase "reach out to the Education team on Slack"
            4. Should NOT provide specific numbers, statistics, or company names not in documents
            5. Should maintain professional tone while admitting limitations
            6. If sources are provided, they should use file names (e.g., "Certifications_2025_07.txt")
            """
            
            judge_result = judge_response(
                response,
                "Fabrication Detection",
                criteria,
                ["education team", "slack", "don't have"]
            )
            
            test_result = {
                "test": f"3.{i}",
                "query": case['query'],
                "response": response,
                "sources": sources,
                "processing_time": processing_time,
                "defers_properly": defers_properly,
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
                "test": f"3.{i}",
                "query": case['query'],
                "error": str(e),
                "judge_score": 0,
                "judge_passed": False
            })
    
    return results

def test_ambiguity_handling(pipeline):
    """Test 4: Ambiguity Handling - Test system's ability to distinguish between similar programs"""
    print("\n🧪 TEST 4: AMBIGUITY HANDLING")
    print("=" * 50)
    
    test_cases = [
        {
            "query": "What's the difference between Data Analytics and Data Science bootcamps?",
            "description": "Should clearly distinguish between Data Analytics and Data Science programs",
            "expected_specificity": "Should mention duration differences (360h vs 400h), curriculum focus, and specific technologies",
            "criteria": "Must clearly distinguish between Data Analytics (360h) and Data Science & ML (400h) programs, highlighting key differences in curriculum and focus"
        },
        {
            "query": "Does Web Development cover SQL?",
            "description": "Should distinguish between Remote (no SQL) and Berlin onsite (includes SQL) programs",
            "expected_specificity": "Should clarify that Remote doesn't include SQL, but Berlin onsite does",
            "criteria": "Must distinguish between Web Dev Remote (no SQL) and Berlin onsite (includes SQL in Unit 6)"
        },
        {
            "query": "What's the difference between the Data Science bootcamp and the 1-year Data Science program?",
            "description": "Should clearly distinguish between bootcamp (400h) and 1-year program (1,582h)",
            "expected_specificity": "Should highlight duration, depth, and scope differences between bootcamp and 1-year program",
            "criteria": "Must clearly distinguish between Data Science bootcamp (400h) and 1-year program (1,582h), highlighting duration, depth, and scope differences"
        }
    ]
    
    results = []
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n[Test 4.{i}] {case['description']}")
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
            judge_prompt = f"""
You are evaluating a response from an educational chatbot for its ability to handle ambiguous queries and provide specific, accurate information.

TEST TYPE: Ambiguity Handling
CRITERIA: {case['criteria']}

RESPONSE TO EVALUATE:
{response}

EXPECTED SPECIFICITY: {case['expected_specificity']}

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
            
            import openai
            client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            judge_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a strict educational content evaluator specializing in ambiguity handling. Always respond in valid JSON format."},
                    {"role": "user", "content": judge_prompt}
                ],
                temperature=0.1
            )
            
            judge_result = judge_response.choices[0].message.content.strip()
            
            # Clean up JSON response
            if judge_result.startswith('```json'):
                judge_result = judge_result.replace('```json', '').replace('```', '').strip()
            
            judge_data = json.loads(judge_result)
            
            test_result = {
                "test": f"4.{i}",
                "query": case['query'],
                "response": response,
                "sources": sources,
                "processing_time": processing_time,
                "clarity_score": judge_data['clarity_score'],
                "specificity_score": judge_data['specificity_score'],
                "accuracy_score": judge_data['accuracy_score'],
                "disambiguation_quality": judge_data['disambiguation_quality'],
                "judge_score": judge_data['score'],
                "judge_passed": judge_data['passed'],
                "judge_feedback": judge_data
            }
            
            results.append(test_result)
            
            print(f"🎯 Judge Score: {judge_data['score']}/10")
            print(f"📊 Clarity: {judge_data['clarity_score']}/10")
            print(f"🎯 Specificity: {judge_data['specificity_score']}/10")
            print(f"✅ Passed: {judge_data['passed']}")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            results.append({
                "test": f"4.{i}",
                "query": case['query'],
                "error": str(e),
                "judge_score": 0,
                "judge_passed": False
            })
    
    return results

def test_response_completeness(pipeline):
    """Test 5: Response Completeness - Compare against expected comprehensive answers"""
    print("\n🧪 TEST 5: RESPONSE COMPLETENESS")
    print("=" * 50)
    
    test_cases = [
        {
            "query": "Tell me about the Data Science & Machine Learning bootcamp",
            "description": "Comprehensive overview of Data Science bootcamp",
            "expected_answer": """The Data Science & Machine Learning bootcamp is a 9-week full-time intensive program (400 hours total) designed to prepare students for data science careers. 

**Program Structure:**
- Duration: 9 weeks full-time
- Total hours: 400 hours
- Schedule: Monday to Friday, 9:00-18:00
- Format: Available both remote and onsite

**Learning Outcomes:**
Students will learn to collect, analyze, and interpret data to solve business problems using industry-standard tools and techniques. The curriculum covers statistical analysis, machine learning algorithms, data visualization, and practical application of data science methodologies.

**Key Technologies & Tools:**
- Python programming language
- SQL for database management
- Statistical analysis and hypothesis testing
- Machine learning libraries (scikit-learn, pandas, numpy)
- Data visualization tools (matplotlib, seaborn, plotly)
- Business Intelligence tools
- Version control with Git
- Cloud platforms and deployment

**Career Focus:**
The program prepares students for roles such as Data Scientist, Data Analyst, Machine Learning Engineer, and Business Intelligence Analyst. Emphasis is placed on real-world project experience and portfolio development.

**Prerequisites:**
Basic mathematical background is recommended, though the program is designed to accommodate students from various backgrounds.

Source: Data_Science_&_Machine_Learning_bootcamp_2025_07"""
        },
        {
            "query": "What are the main differences between the Web Development Remote and Berlin onsite programs?",
            "description": "Comparison between remote and onsite Web Dev programs",
            "expected_answer": """The Web Development programs differ significantly in duration, content, and delivery format:

**Web Development Remote:**
- Duration: 360 hours + 40 hours prework
- Format: 100% online delivery
- Core Technologies: HTML, CSS, JavaScript, React, Node.js, MongoDB
- Students can participate from anywhere with reliable internet
- Virtual classroom environment with digital collaboration tools
- Online mentorship and support
- Flexibility for students who cannot relocate

**Web Development Berlin Onsite:**
- Duration: 600 hours + 50 hours prework (significantly longer)
- Format: Physical classroom in Berlin location
- Extended Technologies: All Remote technologies PLUS SQL, TypeScript, Next.js, PostgreSQL, Prisma
- Additional Modules: SQL & TypeScript Foundations, Modern Full-Stack with Next.js
- Face-to-face interaction with instructors and peers
- In-person networking opportunities and immediate hands-on support
- Traditional classroom experience with direct access to campus facilities

**Key Differences:**
- **Duration**: Berlin program is 240 hours longer (600h vs 360h)
- **Technologies**: Berlin includes advanced technologies (SQL, TypeScript, Next.js) not in Remote
- **Content Depth**: Berlin has additional modules and more comprehensive curriculum
- **Format**: Remote for flexibility, Berlin for immersive experience

**Career Outcomes:**
Both programs prepare students for web development roles, but Berlin graduates have additional skills in modern full-stack development with TypeScript and Next.js.

**Target Audience:**
- Remote: Students seeking core web development skills with flexibility
- Berlin Onsite: Students wanting comprehensive full-stack training with advanced technologies

Source: Web_Dev_Remote_bootcamp_2025_07, Web_Dev_Berlin_onsite_bootcamp_2025_07"""
        }
    ]
    
    results = []
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n[Test 4.{i}] {case['description']}")
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
            
            # Judge completeness against expected answer
            judge_result = judge_completeness(
                response,
                case['expected_answer'],
                "Response Completeness"
            )
            
            # Calculate completeness metrics
            coverage = judge_result.get('coverage_percentage', 0)
            missing_elements = judge_result.get('missing_elements', [])
            
            print(f"📈 Coverage: {coverage}%")
            print(f"❌ Missing Elements: {len(missing_elements)}")
            
            test_result = {
                "test": f"4.{i}",
                "query": case['query'],
                "response": response,
                "expected_answer": case['expected_answer'],
                "sources": sources,
                "processing_time": processing_time,
                "coverage_percentage": coverage,
                "missing_elements_count": len(missing_elements),
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
                "test": f"4.{i}",
                "query": case['query'],
                "error": str(e),
                "judge_score": 0,
                "judge_passed": False,
                "coverage_percentage": 0
            })
    
    return results

def generate_report(all_results):
    """Generate comprehensive test report"""
    print("\n" + "=" * 60)
    print("🏆 REGRESSION TEST REPORT")
    print("=" * 60)
    
    # Calculate overall statistics
    total_tests = len(all_results)
    passed_tests = sum(1 for result in all_results if result.get('judge_passed', False))
    avg_score = sum(result.get('judge_score', 0) for result in all_results) / total_tests if total_tests > 0 else 0
    avg_time = sum(result.get('processing_time', 0) for result in all_results if 'processing_time' in result) / total_tests if total_tests > 0 else 0
    
    print(f"📊 OVERALL RESULTS:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
    print(f"   Average Score: {avg_score:.1f}/10")
    print(f"   Average Processing Time: {avg_time:.2f}s")
    
    # Test category breakdown
    categories = {
        "Source Citation": [r for r in all_results if r.get('test', '').startswith('1.')],
        "Conversation Context": [r for r in all_results if r.get('test', '').startswith('2.')],
        "Fabrication Detection": [r for r in all_results if r.get('test', '').startswith('3.')],
        "Ambiguity Handling": [r for r in all_results if r.get('test', '').startswith('4.')],
        "Response Completeness": [r for r in all_results if r.get('test', '').startswith('5.')]
    }
    
    print(f"\n📋 CATEGORY BREAKDOWN:")
    for category, results in categories.items():
        if results:
            category_passed = sum(1 for r in results if r.get('judge_passed', False))
            category_avg = sum(r.get('judge_score', 0) for r in results) / len(results)
            print(f"   {category}: {category_passed}/{len(results)} passed, avg {category_avg:.1f}/10")
    
    # Quality gates
    print(f"\n🚦 QUALITY GATES:")
    print(f"   ✅ Passing Rate > 80%: {'PASS' if (passed_tests/total_tests) > 0.8 else 'FAIL'}")
    print(f"   ✅ Average Score > 7.0: {'PASS' if avg_score > 7.0 else 'FAIL'}")
    print(f"   ✅ No Category < 70%: {'PASS' if all((sum(1 for r in results if r.get('judge_passed', False))/len(results)) > 0.7 for results in categories.values() if results) else 'FAIL'}")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"tests/results/regression_test_{timestamp}.json"
    
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
            "categories": {name: len(results) for name, results in categories.items()},
            "results": all_results
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    
    return {
        "pass_rate": passed_tests/total_tests,
        "average_score": avg_score,
        "results_file": results_file
    }

def main():
    """Run the complete regression test suite"""
    print("🚀 CUSTOM RAG REGRESSION TEST SUITE")
    print("=" * 60)
    print("Testing: Source Citation, Conversation Context, Fabrication Detection, Ambiguity Handling, Response Completeness")
    print("With automatic judge evaluation for each test case")
    print()
    
    try:
        # Initialize pipeline
        print("🔧 Initializing Custom RAG Pipeline...")
        pipeline = initialize_pipeline()
        print("✅ Pipeline initialized successfully")
        
        # Run all tests
        all_results = []
        
        # Test 1: Source Citation
        source_results = test_source_citation(pipeline)
        all_results.extend(source_results)
        
        # Test 2: Conversation Context
        context_results = test_conversation_context(pipeline)
        all_results.extend(context_results)
        
        # Test 3: Fabrication Detection
        fabrication_results = test_fabrication_detection(pipeline)
        all_results.extend(fabrication_results)
        
        # Test 4: Ambiguity Handling
        ambiguity_results = test_ambiguity_handling(pipeline)
        all_results.extend(ambiguity_results)
        
        # Test 5: Response Completeness
        completeness_results = test_response_completeness(pipeline)
        all_results.extend(completeness_results)
        
        # Generate report
        report = generate_report(all_results)
        
        # Exit with appropriate code
        if report['pass_rate'] > 0.8 and report['average_score'] > 7.0:
            print("\n🎉 ALL TESTS PASSED - System is ready for deployment!")
            return 0
        else:
            print("\n⚠️  SOME TESTS FAILED - Review results before deployment")
            return 1
            
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
