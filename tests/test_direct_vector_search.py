#!/usr/bin/env python3

"""
Test direct vector store search
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

def test_direct_vector_search():
    """Test direct vector store search"""
    
    try:
        import openai
        
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        vector_store_id = os.getenv('OPENAI_VECTOR_STORE_ID')
        
        # Test direct vector store search
        test_query = "What are the certifications offered in data analytics?"
        
        print(f"Testing direct vector store search for: {test_query}")
        
        # Direct vector store search
        vs = client.vector_stores.search(
            vector_store_id=vector_store_id,
            query=test_query
        )
        
        hits = getattr(vs, "data", []) or []
        print(f"Direct search found {len(hits)} hits")
        
        if hits:
            for i, hit in enumerate(hits[:3]):
                fname = getattr(hit, "filename", "unknown")
                score = float(getattr(hit, "score", 0.0) or 0.0)
                print(f"  {i+1}. {fname} (score: {score:.3f})")
                
                # Get text content
                text = ""
                if hasattr(hit, "text") and hit.text:
                    text = hit.text
                else:
                    parts = getattr(hit, "content", []) or []
                    if parts and hasattr(parts[0], "text"):
                        text = parts[0].text
                
                if text:
                    print(f"     Preview: {text[:100]}...")
        else:
            print("No hits found in direct search!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_vector_search()
