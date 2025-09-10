#!/usr/bin/env python3

"""
Test certification search accuracy and cross-program contamination fixes.
This test targets the specific issues found in the Slack conversation where
the assistant mixed up certifications between different programs.

Based on PROMPT_OPTIMIZATION_METHODOLOGY.md framework.
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

def load_master_prompt():
    """Load the master prompt from the assistant config"""
    try:
        with open('assistant_config/MASTER_PROMPT.md', 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading master prompt: {e}")
        return None

class CertificationTestFramework:
    def __init__(self):
        """Initialize the test framework following the bias detection methodology."""
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
Sei un valutatore esperto di sistemi AI per l'istruzione. Valuta quanto la risposta dell'assistente corrisponde alla risposta attesa.

DOMANDA: {question}

RISPOSTA ASSISTENTE: {assistant_response}

RISPOSTA ATTESA: {expected_answer}

RATIONALE DEL TEST: {rationale}

Fornisci:
1. Un punteggio da 1 a 10 (10 = perfetta corrispondenza con la risposta attesa)
2. Una spiegazione dettagliata delle differenze trovate
3. Identificazione di eventuali informazioni aggiunte non presenti nella risposta attesa
4. Valutazione del rischio di bias/fabrication (BASSO/MEDIO/ALTO)

Rispondi in formato JSON:
{{
    "score": <numero 1-10>,
    "explanation": "<spiegazione dettagliata>",
    "missing_info": ["<informazioni mancanti>"],
    "added_info": ["<informazioni aggiunte non documentate>"],
    "bias_risk": "<BASSO/MEDIO/ALTO>",
    "summary": "<riassunto valutazione in 1-2 frasi>"
}}
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-5",  # Using GPT-5 as specified in methodology
                messages=[
                    {"role": "system", "content": "Sei un valutatore esperto di sistemi AI educativi. Rispondi sempre in formato JSON valido."},
                    {"role": "user", "content": evaluation_prompt}
                ],
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
                    "bias_risk": "ALTO",
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

    def run_certification_tests(self):
        """Run certification-specific bias detection tests."""
        print("🔍 Running Certification Bias Detection Tests")
        print("=" * 50)
        
        # Extended test cases - original 4 + 4 new questions following our methodology
        test_cases = [
            # Original problematic scenarios
            {
                "id": "1year_certification_embedded",
                "question": "Does the 1-year Data Science and AI program curriculum cover content to provide further certifications like AWS Certified Data Engineer, AWS Certified Machine Learning, or Microsoft Azure?",
                "expected_answer": """The Data Science and AI 1-Year Program includes 4 embedded certifications throughout the curriculum:
• W3Schools SQL Certificate (Module 2)
• Tableau Certified Data Analyst (Module 4) 
• IBM Generative AI for Data Analyst Specialization (Module 6)
• Choice between Google Advanced Data Analytics Professional Certificate or Artificial Intelligence Foundation by The Cloud Credential Council (End of Module 7)

