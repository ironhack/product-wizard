#!/usr/bin/env python3

"""
Debug script for failed regression tests
Focuses on the specific issues identified in the 2:45 test run
"""

import sys
import os
import json
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment
load_dotenv()

# Set mock Slack environment variables before importing to avoid Slack initialization errors
os.environ['SLACK_BOT_TOKEN'] = 'xoxb-test-token-for-testing'
os.environ['SLACK_SIGNING_SECRET'] = 'test-signing-secret-for-testing'

def initialize_pipeline():
    """Initialize the Custom RAG Pipeline"""
    try:
        import openai
        from src.app_custom_rag import CustomRAGPipeline
        
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        vector_store_id = os.getenv('OPENAI_VECTOR_STORE_ID')
        
        with open('assistant_config/MASTER_PROMPT.md', 'r') as f:
            master_prompt = f.read()
        
        return CustomRAGPipeline(client, vector_store_id, master_prompt)
    except Exception as e:
        raise Exception(f"Failed to initialize pipeline: {e}")

def debug_variant_qa_issue(pipeline):
    """Debug the variant QA errors that are causing UNCLEAR responses"""
    print("\n🔍 DEBUGGING VARIANT QA ISSUES")
    print("=" * 50)
    
    test_queries = [
        "How long is the Web Development Remote bootcamp?",
        "What tools are used in the DevOps bootcamp?",
        "Does Web Development cover SQL?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[Debug {i}] Query: {query}")
        print("-" * 40)
        
        try:
            # Test retrieval first
            print("1. Testing document retrieval...")
            retrieved_docs, sources = pipeline.retrieve_documents(query)
            print(f"   Retrieved {len(retrieved_docs)} documents from {len(sources)} sources")
            print(f"   Sources: {sources}")
            
            # Test variant detection
            print("2. Testing variant detection...")
            by_variant = pipeline._by_variant()
            print(f"   Detected variants: {list(by_variant.keys())}")
            for variant, files in by_variant.items():
                print(f"   {variant}: {[f[1] for f in files]}")
            
            # Test if variant QA would be triggered
            concrete_variants = [v for v in by_variant.keys() if v != "unspecified"]
            print(f"   Concrete variants: {concrete_variants}")
            print(f"   Would trigger variant QA: {len(concrete_variants) > 1}")
            
            # Test full process
            print("3. Testing full process...")
            result = pipeline.process_query(query)
            response = result['response']
            processing_time = result['processing_time']
            
            print(f"   Response: {response[:200]}...")
            print(f"   Processing time: {processing_time:.2f}s")
            print(f"   Validation confidence: {result['validation'].get('confidence', 0):.2f}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

def debug_ambiguity_handling(pipeline):
    """Debug the ambiguity handling issues with incorrect duration information"""
    print("\n🔍 DEBUGGING AMBIGUITY HANDLING")
    print("=" * 50)
    
    query = "What's the difference between Data Analytics and Data Science bootcamps?"
    print(f"Query: {query}")
    print("-" * 40)
    
    try:
        # Test retrieval
        print("1. Testing document retrieval...")
        retrieved_docs, sources = pipeline.retrieve_documents(query)
        print(f"   Retrieved {len(retrieved_docs)} documents from {len(sources)} sources")
        print(f"   Sources: {sources}")
        
        # Check what documents were retrieved
        print("2. Analyzing retrieved content...")
        for i, doc in enumerate(retrieved_docs[:3]):  # Show first 3 docs
            print(f"   Doc {i+1}: {doc[:100]}...")
        
        # Test full process
        print("3. Testing full process...")
        result = pipeline.process_query(query)
        response = result['response']
        
        print(f"   Response: {response}")
        print(f"   Processing time: {result['processing_time']:.2f}s")
        
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
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_specific_fixes(pipeline):
    """Test specific fixes for the identified issues"""
    print("\n🔧 TESTING SPECIFIC FIXES")
    print("=" * 50)
    
    # Test 1: Simple queries that should work without variant QA
    simple_queries = [
        "What is the duration of the Web Development Remote bootcamp?",
        "What tools are taught in the DevOps bootcamp curriculum?",
        "Does the Web Development Remote program include SQL?"
    ]
    
    for i, query in enumerate(simple_queries, 1):
        print(f"\n[Fix Test {i}] Query: {query}")
        print("-" * 40)
        
        try:
            result = pipeline.process_query(query)
            response = result['response']
            
            print(f"   Response: {response[:200]}...")
            
            # Check if it's a variant QA response
            if "*Variant-specific answer*" in response:
                print("   ❌ Still using variant QA (unexpected)")
            else:
                print("   ✅ Using standard generation")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

def main():
    """Run the debug tests"""
    print("🐛 DEBUGGING FAILED REGRESSION TESTS")
    print("=" * 60)
    print("Focusing on variant QA errors and ambiguity handling issues")
    print()
    
    try:
        # Initialize pipeline
        print("🔧 Initializing Custom RAG Pipeline...")
        pipeline = initialize_pipeline()
        print("✅ Pipeline initialized successfully")
        
        # Debug variant QA issues
        debug_variant_qa_issue(pipeline)
        
        # Debug ambiguity handling
        debug_ambiguity_handling(pipeline)
        
        # Test specific fixes
        test_specific_fixes(pipeline)
        
        print("\n🎯 Debug analysis complete!")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
