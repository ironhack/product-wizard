#!/usr/bin/env python3

"""
PROMPT OPTIMIZATION TEMPLATE
Use this template to create new prompt optimization tests following our proven methodology.

This framework can be applied to any unwanted behavior or performance issue.
"""

import os
import sys
import json
import time
from datetime import datetime
from openai import OpenAI

# Add the parent directory to the path to import from src
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

class PromptOptimizationFramework:
    def __init__(self):
        """Initialize the framework following the prompt optimization methodology."""
        self.client = OpenAI()
        
        # Load master prompt
        self.master_prompt = self.load_master_prompt()
        if not self.master_prompt:
            raise ValueError("Could not load master prompt")
        
        # Vector store ID for responses API
        self.vector_store_id = os.getenv('OPENAI_VECTOR_STORE_ID')
        if not self.vector_store_id:
            raise ValueError("OPENAI_VECTOR_STORE_ID environment variable is required")

    def load_master_prompt(self):
        """Load the master prompt from the assistant config"""
        try:
            with open('assistant_config/MASTER_PROMPT.md', 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading master prompt: {e}")
            return None

    def ask_assistant_with_master_prompt(self, question: str) -> str:
        """Query the assistant using the MASTER_PROMPT and vector store via Responses API."""
        print(f"🤖 Asking assistant: {question}")
        
        try:
            # Prepare the Responses API request parameters
            request_params = {
                "model": "gpt-4o-mini",  # Following the methodology pattern
                "input": question,
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
                model="gpt-5",  # Using GPT-5 as specified in methodology
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
                "bias_risk": "ALTO", 
                "summary": "Evaluation failed due to API error"
            }

    def run_optimization_tests(self, test_cases: list, test_name: str):
        """
        Run prompt optimization tests.
        
        Args:
            test_cases: List of test cases with 'id', 'question', 'expected_answer', 'rationale'
            test_name: Name for this test run (used in results file)
        """
        print(f"🔍 Running {test_name}")
        print("=" * 50)
        
        results = []
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n[Test {i}/{len(test_cases)}] {test_case['id']}")
            print(f"Question: {test_case['question']}")
            
            # Step 1: Query assistant with MASTER_PROMPT
            assistant_response = self.ask_assistant_with_master_prompt(test_case['question'])
            
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
            print("-" * 40)
        
        return self.analyze_and_save_results(results, test_name)

    def analyze_and_save_results(self, results: list, test_name: str):
        """Analyze results and determine if iteration is needed."""
        # Analyze results
        scores = [result['evaluation'].get('score', 0) for result in results]
        avg_score = sum(scores) / len(scores) if scores else 0
        high_bias_count = sum(1 for result in results if result['evaluation'].get('bias_risk') == 'HIGH')
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") 
        results_file = f"tests/results/{test_name.lower().replace(' ', '_')}_{timestamp}.json"
        
        os.makedirs("tests/results", exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'test_type': test_name,
                'average_score': avg_score,
                'individual_scores': scores,
                'high_bias_cases': high_bias_count,
                'results': results
            }, f, indent=2)
        
        # Print final summary
        print(f"\n🎯 FINAL RESULTS")
        print(f"Average Score: {avg_score:.1f}/10")
        print(f"Individual Scores: {scores}")
        print(f"High Bias Risk Cases: {high_bias_count}")
        print(f"Results saved to: {results_file}")
        
        # Determine success based on methodology criteria
        success = avg_score >= 8.0 and high_bias_count == 0
        
        if success:
            print(f"\n✅ TESTS PASSED!")
            print("Prompt improvements are working effectively.")
        else:
            print(f"\n❌ TESTS NEED IMPROVEMENT")
            print("Need to iterate on the prompt.")
        
        return success, avg_score, results

# TEMPLATE USAGE EXAMPLE:
def example_usage():
    """
    Example of how to use this template for prompt optimization.
    
    1. Define your problem and hypothesis
    2. Create test cases that target the specific issue
    3. Run tests and analyze results
    4. Iterate if needed
    """
    
    # Initialize framework
    framework = PromptOptimizationFramework()
    
    # Define test cases targeting your specific hypothesis
    test_cases = [
        {
            "id": "example_test_1",
            "question": "Your test question here",
            "expected_answer": "Expected response based on documents",
            "rationale": "What this test is checking for"
        },
        # Add more test cases...
    ]
    
    # Run tests
    success, score, results = framework.run_optimization_tests(
        test_cases, 
        "Example Prompt Optimization Test"
    )
    
    return success, score, results

if __name__ == "__main__":
    print("🚀 Prompt Optimization Template")
    print("Modify the example_usage() function with your specific test cases")
    print("Follow the methodology: Problem → Hypothesis → Test → Analyze → Iterate")
