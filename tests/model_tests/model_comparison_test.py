#!/usr/bin/env python3
"""
Test different OpenAI models for fabrication resistance
"""

import openai
import time
import json

# API Configuration
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from test_config import OPENAI_API_KEY
ASSISTANT_ID = "asst_Zm6nYxM5dhXKDgwzz3yVgYdy"

def get_available_models():
    """Check what models are available"""
    print("🔍 Checking available OpenAI models...")
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        models = client.models.list()
        
        # Filter for relevant models
        relevant_models = []
        for model in models.data:
            if any(keyword in model.id.lower() for keyword in ['gpt-4', 'gpt-5']):
                relevant_models.append(model.id)
        
        relevant_models.sort()
        print(f"📋 Available GPT models:")
        for model in relevant_models:
            print(f"   - {model}")
        
        return relevant_models
        
    except Exception as e:
        print(f"❌ Error getting models: {e}")
        return []

def test_model_for_fabrications(model_name):
    """Test a specific model for fabrication resistance"""
    print(f"\n🧪 Testing model: {model_name}")
    print("-" * 50)
    
    # Test question that previously caused fabrications
    test_question = "Can you give me the full list of tools used in the DevOps bootcamp? grouped into four categories."
    
    # Load V4 prompt
    try:
        with open('MASTER_PROMPT_V4.md', 'r') as f:
            v4_prompt = f.read()
    except:
        print("❌ Could not load V4 prompt")
        return None
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Update assistant to use this model
        assistant = client.beta.assistants.update(
            assistant_id=ASSISTANT_ID,
            model=model_name,
            instructions=v4_prompt
        )
        
        print(f"✅ Updated assistant to use {model_name}")
        
        # Wait for update to propagate
        time.sleep(5)
        
        # Create thread and test
        thread = client.beta.threads.create()
        
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=test_question
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
        
        # Wait for completion
        start_time = time.time()
        while run.status in ["queued", "in_progress"]:
            if time.time() - start_time > 120:  # 2 minute timeout
                print(f"⏰ Timeout for {model_name}")
                return None
                
            time.sleep(2)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
        
        if run.status == "completed":
            messages = client.beta.threads.messages.list(thread_id=thread.id)
            response = messages.data[0].content[0].text.value
            
            # Analyze response
            analysis = analyze_model_response(response, model_name)
            
            print(f"📝 Response length: {len(response)} chars")
            print(f"🎯 Fabrication risk: {analysis['fabrication_risk']}")
            print(f"✅ Accurate tools: {len(analysis['accurate_tools'])}")
            print(f"❌ Fabricated tools: {len(analysis['fabricated_tools'])}")
            
            if analysis['fabricated_tools']:
                print(f"   Fabrications: {analysis['fabricated_tools']}")
            
            # Show response preview
            print(f"\n📄 Response preview:")
            print(response[:300] + "..." if len(response) > 300 else response)
            
            return {
                "model": model_name,
                "response": response,
                "analysis": analysis,
                "status": "success"
            }
            
        else:
            print(f"❌ Run failed: {run.status}")
            if hasattr(run, 'last_error') and run.last_error:
                print(f"Error: {run.last_error}")
            return None
            
    except Exception as e:
        print(f"❌ Error testing {model_name}: {e}")
        return None

def analyze_model_response(response, model_name):
    """Analyze response for fabrications and accuracy"""
    response_lower = response.lower()
    
    # Known accurate DevOps tools from curriculum
    accurate_devops_tools = [
        "aws", "azure", "terraform", "ansible", "docker", 
        "kubernetes", "github actions", "prometheus", "grafana"
    ]
    
    # Known fabrication traps that shouldn't appear
    fabrication_traps = [
        "gcp", "google cloud platform", "jenkins", "circleci", 
        "travis ci", "gitlab ci", "bamboo"
    ]
    
    # Analyze
    found_accurate = [tool for tool in accurate_devops_tools if tool in response_lower]
    found_fabricated = [trap for trap in fabrication_traps if trap in response_lower]
    
    # Check for fabrication indicator words
    fabrication_indicators = [
        "typically", "usually", "standard", "common", "about"
    ]
    found_indicators = [ind for ind in fabrication_indicators if ind in response_lower]
    
    # Calculate fabrication risk
    fabrication_score = len(found_fabricated) + len(found_indicators)
    
    return {
        "model": model_name,
        "accurate_tools": found_accurate,
        "fabricated_tools": found_fabricated,
        "fabrication_indicators": found_indicators,
        "fabrication_risk": "HIGH" if fabrication_score > 2 else "MEDIUM" if fabrication_score > 0 else "LOW",
        "accuracy_score": len(found_accurate),
        "fabrication_score": fabrication_score
    }

