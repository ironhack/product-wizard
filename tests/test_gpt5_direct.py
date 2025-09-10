#!/usr/bin/env python3
"""
Test GPT-5 directly via Chat API with document content
"""

import openai
import os

# API Configuration
from test_config import OPENAI_API_KEY

def test_gpt5_with_document_content():
    """Test GPT-5 directly with document content to see fabrication resistance"""
    
    print("🧪 Testing GPT-5 via Chat API")
    print("=" * 40)
    
    # Load some curriculum content to provide as context
    try:
        with open('/Users/ruds/Documents/Ironhack-Edu/product-wizard/database_txt/DevOps_bootcamp_2025_07.txt', 'r') as f:
            devops_content = f.read()[:3000]  # First 3000 chars
    except:
        print("❌ Could not load DevOps content")
        return
    
    try:
        with open('/Users/ruds/Documents/Ironhack-Edu/product-wizard/MASTER_PROMPT_V4.md', 'r') as f:
            v4_prompt = f.read()
    except:
        print("❌ Could not load V4 prompt")
        return
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    # Test question
    test_question = "Can you give me the full list of tools used in the DevOps bootcamp? grouped into four categories."
    
    # Construct messages
    system_message = f"""
{v4_prompt}

You have access to the following curriculum document:

--- DEVOPS CURRICULUM DOCUMENT ---
{devops_content}
--- END DOCUMENT ---

Use ONLY information from this document to answer questions about the DevOps bootcamp.
"""
    
    try:
        print("🚀 Testing GPT-5...")
        
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": test_question}
            ],
            temperature=0.1  # Low temperature for consistency
        )
        
        gpt5_response = response.choices[0].message.content
        
        print(f"✅ GPT-5 Response ({len(gpt5_response)} chars):")
        print("-" * 50)
        print(gpt5_response)
        print("-" * 50)
        
        # Analyze for fabrications
        response_lower = gpt5_response.lower()
        fabrication_traps = ["gcp", "google cloud platform", "jenkins", "circleci"]
        fabrications = [trap for trap in fabrication_traps if trap in response_lower]
        
        print(f"🔍 Analysis:")
        if fabrications:
            print(f"❌ Fabrications detected: {fabrications}")
        else:
            print(f"✅ No fabrications detected")
        
        # Check accuracy
        accurate_tools = ["aws", "azure", "terraform", "docker", "kubernetes", "github actions", "prometheus", "grafana", "ansible"]
        found_tools = [tool for tool in accurate_tools if tool in response_lower]
        print(f"✅ Accurate tools found: {len(found_tools)}/9")
        print(f"   Tools: {found_tools}")
        
        return {
            "model": "gpt-5",
            "response": gpt5_response,
            "fabrications": fabrications,
            "accurate_tools": found_tools,
            "response_length": len(gpt5_response)
        }
        
    except Exception as e:
        print(f"❌ Error testing GPT-5: {e}")
        return None

def compare_with_current_model():
    """Compare GPT-5 with current gpt-4.1 using same content"""
    
    print("\n🔄 Comparing with GPT-4.1...")
    
    # Load content
    try:
        with open('/Users/ruds/Documents/Ironhack-Edu/product-wizard/database_txt/DevOps_bootcamp_2025_07.txt', 'r') as f:
            devops_content = f.read()[:3000]
        with open('/Users/ruds/Documents/Ironhack-Edu/product-wizard/MASTER_PROMPT_V4.md', 'r') as f:
            v4_prompt = f.read()
    except:
        print("❌ Could not load content")
        return
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    test_question = "Can you give me the full list of tools used in the DevOps bootcamp? grouped into four categories."
    
    system_message = f"""
{v4_prompt}

You have access to the following curriculum document:

--- DEVOPS CURRICULUM DOCUMENT ---
{devops_content}
--- END DOCUMENT ---

Use ONLY information from this document to answer questions about the DevOps bootcamp.
"""
    
    models_to_compare = ["gpt-5", "gpt-4.1", "gpt-4o"]
    results = {}
    
    for model in models_to_compare:
        print(f"\n🧪 Testing {model}...")
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": test_question}
                ],
                temperature=0.1
            )
            
            model_response = response.choices[0].message.content
            
            # Quick analysis
            response_lower = model_response.lower()
            fabrication_traps = ["gcp", "google cloud platform", "jenkins"]
            fabrications = [trap for trap in fabrication_traps if trap in response_lower]
            
            accurate_tools = ["aws", "azure", "terraform", "docker", "kubernetes", "github actions", "prometheus", "grafana", "ansible"]
            found_tools = [tool for tool in accurate_tools if tool in response_lower]
            
            results[model] = {
                "response_length": len(model_response),
                "fabrications": fabrications,
                "accurate_tools_count": len(found_tools),
                "response_preview": model_response[:200] + "..." if len(model_response) > 200 else model_response
            }
            
            print(f"   ✅ Length: {len(model_response)} chars")
            print(f"   🎯 Fabrications: {len(fabrications)}")
            print(f"   ✅ Accurate tools: {len(found_tools)}/9")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results[model] = {"error": str(e)}
    
    # Generate comparison
    print(f"\n{'='*50}")
    print("📊 DIRECT MODEL COMPARISON")
    print("=" * 50)
    
    for model, result in results.items():
        if "error" not in result:
            print(f"\n{model}:")
            print(f"   Response Length: {result['response_length']} chars")
            print(f"   Fabrications: {len(result['fabrications'])}")
            print(f"   Accurate Tools: {result['accurate_tools_count']}/9")
            print(f"   Preview: {result['response_preview']}")
            
            if result['fabrications']:
                print(f"   ❌ Fabricated: {result['fabrications']}")
        else:
            print(f"\n{model}: ❌ {result['error']}")
    
    # Recommendation
    valid_results = {k: v for k, v in results.items() if "error" not in v}
    if valid_results:
        best_model = min(valid_results.items(), key=lambda x: len(x[1]['fabrications']))
        print(f"\n🏆 BEST MODEL: {best_model[0]}")
        print(f"   Reason: {len(best_model[1]['fabrications'])} fabrications, {best_model[1]['accurate_tools_count']} accurate tools")

def main():
    print("🔬 GPT-5 Direct Testing")
    print("=" * 30)
    
    # Test GPT-5 directly
    gpt5_result = test_gpt5_with_document_content()
    
    # Compare models
    compare_with_current_model()
    
    print(f"\n✅ Testing complete!")

if __name__ == "__main__":
    main()
