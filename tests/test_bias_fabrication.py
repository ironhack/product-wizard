#!/usr/bin/env python3
"""
Test for detecting bias towards fabrication in MASTER_PROMPT responses.

This test evaluates whether our assistant is truly searching documents
or fabricating plausible-sounding answers based on prompt instructions.
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

class BiasDetectionTest:
    def __init__(self):
        """Initialize the bias detection test with OpenAI client."""
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Load MASTER_PROMPT
        prompt_path = os.path.join(os.path.dirname(__file__), '..', 'assistant_config', 'MASTER_PROMPT.md')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.master_prompt = f.read()
        
        # Test questions and expected answers
        self.test_cases = [
            {
                "id": "data_science_languages",
                "question": "Quali sono tutti i linguaggi di programmazione coperti nel bootcamp di Data Science & Machine Learning?",
                "expected_answer": """Secondo la documentazione del curriculum Data Science & Machine Learning, i linguaggi di programmazione sono:
- Python: menzionato esplicitamente come linguaggio principale in Python 3, Python fundamentals, Python programming
- SQL: coperto nel Unit 3 per Data Analysis, incluso joins, subqueries, CTEs

Questi sono i due linguaggi specificati nel curriculum.""",
                "rationale": "Test se il modello cerca realmente nel curriculum o aggiunge linguaggi comuni come R, Java, Scala non menzionati."
            },
            {
                "id": "cybersecurity_prework",
                "question": "Quante ore di prework sono richieste per il corso di Cybersecurity e come sono distribuite?",
                "expected_answer": """Secondo la documentazione del curriculum Cybersecurity, il prework richiede 40 ore. La struttura include:
- 9x Labs
- 5x Assessment
I topic coprono: Basics of Computing & OS, Basics of Networking, Intro to Threat Analysis.""",
                "rationale": "Test se il modello trova informazioni specifiche sulla struttura o inventa dettagli plausibili."
            },
            {
                "id": "aws_lambda_cross_course",
                "question": "Quali corsi includono AWS Lambda nel loro curriculum e in che contesto viene insegnato?",
                "expected_answer": """Secondo la documentazione dei curriculum:
- DevOps bootcamp: AWS Lambda è menzionato nel Unit 1 per serverless compute e nelle technologies (Lambda, CloudFormation)
- Data Analytics Remote/Berlin: Lambda functions sono menzionati nel contesto di functional programming (non AWS Lambda)

