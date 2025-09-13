#!/usr/bin/env python3

"""
Simple test to check if certifications document can be found
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

def test_simple_cert_query():
    """Test simple certification query"""
    
    try:
        from src.app_custom_rag import CustomRAGPipeline
        import openai
        
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        vector_store_id = os.getenv('OPENAI_VECTOR_STORE_ID')
        
        with open('assistant_config/MASTER_PROMPT.md', 'r') as f:
            master_prompt = f.read()
        
        pipeline = CustomRAGPipeline(client, vector_store_id, master_prompt)
        
        # Test simple certification query
        test_query = "certifications"
        
        print(f"Testing simple query: {test_query}")
        
        # Test the expansion
        expanded = pipeline._expand_query_for_retrieval(test_query)
        print(f"Expanded query: {expanded}")
        
        # Test retrieval directly
        docs, filenames = pipeline.retrieve_documents(test_query)
        print(f"Retrieved {len(docs)} documents from {len(filenames)} files")
        print(f"Files: {filenames}")
        
        if docs:
            print(f"First doc preview: {docs[0][:200]}...")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_cert_query()
