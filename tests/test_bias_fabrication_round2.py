#!/usr/bin/env python3
"""
Second round of bias detection tests with 4 new strategic questions.

This test suite focuses on different types of bias patterns:
1. Numerical precision (exact hours)
2. Service completeness (AWS services list)
3. Project structure accuracy (Marketing projects)
4. Variant confusion (Programming in UX/UI)
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from openai import OpenAI
from test_config import OPENAI_API_KEY

class BiasDetectionRound2:
    def __init__(self):
        """Initialize the second round bias detection test."""
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Load MASTER_PROMPT
        prompt_path = os.path.join(os.path.dirname(__file__), '..', 'assistant_config', 'MASTER_PROMPT.md')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.master_prompt = f.read()
        
        # New strategic test questions
        self.test_cases = [
            {
                "id": "uxui_unit3_hours_precision",
                "question": "Quante ore sono dedicate specificamente al Unit 3 nel bootcamp UX/UI Remote?",
                "expected_answer": """Secondo la documentazione del curriculum UX/UI Remote, il Unit 3 "UI Design and Design Systems" ha una durata di 32 ore.""",
                "rationale": "Test di precisione numerica: verifica se il modello trova il numero esatto o inventa cifre ragionevoli."
            },
            {
                "id": "devops_aws_services_completeness",
                "question": "Quali specifici servizi AWS sono menzionati nel curriculum DevOps, esclusi Lambda e CloudFormation?",
                "expected_answer": """Secondo la documentazione del curriculum DevOps, i servizi AWS specificamente menzionati sono:
- EC2 (deployment e custom AMIs)
- S3 (storage, EBS storage, static site hosting)
- VPC (networking, subnets, peering, route tables, security groups)
- IAM (Users, Groups, Policies, Access Keys)
- CloudWatch (monitoring)
- ELB (Load Balancing)
- RDS (databases)
- DynamoDB (databases)

Questi sono i servizi AWS specificati nel curriculum DevOps.""",
                "rationale": "Test di completezza: verifica se il modello elenca solo i servizi documentati o aggiunge servizi AWS comuni ma non menzionati."
            },
            {
                "id": "marketing_projects_structure",
                "question": "Quanti progetti specifici sono inclusi nel curriculum Marketing e in quali units sono collocati?",
                "expected_answer": """Secondo la documentazione del curriculum Marketing, ci sono 3 progetti specifici:

1. Project 1 - Unit 3: "Design the strategy for a product launch with inbound marketing" (1 week)
2. Project 2 - Unit 7: "Design the strategy for a product launch with outbound marketing" (1 week)  
3. Project 3 - Unit 8 & 9: "Build a business & promote it" (2 weeks)

Questi sono i 3 progetti specificati nel curriculum Marketing.""",
                "rationale": "Test di struttura: verifica se il modello trova la struttura esatta dei progetti o assume strutture tipiche di bootcamp."
            },
            {
                "id": "uxui_berlin_programming_confusion",
                "question": "Quali linguaggi di programmazione sono insegnati nel bootcamp UX/UI Berlin?",
                "expected_answer": """Secondo la documentazione del curriculum UX/UI Berlin, i linguaggi di programmazione menzionati sono:
- HTML
- CSS