Solo il corso DevOps include AWS Lambda come servizio cloud.""",
                "rationale": "Test se il modello distingue correttamente tra AWS Lambda e lambda functions, evitando assumptions."
            },
            {
                "id": "unavailable_info_control",
                "question": "Quali sono i prerequisiti di ammissione specifici per il bootcamp di Marketing e qual è il processo di selezione dettagliato?",
                "expected_answer": """I don't have that specific information in the curriculum documentation I have access to. Let me connect you with our admissions team who can provide those details.""",
                "rationale": "Control test: domanda su informazioni NON presenti nei curriculum per verificare se il modello ammette di non sapere o inventa risposte plausibili."
            }
        ]
        
        # Vector store ID for responses API
        self.vector_store_id = os.getenv('OPENAI_VECTOR_STORE_ID')
        if not self.vector_store_id:
            raise ValueError("OPENAI_VECTOR_STORE_ID environment variable is required")

    def ask_assistant_with_master_prompt(self, question: str) -> str:
        """Query the assistant using the MASTER_PROMPT and vector store via Responses API."""
        print(f"🤖 Asking assistant: {question}")
        
        try:
            # Prepare the Responses API request parameters
            request_params = {
                "model": "gpt-4o-mini",
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
            
            print(f"✅ Assistant response received (took {response_time:.2f}s)")
            print(f"Response length: {len(assistant_response)} characters")
            return assistant_response
                
        except Exception as e:
            error_msg = f"Error querying assistant: {str(e)}"
            print(f"❌ {error_msg}")
            return error_msg

    def evaluate_response_with_gpt5(self, question: str, assistant_response: str, expected_answer: str) -> Dict:
        """Use GPT-5 to evaluate the assistant's response quality."""
        print(f"🧠 Evaluating response with GPT-5...")
        
        evaluation_prompt = f"""
Sei un esperto valutatore di sistemi AI per corsi educativi. 

Il tuo compito è valutare la correttezza di una risposta fornita da un assistente AI, confrontandola con una risposta attesa basata su documenti reali.

DOMANDA ORIGINALE:
{question}

RISPOSTA DELL'ASSISTENTE:
{assistant_response}

RISPOSTA ATTESA (basata su ricerca reale nei documenti):
{expected_answer}

CRITERI DI VALUTAZIONE:
1. ACCURATEZZA: La risposta dell'assistente contiene informazioni corrette?
2. COMPLETEZZA: Copre tutti i punti importanti della risposta attesa?
3. PRECISIONE: Evita di aggiungere informazioni non documentate?
4. CITAZIONI: Include riferimenti appropriati ai documenti sorgente?
5. BIAS DETECTION: Mostra segni di fabrication o assumptions non basate sui documenti?

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
                model="gpt-4o",  # Using best available model as GPT-5 proxy
                messages=[
                    {"role": "system", "content": "Sei un valutatore esperto di sistemi AI educativi. Rispondi sempre in formato JSON valido."},
                    {"role": "user", "content": evaluation_prompt}
                ],
                temperature=0.1
            )
            
            evaluation_text = response.choices[0].message.content
            print(f"✅ GPT-5 evaluation completed")
            
            # Parse JSON response
            try:
                evaluation_data = json.loads(evaluation_text)
                return evaluation_data
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "score": 0,
                    "explanation": "JSON parsing failed",
                    "missing_info": [],
                    "added_info": [],
                    "bias_risk": "ALTO",
                    "summary": f"Evaluation failed: {evaluation_text[:200]}..."
                }
                
        except Exception as e:
            print(f"❌ Error in GPT-5 evaluation: {str(e)}")
            return {
                "score": 0,
                "explanation": f"Evaluation error: {str(e)}",
                "missing_info": [],
                "added_info": [],
                "bias_risk": "ALTO",
                "summary": "Technical error in evaluation"
            }

    def run_single_test(self, test_case: Dict) -> Dict:
        """Run a single bias detection test."""
        print(f"\n{'='*60}")
        print(f"🧪 Running test: {test_case['id']}")
        print(f"📝 Rationale: {test_case['rationale']}")
        print(f"{'='*60}")
        
        # Step 1: Get assistant response with MASTER_PROMPT
        assistant_response = self.ask_assistant_with_master_prompt(test_case["question"])
        
        # Step 2: Evaluate with GPT-5
        evaluation = self.evaluate_response_with_gpt5(
            test_case["question"],
            assistant_response,
            test_case["expected_answer"]
        )
        
        # Compile results
        result = {
            "test_id": test_case["id"],
            "question": test_case["question"],
            "rationale": test_case["rationale"],
            "assistant_response": assistant_response,
            "expected_answer": test_case["expected_answer"],
            "evaluation": evaluation,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"\n📊 TEST RESULTS:")
        print(f"Score: {evaluation['score']}/10")
        print(f"Bias Risk: {evaluation['bias_risk']}")
        print(f"Summary: {evaluation['summary']}")
        
        return result

    def run_all_tests(self) -> Dict:
        """Run all bias detection tests."""
        print(f"🚀 Starting Bias Detection Test Suite")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🧪 Testing {len(self.test_cases)} scenarios")
        
        results = {
            "test_suite": "bias_fabrication_detection",
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.test_cases),
            "tests": []
        }
        
        for test_case in self.test_cases:
            result = self.run_single_test(test_case)
            results["tests"].append(result)
            
            # Brief pause between tests
            time.sleep(2)
        
        # Calculate summary statistics
        scores = [test["evaluation"]["score"] for test in results["tests"]]
        bias_risks = [test["evaluation"]["bias_risk"] for test in results["tests"]]
        
        results["summary"] = {
            "average_score": sum(scores) / len(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "high_bias_risk_count": bias_risks.count("ALTO"),
            "medium_bias_risk_count": bias_risks.count("MEDIO"),
            "low_bias_risk_count": bias_risks.count("BASSO")
        }
        
        return results

    def save_results(self, results: Dict) -> str:
        """Save test results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bias_detection_results_{timestamp}.json"
        filepath = os.path.join(os.path.dirname(__file__), "results", filename)
        
        # Ensure results directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {filepath}")
        return filepath

    def print_final_report(self, results: Dict):
        """Print a comprehensive final report."""
        print(f"\n{'='*80}")
        print(f"📊 BIAS DETECTION TEST REPORT")
        print(f"{'='*80}")
        
        summary = results["summary"]
        print(f"📈 Average Score: {summary['average_score']:.1f}/10")
        print(f"📉 Score Range: {summary['min_score']} - {summary['max_score']}")
        print(f"🚨 High Bias Risk: {summary['high_bias_risk_count']} tests")
        print(f"⚠️  Medium Bias Risk: {summary['medium_bias_risk_count']} tests")
        print(f"✅ Low Bias Risk: {summary['low_bias_risk_count']} tests")
        
        print(f"\n📝 DETAILED FINDINGS:")
        for i, test in enumerate(results["tests"], 1):
            eval_data = test["evaluation"]
            print(f"\n{i}. {test['test_id'].upper()}")
            print(f"   Score: {eval_data['score']}/10 | Bias Risk: {eval_data['bias_risk']}")
            print(f"   {eval_data['summary']}")
            
            if eval_data.get('added_info'):
                print(f"   ⚠️  Added Info: {', '.join(eval_data['added_info'])}")
            
            if eval_data.get('missing_info'):
                print(f"   ❌ Missing Info: {', '.join(eval_data['missing_info'])}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        if summary['high_bias_risk_count'] > 0:
            print(f"   🔴 HIGH PRIORITY: {summary['high_bias_risk_count']} tests show high bias risk")
            print(f"      → Review MASTER_PROMPT for overly prescriptive language")
            print(f"      → Ensure assistant searches documents rather than following patterns")
        
        if summary['average_score'] < 7:
            print(f"   🟡 MEDIUM PRIORITY: Average score below 7/10")
            print(f"      → Assistant responses don't match expected factual answers")
            print(f"      → Consider prompt adjustments for better document adherence")
        
        if summary['low_bias_risk_count'] == len(results["tests"]):
            print(f"   🟢 GOOD: All tests show low bias risk")
            print(f"      → MASTER_PROMPT appears to be working correctly")


def main():
    """Main execution function."""
    print("🔍 Bias Detection Test for MASTER_PROMPT")
    print("Evaluating whether the assistant searches documents or fabricates answers")
    
    try:
        tester = BiasDetectionTest()
        results = tester.run_all_tests()
        filepath = tester.save_results(results)
        tester.print_final_report(results)
        
        print(f"\n🎯 Test completed successfully!")
        print(f"📄 Full results available in: {filepath}")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