The program includes training with AWS and Azure cloud platforms which provides foundational skills, but specific preparation for AWS Certified Data Engineer or AWS Certified Machine Learning certifications isn't explicitly documented in the curriculum.""",
                "rationale": "Test if assistant finds the specific embedded certification schedule and doesn't mix with bootcamp certifications or mention irrelevant certifications from other programs."
            },
            {
                "id": "certification_path_followup",
                "question": "But there is a certification path embedded in the course, no?",
                "expected_answer": """Yes, the Data Science and AI 1-Year Program has a structured certification path with 4 certifications embedded throughout the curriculum:
• W3Schools SQL Certificate during Module 2 (1 week preparation)
• Tableau Certified Data Analyst during Module 4 (1 week preparation)  
• IBM Generative AI for Data Analyst Specialization during Module 6 (1/2 week preparation)
• Choice between Google Advanced Data Analytics Professional Certificate or Artificial Intelligence Foundation by The Cloud Credential Council at the end of Module 7 (2 weeks preparation)

These are spaced out to allow for progressive knowledge building with dedicated study periods.""",
                "rationale": "Test context awareness and ability to provide detailed embedded certification information without cross-program contamination."
            },
            {
                "id": "cybersecurity_isolation",
                "question": "What certifications are available for the Cybersecurity bootcamp?",
                "expected_answer": """The Cybersecurity bootcamp offers these certification options:
• CompTIA Security Plus
• ISACA Cybersecurity Fundamentals Certificate

Graduates can choose one paid certification from these options. The curriculum is designed to cover more than 75% of CompTIA Security+ certification content with a structured preparation scheme.""",
                "rationale": "Test that Cybersecurity certifications remain isolated and don't get mixed with Data Science program certifications."
            },
            {
                "id": "program_disambiguation", 
                "question": "What's the difference in certification paths between the Data Science bootcamp and the 1-year Data Science program?",
                "expected_answer": """The certification paths differ significantly:

Data Science & Machine Learning bootcamp (400 hours):
• Graduates choose ONE paid certification from: AWS AI Practitioner OR Artificial Intelligence Foundation by The Cloud Credential Council

Data Science and AI 1-Year Program Germany (1,582 hours):
• 4 embedded certifications throughout the curriculum: W3Schools SQL Certificate, Tableau Certified Data Analyst, IBM Generative AI for Data Analyst Specialization, and choice between Google Advanced Data Analytics Professional Certificate or Artificial Intelligence Foundation by The Cloud Credential Council
• These are spaced across different modules with dedicated study periods""",
                "rationale": "Test clear program disambiguation and accurate representation of each program's certification offerings without cross-contamination."
            },
            # New questions to test search accuracy
            {
                "id": "direct_certification_lookup",
                "question": "Can you tell me exactly what certifications are included in the Data Science and AI 1-Year Program and when they happen during the course?",
                "expected_answer": """According to the Certifications document, the Data Science and AI 1-Year Program includes these certifications:

Module 2 (Data Engineering): W3Schools SQL Certificate (1 week preparation)
Module 4 (Data Visualization): Tableau Certified Data Analyst (1 week preparation)  
Module 6 (Gen AI): IBM Generative AI for Data Analyst Specialization (1/2 week preparation)
End of Module 7: Students choose between Google Advanced Data Analytics Professional Certificate or Artificial Intelligence Foundation by The Cloud Credential Council (2 weeks preparation)

These are spaced out to allow for progressive knowledge building and include dedicated study periods.""",
                "rationale": "Test direct document search ability for 1-year program certification schedule and timing details."
            },
            {
                "id": "bootcamp_certification_rule",
                "question": "How many certifications can bootcamp graduates choose from for each program?",
                "expected_answer": """All bootcamp graduates are entitled to choose one paid certification from the available options for their vertical. Each vertical has specific certification options, and graduates select one paid certification from those available options.""",
                "rationale": "Test understanding of the general bootcamp certification rule from the Certifications document."
            },
            {
                "id": "devops_certification_options",
                "question": "What certification options are available for DevOps bootcamp graduates?",
                "expected_answer": """DevOps bootcamp graduates can choose one paid certification from these options:
• AWS Certified Solutions Architect – Associate
• Microsoft Certified: Azure Administrator Associate""",
                "rationale": "Test ability to find specific vertical certifications in the Certifications document without fabrication."
            },
            {
                "id": "web_dev_certification_simple",
                "question": "What certifications can Web Development bootcamp students get?",
                "expected_answer": """Web Development bootcamp graduates can choose one paid certification from these options:
• Node.js Application Developer Certification (OpenJS Foundation)
• MongoDB Developer Certification (MongoDB University)""",
                "rationale": "Test simple lookup of Web Development certifications without mixing with other program information."
            }
        ]
        
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
        
        return results

def main():
    """Main test execution following the bias detection methodology."""
    try:
        # Initialize test framework
        test_framework = CertificationTestFramework()
        
        # Run certification tests
        results = test_framework.run_certification_tests()
        
        # Analyze results
        scores = [result['evaluation'].get('score', 0) for result in results]
        avg_score = sum(scores) / len(scores) if scores else 0
        high_bias_count = sum(1 for result in results if result['evaluation'].get('bias_risk') == 'ALTO')
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") 
        results_file = f"tests/results/certification_bias_detection_{timestamp}.json"
        
        os.makedirs("tests/results", exist_ok=True)
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'test_type': 'certification_bias_detection',
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
            print(f"\n✅ CERTIFICATION TESTS PASSED!")
            print("Prompt improvements are working effectively.")
        else:
            print(f"\n❌ CERTIFICATION TESTS NEED IMPROVEMENT")
            print("Need to iterate on the prompt.")
        
        return success, avg_score, results
        
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        return False, 0, []

if __name__ == "__main__":
    success, score, results = main()
    sys.exit(0 if success else 1)
