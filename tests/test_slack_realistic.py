#!/usr/bin/env python3
"""
Simple realistic Slack thread test
"""

import os
import openai
from dotenv import load_dotenv

load_dotenv()

def test_realistic_slack_thread():
    client = openai.OpenAI(api_key=os.environ['OPENAI_API_KEY'])
    vector_store_id = os.environ.get('OPENAI_VECTOR_STORE_ID', 'vs_68c14625e8d88191a27acb8a3845a706')

    # Load master prompt
    with open('../assistant_config/MASTER_PROMPT.md', 'r') as f:
        master_prompt = f.read()

    print('💬 REALISTIC SLACK THREAD SIMULATION')
    print('=' * 60)
    print('Simulating how a sales prospect would actually chat with Product Wizard')
    print('=' * 60)

    # Realistic conversation that matches your sales use case
    conversation = [
        'What programming languages are taught in the Web Development bootcamp?',
        'Do both Remote and Berlin variants cover the same languages?', 
        'What about SQL? I heard some bootcamps include database work.',
        'If I take the Berlin version, what extra things do I get for the longer duration?'
    ]

    previous_response_id = None
    success_count = 0

    for i, message in enumerate(conversation, 1):
        print(f'\n👤 Prospect: {message}')
        
        # Prepare request exactly like your Slack app does
        request_params = {
            'model': 'gpt-4o',
            'input': message,
            'instructions': master_prompt,
            'tools': [{
                'type': 'file_search',
                'vector_store_ids': [vector_store_id]
            }]
        }
        
        # Add context from previous message (this is the key part!)
        if previous_response_id:
            request_params['previous_response_id'] = previous_response_id
        
        print('🤖 Product Wizard: ', end='', flush=True)
        
        try:
            response = client.responses.create(**request_params)
            
            # Extract response (same logic as your app)
            assistant_message = 'No response generated'
            for output_item in response.output:
                if hasattr(output_item, 'type') and output_item.type == 'message':
                    if hasattr(output_item, 'content') and len(output_item.content) > 0:
                        content = output_item.content[0]
                        if hasattr(content, 'text'):
                            assistant_message = content.text
                            break
            
            # Update context for next message
            previous_response_id = response.id
            
            # Show response (truncated for readability)
            if len(assistant_message) > 200:
                print(assistant_message[:200] + '...')
            else:
                print(assistant_message)
            
            # Quick quality check
            print(f'   ℹ️  Length: {len(assistant_message)} chars | Context ID: {response.id[:12]}...')
            
            # Check if response is meaningful
            if len(assistant_message) > 50 and 'curriculum' in assistant_message.lower():
                success_count += 1
                print('   ✅ Quality check passed')
            else:
                print('   ⚠️ Quality check marginal')
            
        except Exception as e:
            print(f'❌ Error: {e}')
            break

    print(f'\n📊 FINAL RESULTS:')
    print(f'Successful responses: {success_count}/{len(conversation)}')
    print(f'Success rate: {success_count/len(conversation)*100:.1f}%')
    
    if success_count >= len(conversation) * 0.75:
        print('✅ SLACK THREAD SIMULATION PASSED!')
        print('Your Responses API handles threaded conversations well!')
        return True
    else:
        print('⚠️ Some issues detected in conversation flow')
        return False

if __name__ == "__main__":
    success = test_realistic_slack_thread()
    exit(0 if success else 1)