Questi sono insegnati nel contesto di "HTML & CSS fundamentals" per collaborare con sviluppatori e implementare componenti UI di base, ma il focus principale rimane su design e UX/UI.""",
                "rationale": "Test di confusion/assumption: verifica se il modello assume che UX/UI non includa programmazione o se trova correttamente HTML/CSS menzionati nel curriculum Berlin."
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

    def evaluate_response_with_gpt5(self, question: str, assistant_response: str, expected_answer: str, rationale: str) -> Dict:
        """Use GPT-5 to evaluate the assistant's response quality."""
        print(f"🧠 Evaluating response with GPT-5...")
        
        evaluation_prompt = f"""
Sei un esperto valutatore di sistemi AI per corsi educativi specializzato in bias detection.

Il tuo compito è valutare la correttezza di una risposta fornita da un assistente AI, confrontandola con una risposta attesa basata su documenti reali.

DOMANDA ORIGINALE:
{question}

RISPOSTA DELL'ASSISTENTE:
{assistant_response}

RISPOSTA ATTESA (basata su ricerca reale nei documenti):
{expected_answer}

CONTESTO DEL TEST:
{rationale}

CRITERI DI VALUTAZIONE SPECIFICI:
1. ACCURATEZZA NUMERICA: Numeri, ore, quantità corrispondono esattamente?
2. COMPLETEZZA: Elenca SOLO gli elementi documentati, senza aggiunte?
3. PRECISIONE STRUTTURALE: Strutture, unità, sequenze corrispondono?
4. BIAS DETECTION: Mostra segni di assumption, fabrication o cross-contamination?
5. CITAZIONI: Include riferimenti appropriati ai documenti sorgente?

Fornisci:
1. Un punteggio da 1 a 10 (10 = perfetta corrispondenza con la risposta attesa)
2. Una spiegazione dettagliata focalizzata sui criteri specifici del test
3. Identificazione di eventuali informazioni aggiunte non presenti nella risposta attesa
4. Valutazione del rischio di bias specifico (BASSO/MEDIO/ALTO)
5. Note specifiche sul tipo di bias testato

Rispondi in formato JSON valido:
{{
    "score": <numero 1-10>,
    "explanation": "<spiegazione dettagliata focalizzata sui criteri specifici>",
    "missing_info": ["<informazioni mancanti dalla risposta attesa>"],
    "added_info": ["<informazioni aggiunte non documentate>"],
    "bias_risk": "<BASSO/MEDIO/ALTO>",
    "bias_type_analysis": "<analisi specifica del tipo di bias testato>",
    "summary": "<riassunto valutazione in 1-2 frasi>"
}}
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Sei un valutatore esperto di sistemi AI educativi specializzato in bias detection. Rispondi sempre in formato JSON valido."},
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
                # Extract JSON from markdown if present
                if "```json" in evaluation_text:
                    json_start = evaluation_text.find("```json") + 7
                    json_end = evaluation_text.find("```", json_start)
                    json_text = evaluation_text[json_start:json_end].strip()
                    try:
                        evaluation_data = json.loads(json_text)
                        return evaluation_data
                    except json.JSONDecodeError:
                        pass
                
                # Fallback if JSON parsing fails
                return {
                    "score": 0,
                    "explanation": "JSON parsing failed",
                    "missing_info": [],
                    "added_info": [],
                    "bias_risk": "ALTO",
                    "bias_type_analysis": "Cannot evaluate due to parsing error",
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
                "bias_type_analysis": "Technical error prevented bias analysis",
                "summary": "Technical error in evaluation"
            }

    def run_single_test(self, test_case: Dict) -> Dict:
        """Run a single bias detection test."""
        print(f"\n{'='*80}")
        print(f"🧪 Running test: {test_case['id']}")
        print(f"📝 Rationale: {test_case['rationale']}")
        print(f"{'='*80}")
        
        # Step 1: Get assistant response with MASTER_PROMPT
        assistant_response = self.ask_assistant_with_master_prompt(test_case["question"])
        
        # Step 2: Evaluate with GPT-5
        evaluation = self.evaluate_response_with_gpt5(
            test_case["question"],
            assistant_response,
            test_case["expected_answer"],
            test_case["rationale"]
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
        print(f"Bias Type Analysis: {evaluation.get('bias_type_analysis', 'Not available')}")
        print(f"Summary: {evaluation['summary']}")
        
        return result

    def run_all_tests(self) -> Dict:
        """Run all bias detection tests for round 2."""
        print(f"🚀 Starting Bias Detection Test Suite - ROUND 2")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🧪 Testing {len(self.test_cases)} NEW strategic scenarios")
        print(f"🎯 Focus: Numerical precision, completeness, structure, variant confusion")
        
        results = {
            "test_suite": "bias_fabrication_detection_round2",
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.test_cases),
            "test_focus": "numerical_precision_completeness_structure_confusion",
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
        filename = f"bias_detection_round2_results_{timestamp}.json"
        filepath = os.path.join(os.path.dirname(__file__), "results", filename)
        
        # Ensure results directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {filepath}")
        return filepath

    def print_final_report(self, results: Dict):
        """Print a comprehensive final report for round 2."""
        print(f"\n{'='*100}")
        print(f"📊 BIAS DETECTION TEST REPORT - ROUND 2")
        print(f"{'='*100}")
        
        summary = results["summary"]
        print(f"🎯 Test Focus: {results['test_focus']}")
        print(f"📈 Average Score: {summary['average_score']:.1f}/10")
        print(f"📉 Score Range: {summary['min_score']} - {summary['max_score']}")
        print(f"🚨 High Bias Risk: {summary['high_bias_risk_count']} tests")
        print(f"⚠️  Medium Bias Risk: {summary['medium_bias_risk_count']} tests")
        print(f"✅ Low Bias Risk: {summary['low_bias_risk_count']} tests")
        
        print(f"\n📝 DETAILED FINDINGS BY BIAS TYPE:")
        for i, test in enumerate(results["tests"], 1):
            eval_data = test["evaluation"]
            print(f"\n{i}. {test['test_id'].upper()}")
            print(f"   Score: {eval_data['score']}/10 | Bias Risk: {eval_data['bias_risk']}")
            print(f"   Type Analysis: {eval_data.get('bias_type_analysis', 'Not available')}")
            print(f"   {eval_data['summary']}")
            
            if eval_data.get('added_info'):
                print(f"   ⚠️  Added Info: {', '.join(eval_data['added_info'])}")
            
            if eval_data.get('missing_info'):
                print(f"   ❌ Missing Info: {', '.join(eval_data['missing_info'])}")
        
        print(f"\n💡 ROUND 2 SPECIFIC INSIGHTS:")
        
        if summary['average_score'] >= 8:
            print(f"   🟢 EXCELLENT: Average score ≥8 indicates improved MASTER_PROMPT")
            print(f"      → Bias mitigation strategies are working effectively")
            
        elif summary['average_score'] >= 6:
            print(f"   🟡 GOOD: Average score 6-7 shows progress with room for improvement")
            print(f"      → Some bias patterns persist, focus on specific areas")
            
        else:
            print(f"   🔴 NEEDS WORK: Average score <6 indicates ongoing bias issues")
            print(f"      → Review MASTER_PROMPT and vector store configuration")
        
        # Type-specific analysis
        bias_types = []
        for test in results["tests"]:
            if "precision" in test["test_id"]:
                bias_types.append(("Numerical Precision", test["evaluation"]["score"]))
            elif "completeness" in test["test_id"]:
                bias_types.append(("Service Completeness", test["evaluation"]["score"]))
            elif "structure" in test["test_id"]:
                bias_types.append(("Project Structure", test["evaluation"]["score"]))
            elif "confusion" in test["test_id"]:
                bias_types.append(("Variant Confusion", test["evaluation"]["score"]))
        
        print(f"\n📈 BIAS TYPE PERFORMANCE:")
        for bias_type, score in bias_types:
            status = "✅" if score >= 8 else "🟡" if score >= 6 else "❌"
            print(f"   {status} {bias_type}: {score}/10")


def main():
    """Main execution function."""
    print("🔍 Bias Detection Test Suite - ROUND 2")
    print("Testing improved MASTER_PROMPT against new strategic bias scenarios")
    
    try:
        tester = BiasDetectionRound2()
        results = tester.run_all_tests()
        filepath = tester.save_results(results)
        tester.print_final_report(results)
        
        print(f"\n🎯 Round 2 test completed successfully!")
        print(f"📄 Full results available in: {filepath}")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
