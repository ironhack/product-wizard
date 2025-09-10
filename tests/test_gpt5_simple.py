#!/usr/bin/env python3
"""
Test GPT-5 with default parameters
"""

import openai

from test_config import OPENAI_API_KEY

def quick_gpt5_test():
    """Quick test of GPT-5 capabilities"""
    
    print("🧪 Quick GPT-5 Test")
    print("=" * 30)
    
    # Load DevOps content
    try:
        with open('/Users/ruds/Documents/Ironhack-Edu/product-wizard/database_txt/DevOps_bootcamp_2025_07.txt', 'r') as f:
            devops_content = f.read()[:2000]  # First 2000 chars
    except:
        print("❌ Could not load content")
        return
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    prompt = f"""Based ONLY on this curriculum document, what tools are used in the DevOps bootcamp?

CURRICULUM DOCUMENT:
{devops_content}

Instructions:
- Only mention tools explicitly listed in the document
- Do NOT add tools like Jenkins, Google Cloud Platform, or other tools not mentioned
- Organize into categories if possible
- Be precise and accurate
"""
    
    models_to_test = ["gpt-5", "gpt-4.1", "gpt-4o"]
    
    for model in models_to_test:
        print(f"\n🔬 Testing {model}:")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = response.choices[0].message.content
            print(f"✅ Response ({len(result)} chars):")
            print("-" * 30)
            print(result[:400] + "..." if len(result) > 400 else result)
            print("-" * 30)
            
            # Quick check for fabrications
            fabrications = []
            response_lower = result.lower()
            traps = ["jenkins", "gcp", "google cloud platform", "circleci"]
            
            for trap in traps:
                if trap in response_lower:
                    fabrications.append(trap)
            
            if fabrications:
                print(f"❌ FABRICATIONS: {fabrications}")
            else:
                print(f"✅ NO FABRICATIONS DETECTED")
            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    quick_gpt5_test()
