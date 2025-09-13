#!/usr/bin/env python3

"""
Debug test for second retrieval
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment
load_dotenv()

# Set mock Slack environment variables
os.environ['SLACK_BOT_TOKEN'] = 'xoxb-test-token-for-testing'
os.environ['SLACK_SIGNING_SECRET'] = 'test-signing-secret-for-testing'

def test_second_retrieval():
    """Test the second retrieval directly"""
    
    try:
        from src.app_custom_rag import CustomRAGPipeline
        import openai
        
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        vector_store_id = os.getenv('OPENAI_VECTOR_STORE_ID')
        
        with open('assistant_config/MASTER_PROMPT.md', 'r') as f:
            master_prompt = f.read()
        
        pipeline = CustomRAGPipeline(client, vector_store_id, master_prompt)
        
        # Test the exact query that's failing in the second retrieval
        test_query = "What are the certifications offered in data analytics?"
        
        print(f"Testing second retrieval query: {test_query}")
        
        # Test the enhance_query_with_context method
        enhanced = pipeline._enhance_query_with_context(test_query, None)
        print(f"Enhanced query: {enhanced}")
        
        # Test the retrieval instructions
        instructions = pipeline._get_retrieval_instructions(enhanced)
        print(f"Instructions: {instructions[:100]}...")
        
        # Test the retrieval directly
        docs, filenames = pipeline.retrieve_documents_original(test_query)
        print(f"Retrieved {len(docs)} documents from {len(filenames)} files")
        print(f"Files: {filenames}")
        
        if docs:
            print(f"First doc preview: {docs[0][:200]}...")
        else:
            print("No documents retrieved!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_second_retrieval()