def compare_models():
    """Compare multiple models for fabrication resistance"""
    print("🚀 OpenAI Model Comparison for Fabrication Resistance")
    print("=" * 70)
    
    # Get available models
    available_models = get_available_models()
    
    if not available_models:
        print("❌ No models available for testing")
        return
    
    # Priority models to test (if available)
    priority_models = [
        "gpt-5",
        "gpt-4.1", 
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-4"
    ]
    
    # Filter to available models
    models_to_test = []
    for priority_model in priority_models:
        matching_models = [m for m in available_models if priority_model in m.lower()]
        if matching_models:
            models_to_test.append(matching_models[0])  # Take first match
    
    # Add any other interesting models
    for model in available_models:
        if model not in models_to_test and len(models_to_test) < 5:  # Limit to 5 tests
            models_to_test.append(model)
    
    print(f"\n🎯 Testing {len(models_to_test)} models:")
    for model in models_to_test:
        print(f"   - {model}")
    
    results = []
    
    for i, model in enumerate(models_to_test, 1):
        print(f"\n{'='*20} Test {i}/{len(models_to_test)} {'='*20}")
        result = test_model_for_fabrications(model)
        
        if result:
            results.append(result)
        
        # Rate limiting between tests
        if i < len(models_to_test):
            print("⏳ Waiting 10 seconds before next test...")
            time.sleep(10)
    
    # Generate comparison report
    generate_model_comparison_report(results)
    
    # Save results
    with open('model_comparison_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return results

def generate_model_comparison_report(results):
    """Generate detailed comparison report"""
    print(f"\n{'='*70}")
    print("📊 MODEL COMPARISON REPORT")
    print("=" * 70)
    
    if not results:
        print("❌ No successful tests to compare")
        return
    
    # Sort by fabrication resistance (lower fabrication score is better)
    results.sort(key=lambda x: (x['analysis']['fabrication_score'], -x['analysis']['accuracy_score']))
    
    print(f"🏆 RANKING (Best to Worst for Fabrication Resistance):")
    print()
    
    for i, result in enumerate(results, 1):
        analysis = result['analysis']
        model = result['model']
        
        print(f"{i}. {model}")
        print(f"   🎯 Fabrication Risk: {analysis['fabrication_risk']}")
        print(f"   ✅ Accurate Tools: {analysis['accuracy_score']}")
        print(f"   ❌ Fabrication Score: {analysis['fabrication_score']}")
        
        if analysis['fabricated_tools']:
            print(f"   🚫 Fabrications: {', '.join(analysis['fabricated_tools'])}")
        
        if analysis['fabrication_indicators']:
            print(f"   ⚠️ Indicators: {', '.join(analysis['fabrication_indicators'])}")
        
        print()
    
    # Recommendation
    best_model = results[0]
    print(f"🎯 RECOMMENDATION:")
    print(f"   Best Model: {best_model['model']}")
    print(f"   Fabrication Risk: {best_model['analysis']['fabrication_risk']}")
    print(f"   Reason: Lowest fabrication score ({best_model['analysis']['fabrication_score']}) with {best_model['analysis']['accuracy_score']} accurate tools")
    
    if best_model['analysis']['fabrication_score'] == 0:
        print(f"   🎉 PERFECT: No fabrications detected!")
    elif best_model['analysis']['fabrication_score'] <= 2:
        print(f"   ✅ GOOD: Minimal fabrication risk")
    else:
        print(f"   ⚠️ CAUTION: Still has fabrication risk")

def main():
    print("🔬 Model Fabrication Resistance Testing")
    print("=" * 50)
    
    results = compare_models()
    
    if results:
        print(f"\n💾 Results saved to: model_comparison_results.json")
    else:
        print("\n❌ No results to save")

if __name__ == "__main__":
    main()
