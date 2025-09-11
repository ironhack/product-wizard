#!/usr/bin/env python3
"""
Fabrication Testing: Tools and Course Variants
Tests the specific fabrication patterns identified in Slack:
1. Webflow claim in UX/UI courses
2. AI features misattributed to wrong variants
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from openai import OpenAI
from test_config import OPENAI_API_KEY

# Load environment variables for vector store
from dotenv import load_dotenv
load_dotenv()

class FabricationDetectionTest:
    def __init__(self):
        """Initialize the fabrication detection test with OpenAI client."""
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Load MASTER_PROMPT
        prompt_path = os.path.join(os.path.dirname(__file__), '..', 'assistant_config', 'MASTER_PROMPT.md')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.master_prompt = f.read()
    
    def query_assistant(self, question: str) -> str:
        """Query assistant using Responses API with file search (like production)"""
        try:
            # Get vector store ID from environment 
            vector_store_id = os.environ.get("OPENAI_VECTOR_STORE_ID")
            if not vector_store_id:
                return "Error: OPENAI_VECTOR_STORE_ID not found in environment"

            # Prepare Responses API request (matching production)
            request_params = {
                "model": "gpt-4o",
                "input": [{"role": "user", "content": question}],
                "instructions": self.master_prompt,
                "tools": [
                    {
                        "type": "file_search",
                        "vector_store_ids": [vector_store_id]
                    }
                ]
            }
            
            # Use Responses API like production
            response = self.client.responses.create(**request_params)
            
            # Extract response like production app
            assistant_response = "No response found"
            if response.output and len(response.output) > 0:
                for output_item in response.output:
                    if hasattr(output_item, 'type') and output_item.type == 'message':
                        if hasattr(output_item, 'content') and len(output_item.content) > 0:
                            content = output_item.content[0]
                            if hasattr(content, 'text'):
                                assistant_response = content.text
                                break
            
            return assistant_response
            
        except Exception as e:
            return f"Error querying assistant: {str(e)}"

    def evaluate_with_gpt5_judge(self, question: str, assistant_response: str, expected_answer: str, rationale: str) -> Dict:
        """Evaluate assistant response using GPT-5 as judge"""
        
        evaluation_prompt = f"""You are an expert evaluator assessing the accuracy of an AI assistant's response about Ironhack course curricula.

QUESTION: {question}

ASSISTANT RESPONSE:
{assistant_response}

EXPECTED ANSWER:
{expected_answer}

EVALUATION RATIONALE:
{rationale}

Evaluate the assistant's response on accuracy, precision, and bias risk:

SCORING CRITERIA:
- 10/10: Perfect accuracy, exactly matches expected answer
- 8-9/10: Minor additions or context, factually correct
- 6-7/10: Some fabrication or wrong course attribution  
- 4-5/10: Major fabrication or significant errors
- 1-3/10: Mostly incorrect or highly fabricated
- 0/10: Complete failure or opposite of expected

BIAS RISK CATEGORIES:
- BASSO: Low risk - minor context additions, factually correct
- MEDIO: Medium risk - some assumptions, partially incorrect
- ALTO: High risk - clear fabrication, wrong course attribution, tools not in curriculum

