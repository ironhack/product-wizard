#!/usr/bin/env python3
"""
Simple test for WD SQL question - keep this one!
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment
load_dotenv()

# Set mock Slack environment variables before importing to avoid Slack initialization errors
os.environ['SLACK_BOT_TOKEN'] = 'xoxb-test-token-for-testing'
os.environ['SLACK_SIGNING_SECRET'] = 'test-signing-secret-for-testing'

def test_wd_sql():
    """Test the WD SQL question."""
    print("🧪 TESTING WD SQL QUESTION")
    print("=" * 40)
    
    try:
        import openai
        from src.app_custom_rag import CustomRAGPipeline
        
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        vector_store_id = os.getenv('OPENAI_VECTOR_STORE_ID')
        
        with open('assistant_config/MASTER_PROMPT.md', 'r') as f:
            master_prompt = f.read()
        
        pipeline = CustomRAGPipeline(client, vector_store_id, master_prompt)
        
        query = "Does Web Development cover SQL?"
        print(f"Query: {query}")
        print()
        
        result = pipeline.process_query(query, [])
        response = result['response']
        sources = result.get('sources', [])
        
        print(f"📊 Sources: {sources}")
        print()
        print("📝 Response:")
        print("-" * 30)
        print(response)
        print("-" * 30)
        print()
        
        # Quick analysis
        web_dev_sources = [s for s in sources if 'Web_Dev' in s]
        data_analytics_sources = [s for s in sources if 'Data_Analytics' in s]
        
        print("🔍 Analysis:")
        print(f"  Web Dev sources: {web_dev_sources}")
        print(f"  Data Analytics sources: {data_analytics_sources}")
        
        if web_dev_sources and not data_analytics_sources:
            print("✅ SUCCESS: Only Web Dev sources retrieved!")
        elif web_dev_sources and data_analytics_sources:
            print("⚠️  PARTIAL: Both Web Dev and Data Analytics sources")
        else:
            print("❌ FAILED: No Web Dev sources or wrong sources")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_wd_sql()
