#!/usr/bin/env python3
"""
Deploy the current production prompt to the OpenAI assistant.
This reads from assistant_config/MASTER_PROMPT.md and updates the assistant's instructions via API.
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

def read_current_prompt():
    """Read the current production prompt from assistant_config"""
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'assistant_config', 'MASTER_PROMPT.md')
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

def deploy_prompt_to_assistant():
    """Deploy the current prompt to the OpenAI assistant"""
    try:
        assistant_id = os.environ["OPENAI_ASSISTANT_ID"]
        openai.api_key = os.environ["OPENAI_API_KEY"]
        
        print(f"Deploying current prompt to assistant: {assistant_id}")
        
        # Read the current production prompt
        current_prompt = read_current_prompt()
        
        # Update the assistant with the new prompt
        updated_assistant = openai.beta.assistants.update(
            assistant_id=assistant_id,
            instructions=current_prompt
        )
        
        print("✅ Successfully updated assistant with current production prompt!")
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
        print("The Product Wizard assistant now has the current production prompt.")
    else:
        print("\n💥 Deployment failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
