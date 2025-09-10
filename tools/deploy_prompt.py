#!/usr/bin/env python3
"""
Deploy the enhanced V6 prompt to the OpenAI assistant.
This actually updates the assistant's instructions via API.
"""

import openai
import os
import sys

# Load environment variables manually
def load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

load_env_file()

def read_v6_prompt():
    """Read the V6 enhanced prompt"""
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'development', 'MASTER_PROMPT_V6_ENHANCED_TOOLS.md')
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

def deploy_prompt_to_assistant():
    """Deploy the V6 prompt to the OpenAI assistant"""
    try:
        assistant_id = os.environ["OPENAI_ASSISTANT_ID"]
        openai.api_key = os.environ["OPENAI_API_KEY"]
        
        print(f"Deploying V6 prompt to assistant: {assistant_id}")
        
        # Read the enhanced V6 prompt
        v6_prompt = read_v6_prompt()
        
        # Update the assistant with the new prompt
        updated_assistant = openai.beta.assistants.update(
            assistant_id=assistant_id,
            instructions=v6_prompt
        )
        
        print("✅ Successfully updated assistant with V6 enhanced prompt!")
        print(f"Assistant name: {updated_assistant.name}")
        print(f"Model: {updated_assistant.model}")
        print(f"Instructions length: {len(updated_assistant.instructions)} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ Error deploying prompt: {e}")
        return False

def main():
    """Main deployment function"""
    print("OpenAI Assistant Prompt Deployment")
    print("="*50)
    
    success = deploy_prompt_to_assistant()
    
    if success:
        print("\n🚀 Deployment completed successfully!")
        print("The Product Wizard assistant now has the enhanced V6 prompt.")
    else:
        print("\n💥 Deployment failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
