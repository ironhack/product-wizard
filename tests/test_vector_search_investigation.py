#!/usr/bin/env python3
"""
Investigation script to analyze what the vector search returns
for bias-inducing queries to understand the root cause of fabrication.
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from openai import OpenAI
from test_config import OPENAI_API_KEY

class VectorSearchInvestigation:
    def __init__(self):
        """Initialize the vector search investigation."""
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Vector store ID for responses API
        self.vector_store_id = os.getenv('OPENAI_VECTOR_STORE_ID')
        if not self.vector_store_id:
            raise ValueError("OPENAI_VECTOR_STORE_ID environment variable is required")
        
        # Test queries that caused bias
        self.test_queries = [
            {
                "id": "data_science_languages",
                "query": "Quali sono tutti i linguaggi di programmazione coperti nel bootcamp di Data Science & Machine Learning?",
                "expected_languages": ["Python", "SQL"],
                "fabricated_languages": ["R", "JavaScript", "NoSQL"]
            },
            {
                "id": "cybersecurity_prework_details", 
                "query": "Quante ore di prework sono richieste per il corso di Cybersecurity e come sono distribuite?",
                "expected_details": ["40 hours", "9x Labs", "5x Assessment"],
                "missing_specifics": ["9x Labs", "5x Assessment"]
            },
            {
                "id": "aws_lambda_location",
                "query": "In quale unit del DevOps bootcamp è insegnato AWS Lambda?",
                "expected_unit": "Unit 1",
                "common_error": "Unit 2"
            }
        ]

    def search_with_detailed_response(self, query: str) -> Dict:
        """Execute search and return detailed response including citations."""
        print(f"\n🔍 Searching: {query}")
        
        try:
            # Use a minimal prompt that just asks for facts with citations
            minimal_prompt = """You are a helpful assistant. Answer the question based on the retrieved documents. 
            Always cite your sources clearly and indicate exactly which document each piece of information comes from.
            If you cannot find specific information in the documents, say so clearly."""
            
            request_params = {
                "model": "gpt-4o-mini",
                "input": query,
                "instructions": minimal_prompt,
                "tools": [
                    {
                        "type": "file_search",
                        "vector_store_ids": [self.vector_store_id]
                    }
                ]
            }
            
            print("Making Responses API call...")
            start_time = time.time()
            response = self.client.responses.create(**request_params)
            end_time = time.time()
            
            # Extract response and citations
            assistant_response = "No response found"
            citations = []
            
            if response.output and len(response.output) > 0:
                for output_item in response.output:
                    if hasattr(output_item, 'type') and output_item.type == 'message':
                        if hasattr(output_item, 'content') and len(output_item.content) > 0:
                            content = output_item.content[0]
                            if hasattr(content, 'text'):
                                assistant_response = content.text
                                
                                # Extract citations if available
                                if hasattr(content.text, 'annotations'):
                                    for annotation in content.text.annotations:
                                        citations.append({
                                            "type": annotation.type,
                                            "text": annotation.text,
                                            "file_citation": getattr(annotation, 'file_citation', None)
                                        })
                                break
            
            result = {
                "query": query,
                "response": assistant_response,
                "citations": citations,
                "response_time": end_time - start_time,
                "response_length": len(assistant_response)
            }
            
            print(f"✅ Response received in {result['response_time']:.2f}s")
            print(f"📄 Response length: {result['response_length']} characters")
            print(f"📚 Citations found: {len(citations)}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error in search: {str(e)}")
            return {
                "query": query,
                "response": f"Error: {str(e)}",
                "citations": [],
                "response_time": 0,
                "response_length": 0
            }

    def analyze_specific_documents(self, query: str) -> Dict:
        """Try to understand which specific documents are being retrieved."""
        print(f"\n📖 Document Analysis for: {query}")
        
        # Try with a more explicit prompt asking for document sources
        source_analysis_prompt = """List all the documents that contain information relevant to this query.
        For each document, specify:
        1. The exact document name
        2. What information from that document is relevant
        3. Quote the exact text that answers the query
        
        Be very explicit about your sources."""
        
        try:
            request_params = {
                "model": "gpt-4o-mini", 
                "input": f"{query}\n\nPlease analyze which documents contain relevant information and quote exact text.",
                "instructions": source_analysis_prompt,
                "tools": [
                    {
                        "type": "file_search",
                        "vector_store_ids": [self.vector_store_id]
                    }
                ]
            }
            
            response = self.client.responses.create(**request_params)
            
            # Extract response
            analysis_response = "No analysis found"
            if response.output and len(response.output) > 0:
                for output_item in response.output:
                    if hasattr(output_item, 'type') and output_item.type == 'message':
                        if hasattr(output_item, 'content') and len(output_item.content) > 0:
                            content = output_item.content[0]
                            if hasattr(content, 'text'):
                                analysis_response = content.text
                                break
            
            return {
                "query": query,
                "document_analysis": analysis_response
            }
            
        except Exception as e:
            return {
                "query": query,
                "document_analysis": f"Error: {str(e)}"
            }

    def run_comprehensive_investigation(self) -> Dict:
        """Run comprehensive investigation of vector search behavior."""
        print("🕵️ Starting Vector Search Investigation")
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Investigating {len(self.test_queries)} problematic queries")
        
        results = {
            "investigation_suite": "vector_search_bias_analysis",
            "timestamp": datetime.now().isoformat(),
            "vector_store_id": self.vector_store_id,
            "queries_analyzed": len(self.test_queries),
            "detailed_results": []
        }
        
        for i, test_case in enumerate(self.test_queries, 1):
            print(f"\n{'='*80}")
            print(f"🧪 Investigation {i}/{len(self.test_queries)}: {test_case['id']}")
            print(f"{'='*80}")
            
            # Get search response with minimal prompt
            search_result = self.search_with_detailed_response(test_case["query"])
            
            # Get document analysis
            doc_analysis = self.analyze_specific_documents(test_case["query"])
            
            # Combine results
            combined_result = {
                "test_id": test_case["id"],
                "original_query": test_case["query"],
                "search_result": search_result,
                "document_analysis": doc_analysis,
                "expected_info": {k: v for k, v in test_case.items() if k not in ["id", "query"]},
                "timestamp": datetime.now().isoformat()
            }
            
            results["detailed_results"].append(combined_result)
            
            # Brief pause between tests
            time.sleep(2)
        
        return results

    def analyze_bias_patterns(self, results: Dict) -> Dict:
        """Analyze patterns in the bias from vector search results."""
        print(f"\n🔬 ANALYZING BIAS PATTERNS")
        
        bias_analysis = {
            "total_queries": len(results["detailed_results"]),
            "bias_sources": [],
            "common_patterns": [],
            "recommendations": []
        }
        
        for result in results["detailed_results"]:
            search_response = result["search_result"]["response"]
            expected = result["expected_info"]
            
            # Analyze each case
            if result["test_id"] == "data_science_languages":
                # Check if fabricated languages appear
                fabricated_found = []
                for lang in expected.get("fabricated_languages", []):
                    if lang.lower() in search_response.lower():
                        fabricated_found.append(lang)
                
                if fabricated_found:
                    bias_analysis["bias_sources"].append({
                        "query": result["test_id"],
                        "issue": "fabricated_languages",
                        "details": f"Found fabricated languages: {fabricated_found}",
                        "possible_cause": "Vector search returning irrelevant documents containing these languages"
                    })
            
            elif result["test_id"] == "cybersecurity_prework_details":
                # Check if specific details are missing
                missing_details = []
                for detail in expected.get("missing_specifics", []):
                    if detail not in search_response:
                        missing_details.append(detail)
                
                if missing_details:
                    bias_analysis["bias_sources"].append({
                        "query": result["test_id"],
                        "issue": "missing_specific_details",
                        "details": f"Missing: {missing_details}",
                        "possible_cause": "Vector search not finding the specific curriculum section with detailed structure"
                    })
            
            elif result["test_id"] == "aws_lambda_location":
                # Check for unit number confusion
                if expected.get("common_error") in search_response:
                    bias_analysis["bias_sources"].append({
                        "query": result["test_id"],
                        "issue": "incorrect_unit_reference",
                        "details": f"Said '{expected['common_error']}' instead of '{expected['expected_unit']}'",
                        "possible_cause": "Vector search returning wrong section or conflating information"
                    })
        
        # Identify common patterns
        if len(bias_analysis["bias_sources"]) > 0:
            bias_analysis["common_patterns"] = [
                "Vector search appears to return documents/sections beyond the specific curriculum requested",
                "Information from different courses may be getting mixed",
                "Specific structural details (like '9x Labs') may not be properly indexed",
                "Unit numbering may be inconsistent across documents or search is conflating units"
            ]
            
            bias_analysis["recommendations"] = [
                "Review vector store contents to ensure only relevant curriculum documents are included",
                "Check document chunking strategy - may be creating chunks that lose context",
                "Verify file naming and structure in vector store matches expected curriculum docs",
                "Consider more specific search queries or query preprocessing",
                "Test with manual document retrieval to compare against vector search results"
            ]
        
        return bias_analysis

    def save_investigation_results(self, results: Dict, analysis: Dict) -> str:
        """Save investigation results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"vector_search_investigation_{timestamp}.json"
        filepath = os.path.join(os.path.dirname(__file__), "results", filename)
        
        # Ensure results directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        final_results = {
            **results,
            "bias_analysis": analysis
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Investigation results saved to: {filepath}")
        return filepath

    def print_investigation_summary(self, results: Dict, analysis: Dict):
        """Print comprehensive investigation summary."""
        print(f"\n{'='*100}")
        print(f"🕵️ VECTOR SEARCH INVESTIGATION SUMMARY")
        print(f"{'='*100}")
        
        print(f"📊 Queries Analyzed: {analysis['total_queries']}")
        print(f"🚨 Bias Sources Found: {len(analysis['bias_sources'])}")
        
        if analysis["bias_sources"]:
            print(f"\n🔍 DETAILED BIAS SOURCES:")
            for i, bias in enumerate(analysis["bias_sources"], 1):
                print(f"\n{i}. {bias['query'].upper()}")
                print(f"   Issue: {bias['issue']}")
                print(f"   Details: {bias['details']}")
                print(f"   Possible Cause: {bias['possible_cause']}")
        
        if analysis["common_patterns"]:
            print(f"\n🎯 COMMON PATTERNS IDENTIFIED:")
            for i, pattern in enumerate(analysis["common_patterns"], 1):
                print(f"{i}. {pattern}")
        
        if analysis["recommendations"]:
            print(f"\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(analysis["recommendations"], 1):
                print(f"{i}. {rec}")
        
        print(f"\n📄 SAMPLE RESPONSES:")
        for result in results["detailed_results"]:
            print(f"\n--- {result['test_id'].upper()} ---")
            print(f"Query: {result['original_query']}")
            print(f"Response Preview: {result['search_result']['response'][:200]}...")
            if result['search_result']['citations']:
                print(f"Citations: {len(result['search_result']['citations'])} found")


def main():
    """Main execution function."""
    print("🕵️ Vector Search Investigation for Bias Detection")
    print("Analyzing what the vector search returns to understand fabrication sources")
    
    try:
        investigator = VectorSearchInvestigation()
        results = investigator.run_comprehensive_investigation()
        analysis = investigator.analyze_bias_patterns(results)
        filepath = investigator.save_investigation_results(results, analysis)
        investigator.print_investigation_summary(results, analysis)
        
        print(f"\n🎯 Investigation completed successfully!")
        print(f"📄 Full results available in: {filepath}")
        
    except Exception as e:
        print(f"❌ Investigation failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
