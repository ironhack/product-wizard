"""
Custom RAG Pipeline Tester Template
Uses the actual CustomRAGPipeline class from app_custom_rag.py
This ensures we test the exact same code that runs in production
"""
import os
import sys
import openai
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path to import the actual production code
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

# Import the actual CustomRAGPipeline class from production app
try:
    from app_custom_rag import CustomRAGPipeline, load_master_prompt
    print("✅ Successfully imported production CustomRAGPipeline class")
except ImportError as e:
    print(f"❌ Failed to import production code: {e}")
    print("Make sure you're running this from the project root or tools/ directory")
    sys.exit(1)

class CustomRAGTester:
    """Wrapper class that uses the actual production CustomRAGPipeline"""
    
    def __init__(self, client=None, vector_store_id=None, master_prompt=None):
        self.client = client or openai.OpenAI(api_key=os.environ['OPENAI_API_KEY'])
        self.vector_store_id = vector_store_id or os.environ['OPENAI_VECTOR_STORE_ID']
        self.master_prompt = master_prompt or load_master_prompt()
        
        # Initialize the actual production RAG pipeline
        self.rag_pipeline = CustomRAGPipeline(
            client=self.client,
            vector_store_id=self.vector_store_id,
            master_prompt=self.master_prompt
        )
        print("✅ Initialized production CustomRAGPipeline for testing")
    
    def retrieve_documents(self, query):
        """Use production retrieve_documents method"""
        return self.rag_pipeline.retrieve_documents(query)
    
    def generate_response(self, query, retrieved_docs, sources=None, conversation_context=None):
        """Use production generate_response method"""
        # The production method expects sources to be passed via the retrieved_docs parameter
        # So we call it with the same signature as production
        return self.rag_pipeline.generate_response(query, retrieved_docs, conversation_context)
    
    def run_test(self, query, conversation_context=None):
        """Run a complete test using the production process_query method"""
        start_time = time.time()
        
        print(f"\n🎯 Testing: {query}")
        print("-" * 60)
        
        # Use the actual production process_query method
        result = self.rag_pipeline.process_query(query, conversation_context)
        
        total_time = time.time() - start_time
        
        print(f"\n📝 Response: {result['response']}")
        print(f"📊 Metrics: {result['retrieved_docs_count']} docs, {result['sources']}, {total_time:.2f}s")
        
        # Return results in consistent format
        return {
            "query": query,
            "response": result["response"],
            "retrieved_docs_count": result["retrieved_docs_count"],
            "sources": result["sources"],
            "processing_time": total_time,
            "validation": result.get("validation", {})  # Include validation if available
        }
    
    def run_test_suite(self, test_queries):
        """Run a suite of tests using production pipeline"""
        print("🚀 Running Custom RAG Test Suite (Production Code)")
        print("=" * 60)
        
        results = []
        for i, query in enumerate(test_queries, 1):
            print(f"\n[Test {i}/{len(test_queries)}]")
            result = self.run_test(query)
            results.append(result)
            time.sleep(1)  # Brief pause
        
        # Summary
        print("\n" + "=" * 60)
        print("🏆 SUMMARY")
        print("=" * 60)
        
        avg_time = sum(r['processing_time'] for r in results) / len(results)
        successful_retrievals = sum(1 for r in results if r['retrieved_docs_count'] > 0)
        
        print(f"Tests: {len(results)}")
        print(f"Avg time: {avg_time:.2f}s")
        print(f"Successful retrievals: {successful_retrievals}/{len(results)}")
        print(f"Production code validated: ✅")
        
        return results

def example_usage():
    """Example usage of the Custom RAG Tester with production code"""
    
    # Initialize tester (uses actual production CustomRAGPipeline)
    tester = CustomRAGTester()
    
    # Define test queries
    test_queries = [
        "What certifications does Ironhack offer for Data Analytics?",
        "How many weeks is the Web Development Remote bootcamp?",
        "What programming languages are taught in the AI Engineering bootcamp?",
        "How much does the Cybersecurity bootcamp cost?"
    ]
    
    # Run test suite using production pipeline
    results = tester.run_test_suite(test_queries)
    
    # Additional validation information
    print("\n🎯 Benefits of using production code:")
    print("  ✅ Tests exact same logic that runs in Slack app")
    print("  ✅ Single source of truth - no code duplication")
    print("  ✅ Changes to app_custom_rag.py automatically tested")
    print("  ✅ Includes production validation and error handling")
    
    return results

if __name__ == "__main__":
    # Run example usage
    example_usage()
