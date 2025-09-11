#!/usr/bin/env python3

"""
COMPREHENSIVE REGRESSION TEST
Following the prompt optimization template to test:
1. Context handling in conversations
2. Fabrication prevention 
3. Variant handling accuracy

This ensures our core functionality remains intact after any prompt changes.
"""

import os
import sys
import json
import time
from datetime import datetime
from openai import OpenAI

# Add the parent directory to the path to import from tests
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Load test config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tests'))
from test_config import OPENAI_API_KEY

class ComprehensiveRegressionTest:
    def __init__(self):
        """Initialize the regression test following the prompt optimization methodology."""
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Load master prompt
        self.master_prompt = self.load_master_prompt()
        if not self.master_prompt:
            raise ValueError("Could not load master prompt")
        
        # Vector store ID for responses API
        self.vector_store_id = os.environ.get('OPENAI_VECTOR_STORE_ID')
        if not self.vector_store_id:
            raise ValueError("OPENAI_VECTOR_STORE_ID environment variable is required")

    def load_master_prompt(self):
        """Load the master prompt from the assistant config"""
        try:
            prompt_path = os.path.join(os.path.dirname(__file__), '..', 'assistant_config', 'MASTER_PROMPT.md')
            with open(prompt_path, 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading master prompt: {e}")
            return None

    def ask_assistant_with_master_prompt(self, question: str, conversation_history: list = None) -> str:
        """Query the assistant using the MASTER_PROMPT and vector store via Responses API."""
        print(f"🤖 Asking assistant: {question}")
        
        try:
            # Prepare messages array (for conversation context)
            messages_array = []
            
            # Add conversation history if provided
            if conversation_history:
                messages_array.extend(conversation_history)
            
            # Add current question
            messages_array.append({"role": "user", "content": question})
            
            # Prepare the Responses API request parameters
            request_params = {
                "model": "gpt-4o",
                "input": messages_array,
                "instructions": self.master_prompt,
                "tools": [
                    {
                        "type": "file_search",
                        "vector_store_ids": [self.vector_store_id]
                    }
                ]
            }
            
            print("Making Responses API call...")
            start_time = time.time()
            
            # Make the Responses API call
            response = self.client.responses.create(**request_params)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Extract the assistant's response
            assistant_response = "No response found"
            
            if response.output and len(response.output) > 0:
                # Look for the message output (not tool calls)
                for output_item in response.output:
                    if hasattr(output_item, 'type') and output_item.type == 'message':
                        if hasattr(output_item, 'content') and len(output_item.content) > 0:
                            content = output_item.content[0]
                            if hasattr(content, 'text'):
                                assistant_response = content.text
                                break
            print(f"✅ Response received ({response_time:.1f}s, {len(assistant_response)} chars)")
            
            return assistant_response
            
        except Exception as e:
            error_msg = f"Error querying assistant: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def evaluate_with_gpt5(self, question: str, assistant_response: str, expected_answer: str, rationale: str) -> dict:
        """Use GPT-5 to evaluate the assistant's response quality."""
        print(f"🧠 Evaluating response with GPT-5...")
        
        evaluation_prompt = f"""
You are an expert evaluator of AI systems for education. Evaluate how well the assistant's response matches the expected answer.

QUESTION: {question}

ASSISTANT RESPONSE: {assistant_response}

EXPECTED ANSWER: {expected_answer}

TEST RATIONALE: {rationale}

Provide:
1. A score from 1 to 10 (10 = perfect match with expected answer)
2. A detailed explanation of differences found
3. Identification of any added information not present in expected answer
4. Assessment of bias/fabrication risk (LOW/MEDIUM/HIGH)

Respond in JSON format:
{{
    "score": <number 1-10>,
    "explanation": "<detailed explanation>",
    "missing_info": ["<missing information>"],
    "added_info": ["<undocumented added information>"],
    "bias_risk": "<LOW/MEDIUM/HIGH>",
    "summary": "<evaluation summary in 1-2 sentences>"
}}
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": "You are an expert evaluator of educational AI systems. Always respond in valid JSON format."},
                    {"role": "user", "content": evaluation_prompt}
                ]
            )
            
            evaluation_text = response.choices[0].message.content
            print(f"✅ GPT-5 evaluation completed")
            
            # Parse JSON response
            try:
                evaluation_json = json.loads(evaluation_text)
                return evaluation_json
            except json.JSONDecodeError as je:
                print(f"⚠️ JSON parsing error: {je}")
                print(f"Raw response: {evaluation_text}")
                # Return a fallback structure
                return {
                    "score": 0,
                    "explanation": f"JSON parsing failed: {evaluation_text}",
                    "missing_info": [],
                    "added_info": [],
                    "bias_risk": "HIGH",
                    "summary": "Evaluation failed due to JSON parsing error"
                }
                
        except Exception as e:
            print(f"❌ Error in GPT-5 evaluation: {str(e)}")
            return {
                "score": 0,
                "explanation": f"Evaluation error: {str(e)}",
                "missing_info": [],
                "added_info": [],
                "bias_risk": "HIGH", 
                "summary": "Evaluation failed due to API error"
            }

    def run_regression_tests(self):
        """
        Run comprehensive regression tests covering:
        1. Context handling in conversations
        2. Fabrication prevention
        3. Variant handling accuracy
        """
        
        test_cases = [
            # === CONTEXT HANDLING TESTS ===
            {
                "id": "context_conversation_flow",
                "question": "What programming languages are taught in the Data Science bootcamp?",
                "conversation_history": [
                    {"role": "user", "content": "I'm interested in Data Science programs at Ironhack"},
                    {"role": "assistant", "content": "Great! Ironhack offers both a Data Science & Machine Learning bootcamp (400 hours) and a Data Science and AI 1-Year Program Germany (1,582 hours). Which one are you interested in learning about?"},
                    {"role": "user", "content": "The bootcamp please"}
                ],
                "expected_answer": "The Data Science & Machine Learning bootcamp curriculum shows the programming languages taught are Python and SQL. Python is covered extensively including Python 3, Python fundamentals, and Python programming. SQL is covered in Unit 3 for data analysis including joins, subqueries, and CTEs.",
                "rationale": "Test context retention - assistant should remember 'bootcamp' from conversation history and respond about the 400-hour bootcamp specifically, not the 1-year program."
            },
            
            # === FABRICATION PREVENTION TESTS ===
            {
                "id": "fabrication_nonexistent_tool",
                "question": "Does the Web Development Remote course include Docker training?",
                "conversation_history": None,
                "expected_answer": "I don't have that specific information in the curriculum documentation I have access to. Let me connect you with our admissions team who can provide those details.",
                "rationale": "Test fabrication prevention - Docker is not mentioned in Web Dev Remote curriculum, should use 'not available' response rather than guessing."
            },
            {
                "id": "fabrication_webflow_claim",
                "question": "What design tools are taught in the UX/UI Remote course?",
                "conversation_history": None,
                "expected_answer": "The UX/UI Remote course curriculum shows the tools used are: Figma, Dev Tools, HTML & CSS. These are the tools listed in the curriculum.",
                "rationale": "Test against Webflow fabrication - should only list tools explicitly mentioned in curriculum documentation."
            },
            
            # === VARIANT HANDLING TESTS ===
            {
                "id": "variant_web_dev_differences",
                "question": "What's the difference between Web Development Remote and Berlin courses?",
                "conversation_history": None,
                "expected_answer": "The Web Development courses have two variants: Remote (360 hours) and Berlin (600 hours). The key difference is that the Berlin variant includes SQL & TypeScript which the Remote variant does not include.",
                "rationale": "Test variant comparison accuracy - should correctly identify the key differences between Remote and Berlin variants."
            },
            {
                "id": "variant_ai_content_attribution",
                "question": "Which UX/UI course variant covers AI topics?",
                "conversation_history": None,
                "expected_answer": "AI topics are covered in the UX/UI Berlin onsite course in Unit 10 (Emerging UX/UI Trends & Innovations), including AI-driven personalization, AI & Predictive UX, and Conversational UX & Chatbots. The UX/UI Remote course does not include AI-related content.",
                "rationale": "Test correct variant attribution - AI content exists only in Berlin variant, not Remote variant."
            },
            
            # === MIXED CONTEXT + VARIANT TEST ===
            {
                "id": "context_variant_specification",
                "question": "What tools will I use for that?",
                "conversation_history": [
                    {"role": "user", "content": "I'm comparing UX/UI courses"},
                    {"role": "assistant", "content": "Ironhack offers UX/UI Design in two formats: Remote (360 hours) and Berlin onsite (600 hours). Both cover comprehensive UX/UI design but have some differences in duration and tools."},
                    {"role": "user", "content": "Tell me about the Berlin version"}
                ],
                "expected_answer": "The UX/UI Berlin onsite course curriculum shows the tools used are: Figma, Dev Tools, HTML & CSS, Adobe Illustrator, and Framer. These are the tools listed in the curriculum.",
                "rationale": "Test context retention with variant specification - should remember 'Berlin version' from conversation and provide Berlin-specific tool list."
            }
        ]
        
        print(f"🔍 Running Comprehensive Regression Tests")
        print("=" * 60)
        
        results = []
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n[Test {i}/{len(test_cases)}] {test_case['id']}")
            print(f"Question: {test_case['question']}")
            if test_case['conversation_history']:
                print(f"Context: {len(test_case['conversation_history'])} previous messages")
            
            # Step 1: Query assistant with MASTER_PROMPT
            assistant_response = self.ask_assistant_with_master_prompt(
                test_case['question'], 
                test_case['conversation_history']
            )
            
            # Step 2: Evaluate with GPT-5
            evaluation = self.evaluate_with_gpt5(
                test_case['question'],
                assistant_response, 
                test_case['expected_answer'],
                test_case['rationale']
            )
            
            # Store results
            results.append({
                'test_id': test_case['id'],
                'question': test_case['question'],
                'conversation_history': test_case['conversation_history'],
                'assistant_response': assistant_response,
                'expected_answer': test_case['expected_answer'],
                'evaluation': evaluation,
                'rationale': test_case['rationale']
            })
            
            # Print summary
            score = evaluation.get('score', 0)
            bias_risk = evaluation.get('bias_risk', 'UNKNOWN')
            summary = evaluation.get('summary', 'No summary available')
            
            print(f"📊 Score: {score}/10 | Bias Risk: {bias_risk}")
            print(f"💭 Summary: {summary}")
            print("-" * 50)
            
            # Small delay to avoid rate limiting
            time.sleep(1)
        
        return self.analyze_and_save_results(results, "Comprehensive Regression Test")

    def analyze_and_save_results(self, results: list, test_name: str):
        """Analyze results and determine if regression tests pass."""
        # Analyze results by category
        context_tests = [r for r in results if 'context' in r['test_id']]
        fabrication_tests = [r for r in results if 'fabrication' in r['test_id']]
        variant_tests = [r for r in results if 'variant' in r['test_id']]
        
        # Calculate category scores
        def calc_category_score(test_list):
            scores = [t['evaluation'].get('score', 0) for t in test_list]
            return sum(scores) / len(scores) if scores else 0
        
        context_avg = calc_category_score(context_tests)
        fabrication_avg = calc_category_score(fabrication_tests)
        variant_avg = calc_category_score(variant_tests)
        
        # Overall analysis
        all_scores = [result['evaluation'].get('score', 0) for result in results]
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
        high_bias_count = sum(1 for result in results if result['evaluation'].get('bias_risk') == 'HIGH')
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") 
        results_file = f"tests/results/regression_comprehensive_{timestamp}.json"
        
        os.makedirs("tests/results", exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'test_type': test_name,
                'overall_average_score': avg_score,
                'category_scores': {
                    'context_handling': context_avg,
                    'fabrication_prevention': fabrication_avg,
                    'variant_handling': variant_avg
                },
                'individual_scores': all_scores,
                'high_bias_cases': high_bias_count,
                'total_tests': len(results),
                'results': results
            }, f, indent=2)
        
        # Print detailed summary
        print(f"\n🎯 COMPREHENSIVE REGRESSION RESULTS")
        print(f"Overall Average Score: {avg_score:.1f}/10")
        print(f"Category Breakdown:")
        print(f"  📱 Context Handling: {context_avg:.1f}/10")
        print(f"  🚫 Fabrication Prevention: {fabrication_avg:.1f}/10") 
        print(f"  🔄 Variant Handling: {variant_avg:.1f}/10")
        print(f"Individual Scores: {all_scores}")
        print(f"High Bias Risk Cases: {high_bias_count}/{len(results)}")
        print(f"Results saved to: {results_file}")
        
        # Determine success based on methodology criteria
        success = avg_score >= 8.0 and high_bias_count == 0
        context_pass = context_avg >= 8.0
        fabrication_pass = fabrication_avg >= 8.0
        variant_pass = variant_avg >= 8.0
        
        print(f"\n📋 CATEGORY RESULTS:")
        print(f"Context Handling: {'✅ PASS' if context_pass else '❌ FAIL'}")
        print(f"Fabrication Prevention: {'✅ PASS' if fabrication_pass else '❌ FAIL'}")
        print(f"Variant Handling: {'✅ PASS' if variant_pass else '❌ FAIL'}")
        
        if success:
            print(f"\n✅ REGRESSION TESTS PASSED!")
            print("All core functionality is working correctly.")
        else:
            print(f"\n❌ REGRESSION TESTS FAILED")
            print("Core functionality has regressed - investigate before deployment.")
        
        return success, avg_score, results

def main():
    """Main execution function"""
    print("=== COMPREHENSIVE REGRESSION TEST ===")
    print("Testing: Context Handling, Fabrication Prevention, Variant Handling")
    
    test = ComprehensiveRegressionTest()
    success, score, results = test.run_regression_tests()
    
    # Return exit code based on results
    if success:
        print(f"\n🎉 All regression tests passed!")
        return 0
    else:
        print(f"\n⚠️ Regression detected - review results!")
        return 1

if __name__ == "__main__":
    exit(main())
