#!/usr/bin/env python3

"""
Test script to debug the Data Analytics vs Data Science duration comparison issue
"""

import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment
load_dotenv()

# Set mock Slack environment variables
os.environ['SLACK_BOT_TOKEN'] = 'xoxb-test-token-for-testing'
os.environ['SLACK_SIGNING_SECRET'] = 'test-signing-secret-for-testing'

def test_duration_comparison():
    """Test the specific duration comparison issue"""
    try:
        import openai
        from src.app_custom_rag import CustomRAGPipeline
        
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        vector_store_id = os.getenv('OPENAI_VECTOR_STORE_ID')
        
        with open('assistant_config/MASTER_PROMPT.md', 'r') as f:
            master_prompt = f.read()
        
        pipeline = CustomRAGPipeline(client, vector_store_id, master_prompt)
        
        query = "What's the difference between Data Analytics and Data Science bootcamps?"
        print(f"Query: {query}")
        print("=" * 60)
        
        # Test retrieval
        print("1. Testing document retrieval...")
        retrieved_docs, sources = pipeline.retrieve_documents(query)
        print(f"   Retrieved {len(retrieved_docs)} documents from {len(sources)} sources")
        print(f"   Sources: {sources}")
        
        # Check if we have both Data Analytics and Data Science documents
        has_data_analytics = any('Data Analytics' in source for source in sources)
        has_data_science = any('Data Science' in source for source in sources)
        
        print(f"   Has Data Analytics: {has_data_analytics}")
        print(f"   Has Data Science: {has_data_science}")
        
        # Check content for duration information
        print("\n2. Checking duration information in retrieved content...")
        for i, doc in enumerate(retrieved_docs[:3]):  # Check first 3 docs
            print(f"   Doc {i+1}: {doc[:200]}...")
            if '360' in doc:
                print(f"      -> Contains 360 hours")
            if '400' in doc:
                print(f"      -> Contains 400 hours")
        
        # Test full process
        print("\n3. Testing full process...")
        result = pipeline.process_query(query)
        response = result['response']
        
        print(f"   Response: {response}")
        
        # Check for specific duration mentions
        if "360" in response and "400" in response:
            print("   ✅ Both durations mentioned")
        elif "360" in response:
            print("   ⚠️  Only 360h mentioned")
        elif "400" in response:
            print("   ⚠️  Only 400h mentioned")
        else:
            print("   ❌ Neither duration clearly mentioned")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_duration_comparison()