Respond in this exact JSON format:
{{
    "score": <number 0-10>,
    "bias_risk": "<BASSO|MEDIO|ALTO>",
    "reasoning": "<detailed explanation>",
    "key_issues": ["<list of main problems>"],
    "fabricated_elements": ["<list of any fabricated claims>"]
}}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": "You are an expert evaluator of educational AI systems. Always respond in valid JSON format."},
                    {"role": "user", "content": evaluation_prompt}
                ]
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"error": "No JSON found in response", "raw_content": content}
                
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON", "raw_content": content}
        except Exception as e:
            return {"error": f"Evaluation error: {str(e)}"}

    def run_test(self) -> Dict:
        """Run fabrication detection tests"""
        
        test_cases = [
            {
                "id": "webflow_uxui_remote",
                "question": "What no-code web tools are used in the UX/UI Remote course?",
                "expected_answer": "The UX/UI Remote course curriculum shows the tools used are: Figma, Dev Tools, HTML & CSS. No no-code web tools like Webflow are mentioned in the curriculum documentation.",
                "rationale": "Test for fabricated Webflow claim. Only Figma, Dev Tools, HTML & CSS are documented.",
                "vulnerability": "Adding popular tools not in curriculum"
            },
            {
                "id": "webflow_uxui_berlin",
                "question": "Does the UX/UI Berlin course include Webflow training?",
                "expected_answer": "The UX/UI Berlin onsite course curriculum shows the tools used are: Figma, Dev Tools, HTML & CSS, Adobe Illustrator, Framer. Webflow is not mentioned in the curriculum documentation.",
                "rationale": "Test for fabricated Webflow claim in Berlin variant. Webflow is not documented in either UX/UI variant.",
                "vulnerability": "Assuming popular tools are included without verification"
            },
            {
                "id": "ai_uxui_remote_specific",
                "question": "Is there any focus on AI in the UX/UI Remote course specifically?",
                "expected_answer": "The UX/UI Remote course curriculum does not include any AI-related content. AI topics are covered in the UX/UI Berlin onsite course in Unit 10 (Emerging UX/UI Trends), but not in the Remote variant.",
                "rationale": "Test for wrong variant attribution. AI content exists only in Berlin variant, not Remote.",
                "vulnerability": "Mixing content between course variants"
            },
            {
                "id": "ai_uxui_berlin_correct",
                "question": "What AI-related topics are covered in the UX/UI Berlin course?",
                "expected_answer": "The UX/UI Berlin onsite course covers AI in Unit 10 (Emerging UX/UI Trends & Innovations), including: AI-driven personalization, AI & Predictive UX (how AI impacts personalization and user behavior), and Conversational UX & Chatbots (enhancing user interactions through AI).",
                "rationale": "Control test - verify correct AI information attribution to Berlin variant.",
                "vulnerability": "Should correctly identify AI content in Berlin variant"
            }
        ]
        
        results = {}
        
        print("🧪 Testing Fabrication Patterns: Tools and Course Variants")
        print("=" * 60)
        
        for test_case in test_cases:
            print(f"\n📋 Test: {test_case['id']}")
            print(f"❓ Question: {test_case['question']}")
            
            # Get assistant response
            print("🤖 Querying assistant...")
            assistant_response = self.query_assistant(test_case['question'])
            
            # Evaluate with GPT-5 judge
            print("⚖️  Evaluating with judge...")
            evaluation = self.evaluate_with_gpt5_judge(
                question=test_case['question'],
                assistant_response=assistant_response,
                expected_answer=test_case['expected_answer'],
                rationale=test_case['rationale']
            )
            
            # Store results
            results[test_case['id']] = {
                "question": test_case['question'],
                "assistant_response": assistant_response,
                "expected_answer": test_case['expected_answer'],
                "evaluation": evaluation,
                "vulnerability_tested": test_case['vulnerability']
            }
            
            # Display results
            score = evaluation.get('score', 'N/A')
            bias_risk = evaluation.get('bias_risk', 'N/A')
            print(f"📊 Score: {score}/10 | Bias Risk: {bias_risk}")
            
            if evaluation.get('fabricated_elements'):
                print(f"🚨 Fabricated Elements: {evaluation['fabricated_elements']}")
            
            print("-" * 40)
            time.sleep(1)  # Rate limiting
        
        # Calculate summary statistics
        scores = [r['evaluation'].get('score', 0) for r in results.values() if 'score' in r['evaluation']]
        high_risk_count = sum(1 for r in results.values() if r['evaluation'].get('bias_risk') == 'ALTO')
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(test_cases),
            "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "score_range": f"{min(scores)}-{max(scores)}" if scores else "N/A",
            "high_bias_risk_count": high_risk_count,
            "results": results
        }
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        results_file = os.path.join(results_dir, f'fabrication_tools_variants_{timestamp}.json')
        with open(results_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📈 SUMMARY RESULTS")
        print(f"Average Score: {summary['average_score']}/10")
        print(f"Score Range: {summary['score_range']}")
        print(f"High Bias Risk Tests: {summary['high_bias_risk_count']}/{summary['total_tests']}")
        print(f"Results saved: {results_file}")
        
        return summary

def main():
    """Main execution function"""
    print("=== FABRICATION DETECTION TEST: TOOLS & VARIANTS ===")
    
    test = FabricationDetectionTest()
    results = test.run_test()
    
    # Return exit code based on results
    if results['high_bias_risk_count'] > 0:
        print("\n🚨 WARNING: High bias risk detected!")
        return 1
    elif results['average_score'] < 8.0:
        print("\n⚠️  WARNING: Average score below threshold!")
        return 1
    else:
        print("\n✅ Tests passed!")
        return 0

if __name__ == "__main__":
    exit(main())
