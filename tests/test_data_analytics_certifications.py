#!/usr/bin/env python3

"""
Test for Data Analytics Certifications Question
Tests the assistant's ability to provide accurate information about certifications
offered in data analytics programs.
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
    Use GPT-4o to judge the quality of the response
    """
    try:
        import openai
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        judge_prompt = f"""
You are an expert judge evaluating an AI assistant's response. Please evaluate the following response based on the criteria provided.

TEST TYPE: {test_type}
CRITERIA: {criteria}

RESPONSE TO EVALUATE:
{response}

Please provide your evaluation in the following JSON format:
{{
    "score": <number from 0-10>,
    "reasoning": "<detailed explanation of your scoring>",
    "bias_risk": "<BASSO/MEDIO/ALTO>",
    "strengths": ["<list of strengths>"],
    "weaknesses": ["<list of weaknesses>"],
    "improvements": ["<suggested improvements>"]
}}

Scoring Guidelines:
- 10: Perfect response, meets all criteria
- 8-9: Very good response with minor issues
- 6-7: Good response with some problems
- 4-5: Poor response with significant issues
- 1-3: Very poor response with major problems
- 0: Complete failure or technical error

Bias Risk Assessment:
- BASSO: Low risk of bias, response is well-balanced
- MEDIO: Medium risk of bias, some potential issues
- ALTO: High risk of bias, significant concerns

Focus on accuracy, completeness, source citation, and factual correctness.
"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": judge_prompt}],
            temperature=0.1,
            max_tokens=1000
        )
        
        judge_result = json.loads(response.choices[0].message.content)
        return judge_result
        
    except Exception as e:
        return {
            "score": 0,
            "reasoning": f"Judge evaluation failed: {e}",
            "bias_risk": "ALTO",
            "strengths": [],
            "weaknesses": ["Judge evaluation failed"],
            "improvements": ["Fix judge evaluation system"]
        }

def test_data_analytics_certifications():
    """Test the assistant's response to data analytics certifications question"""
    
    print("=" * 80)
    print("TESTING: Data Analytics Certifications Question")
    print("=" * 80)
    
    # Initialize pipeline
    try:
        pipeline = initialize_pipeline()
        print("✓ Pipeline initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize pipeline: {e}")
        return
    
    # Test query
    test_query = "What are the certifications offered in data analytics?"
    
    print(f"\nQuery: {test_query}")
    print("-" * 80)
    
    try:
        # Process the query
        start_time = time.time()
        result = pipeline.process_query(test_query)
        end_time = time.time()
        
        response_time = end_time - start_time
        print(f"Response time: {response_time:.2f} seconds")
        
        # Display the response
        response_text = result.get('response', 'No response generated')
        print(f"\nResponse:\n{response_text}")
        
        # Display validation metrics
        validation = result.get('validation', {})
        print(f"\nValidation Metrics:")
        print(f"  Confidence: {validation.get('confidence', 'N/A')}")
        print(f"  Source Count: {validation.get('source_count', 'N/A')}")
        print(f"  Validation Score: {validation.get('validation_score', 'N/A')}")
        
        # Judge the response
        print(f"\n" + "=" * 80)
        print("JUDGE EVALUATION")
        print("=" * 80)
        
        criteria = """
        - Response should provide specific information about certifications available in data analytics programs
        - Should cite sources from Ironhack's curriculum materials
        - Should be accurate and factual
        - Should be complete and comprehensive
        - Should maintain a professional, sales-appropriate tone
        """
        
        expected_elements = [
            "Specific certification names",
            "Source citations",
            "Accurate information about data analytics programs",
            "Professional tone"
        ]
        
        judge_result = judge_response(
            response_text, 
            "Data Analytics Certifications", 
            criteria, 
            expected_elements
        )
        
        print(f"Judge Score: {judge_result['score']}/10")
        print(f"Bias Risk: {judge_result['bias_risk']}")
        print(f"Reasoning: {judge_result['reasoning']}")
        
        if judge_result['strengths']:
            print(f"Strengths: {', '.join(judge_result['strengths'])}")
        
        if judge_result['weaknesses']:
            print(f"Weaknesses: {', '.join(judge_result['weaknesses'])}")
        
        if judge_result['improvements']:
            print(f"Improvements: {', '.join(judge_result['improvements'])}")
        
        # Save results
        results = {
            "test_name": "Data Analytics Certifications Test",
            "timestamp": datetime.now().isoformat(),
            "query": test_query,
            "response": response_text,
            "response_time": response_time,
            "validation": validation,
            "judge_result": judge_result
        }
        
        # Create results directory if it doesn't exist
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"data_analytics_certifications_test_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✓ Results saved to: {results_file}")
        
        # Final assessment
        print(f"\n" + "=" * 80)
        print("FINAL ASSESSMENT")
        print("=" * 80)
        
        if judge_result['score'] >= 8:
            print("✓ PASS: Response meets quality standards")
        elif judge_result['score'] >= 6:
            print("⚠ PARTIAL: Response has some issues but is acceptable")
        else:
            print("✗ FAIL: Response does not meet quality standards")
        
        if judge_result['bias_risk'] == 'ALTO':
            print("⚠ HIGH BIAS RISK: Response may contain biased or inaccurate information")
        elif judge_result['bias_risk'] == 'MEDIO':
            print("⚠ MEDIUM BIAS RISK: Response has some potential bias issues")
        else:
            print("✓ LOW BIAS RISK: Response appears balanced and accurate")
        
        return judge_result['score'] >= 6 and judge_result['bias_risk'] != 'ALTO'
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_data_analytics_certifications()
    sys.exit(0 if success else 1)
