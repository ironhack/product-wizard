#!/usr/bin/env python3
"""
Automated testing system for the Ironhack Assistant
Tests file search functionality and response quality
"""

import openai
import time
import json
import re
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration from environment
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ASSISTANT_ID = os.environ.get("OPENAI_ASSISTANT_ID")

if not OPENAI_API_KEY or not ASSISTANT_ID:
    raise ValueError("Please set OPENAI_API_KEY and OPENAI_ASSISTANT_ID in your .env file")

openai.api_key = OPENAI_API_KEY

class AssistantTester:
    def __init__(self):
        self.test_results = []
        
    def check_assistant_config(self):
        """Check the current assistant configuration"""
        print("🔍 Checking Assistant Configuration...")
        print("=" * 60)
        
        try:
            assistant = openai.beta.assistants.retrieve(assistant_id=ASSISTANT_ID)
            
            print(f"✅ Assistant Name: {assistant.name}")
            print(f"✅ Model: {assistant.model}")
            print(f"✅ Instructions Preview: {assistant.instructions[:100]}...")
            
            print(f"\n🛠️ Tools enabled:")
            for tool in assistant.tools:
                print(f"   - {tool.type}")
            
            if hasattr(assistant, 'tool_resources') and assistant.tool_resources:
                if hasattr(assistant.tool_resources, 'file_search') and assistant.tool_resources.file_search:
                    vector_store_ids = assistant.tool_resources.file_search.vector_store_ids
                    print(f"\n📦 Vector Store IDs: {vector_store_ids}")
                    
                    for vs_id in vector_store_ids:
                        print(f"\n📂 Checking Vector Store: {vs_id}")
                        try:
                            vector_store = openai.beta.vector_stores.retrieve(vector_store_id=vs_id)
                            print(f"   Name: {vector_store.name}")
                            print(f"   Status: {vector_store.status}")
                            print(f"   File counts: {vector_store.file_counts}")
                            
                            # List files
                            files = openai.beta.vector_stores.files.list(vector_store_id=vs_id)
                            print(f"   Files ({len(files.data)}):")
                            for file in files.data[:10]:  # Show first 10
                                try:
                                    file_details = openai.files.retrieve(file.id)
                                    print(f"      - {file_details.filename} ({file.status})")
                                except:
                                    print(f"      - {file.id} ({file.status})")
                                    
                        except Exception as e:
                            print(f"   ❌ Error: {e}")
                else:
                    print("❌ No file_search configuration found!")
            else:
                print("❌ No tool_resources found!")
                
            return True
                
        except Exception as e:
            print(f"❌ Error checking assistant: {e}")
            return False
    
    def test_question(self, question: str, expected_keywords: List[str] = None) -> Dict[str, Any]:
        """Test a single question with the assistant"""
        print(f"\n🤔 Testing Question: {question}")
        print("-" * 40)
        
        try:
            # Create thread
            thread = openai.beta.threads.create()
            
            # Add message
            openai.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=question
            )
            
            # Run assistant
            run = openai.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )
            
            # Wait for completion
            start_time = time.time()
            while run.status in ["queued", "in_progress"]:
                time.sleep(1)
                run = openai.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                
                if time.time() - start_time > 60:  # Timeout after 60 seconds
                    return {"error": "Timeout waiting for response"}
            
            if run.status == "completed":
                # Get response
                messages = openai.beta.threads.messages.list(thread_id=thread.id)
                response = messages.data[0].content[0].text.value
                annotations = messages.data[0].content[0].text.annotations
                
                # Analyze response
                analysis = self.analyze_response(response, annotations, expected_keywords)
                
                result = {
                    "question": question,
                    "response": response,
                    "annotations_count": len(annotations),
                    "annotations": [str(ann) for ann in annotations],
                    "analysis": analysis,
                    "status": "success"
                }
                
                print(f"✅ Response received ({len(response)} chars)")
                print(f"📎 Citations: {len(annotations)}")
                print(f"🎯 Analysis: {analysis['summary']}")
                
                return result
                
            else:
                error_msg = f"Run failed with status: {run.status}"
                if hasattr(run, 'last_error'):
                    error_msg += f" - {run.last_error}"
                print(f"❌ {error_msg}")
                return {"error": error_msg, "question": question}
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"error": str(e), "question": question}
    
    def analyze_response(self, response: str, annotations: List, expected_keywords: List[str] = None) -> Dict[str, Any]:
        """Analyze the quality of the response"""
        analysis = {
            "has_citations": len(annotations) > 0,
            "response_length": len(response),
            "contains_expected_keywords": False,
            "looks_fabricated": False,
            "summary": ""
        }
        
        # Check for expected keywords
        if expected_keywords:
            found_keywords = []
            for keyword in expected_keywords:
                if keyword.lower() in response.lower():
                    found_keywords.append(keyword)
            analysis["found_keywords"] = found_keywords
            analysis["contains_expected_keywords"] = len(found_keywords) > 0
        
        # Look for signs of fabrication
        fabrication_indicators = [
            "i don't have access",
            "i cannot find",
            "based on general knowledge",
            "typically includes",
            "usually covers",
            "generally consists of",
            "commonly taught"
        ]
        
        fabricated_phrases = []
        for indicator in fabrication_indicators:
            if indicator in response.lower():
                fabricated_phrases.append(indicator)
        
        analysis["fabricated_phrases"] = fabricated_phrases
        analysis["looks_fabricated"] = len(fabricated_phrases) > 0
        
        # Check for "not available" message
        analysis["says_not_available"] = "not available in the official curriculum documentation" in response.lower()
        
        # Generate summary
        if analysis["has_citations"]:
            analysis["summary"] = f"✅ Good - Has {len(annotations)} citations"
        elif analysis["says_not_available"]:
            analysis["summary"] = "⚠️ Says info not available (good honesty)"
        elif analysis["looks_fabricated"]:
            analysis["summary"] = f"❌ Looks fabricated - found: {fabricated_phrases}"
        else:
            analysis["summary"] = "⚠️ No citations but doesn't look obviously fabricated"
            
        return analysis
    
    def run_comprehensive_test(self):
        """Run a comprehensive test suite"""
        print("\n🚀 Starting Comprehensive Assistant Test")
        print("=" * 60)
        
        # Check configuration first
        if not self.check_assistant_config():
            print("❌ Configuration check failed, aborting tests")
            return
        
        # Test questions
        test_cases = [
            {
                "question": "What technologies are covered in the Web Development bootcamp?",
                "expected_keywords": ["JavaScript", "React", "Node.js", "HTML", "CSS"]
            },
            {
                "question": "How long is the Data Analytics bootcamp?",
                "expected_keywords": ["weeks", "months", "duration"]
            },
            {
                "question": "What's the difference between Remote and Berlin variants for UX/UI?",
                "expected_keywords": ["Remote", "Berlin", "variant"]
            },
            {
                "question": "Tell me about the AI Engineering bootcamp curriculum.",
                "expected_keywords": ["AI", "machine learning", "Python"]
            },
            {
                "question": "What are the prerequisites for the Data Science program?",
                "expected_keywords": ["prerequisites", "requirements"]
            }
        ]
        
        print(f"\n🧪 Running {len(test_cases)} test cases...")
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{'='*20} Test {i}/{len(test_cases)} {'='*20}")
            result = self.test_question(
                test_case["question"], 
                test_case.get("expected_keywords")
            )
            self.test_results.append(result)
            time.sleep(2)  # Rate limiting
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate a comprehensive test report"""
        print(f"\n📊 TEST REPORT")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r.get("status") == "success"])
        tests_with_citations = len([r for r in self.test_results if r.get("analysis", {}).get("has_citations", False)])
        fabricated_responses = len([r for r in self.test_results if r.get("analysis", {}).get("looks_fabricated", False)])
        
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {successful_tests}")
        print(f"With Citations: {tests_with_citations}")
        print(f"Looks Fabricated: {fabricated_responses}")
        print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        print(f"Citation Rate: {(tests_with_citations/successful_tests)*100:.1f}%" if successful_tests > 0 else "Citation Rate: 0%")
        
        print(f"\n📝 Detailed Results:")
        for i, result in enumerate(self.test_results, 1):
            if result.get("status") == "success":
                analysis = result.get("analysis", {})
                print(f"\n{i}. {result['question'][:50]}...")
                print(f"   Status: {analysis.get('summary', 'Unknown')}")
                print(f"   Citations: {result.get('annotations_count', 0)}")
                if analysis.get("found_keywords"):
                    print(f"   Keywords found: {analysis['found_keywords']}")
            else:
                print(f"\n{i}. {result['question'][:50]}...")
                print(f"   Status: ❌ ERROR - {result.get('error', 'Unknown error')}")
        
        # Save detailed report
        with open('test_report.json', 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed report saved to: test_report.json")
        
        # Assessment
        print(f"\n🎯 ASSESSMENT:")
        if tests_with_citations == 0:
            print("❌ CRITICAL: No responses have citations - file search is not working!")
        elif tests_with_citations < successful_tests * 0.5:
            print("⚠️ WARNING: Less than 50% of responses have citations - file search may be unreliable")
        else:
            print("✅ File search appears to be working - most responses have citations")
            
        if fabricated_responses > 0:
            print(f"⚠️ WARNING: {fabricated_responses} responses show signs of fabrication")

if __name__ == "__main__":
    tester = AssistantTester()
    tester.run_comprehensive_test()
