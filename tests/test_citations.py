#!/usr/bin/env python3
"""
Test if files are being quoted properly with correct names and sections
"""

import openai
import time
import re
from test_config import OPENAI_API_KEY, OPENAI_ASSISTANT_ID

ASSISTANT_ID = OPENAI_ASSISTANT_ID

def test_citations_quality():
    """Test various questions to see citation quality and accuracy"""
    
    print("🔍 Testing Citation Quality and Accuracy")
    print("=" * 50)
    
    # Test questions targeting different courses and specific information
    test_cases = [
        {
            "question": "What technologies are covered in the Web Development bootcamp?",
            "expected_files": ["Web_Dev_Remote_bootcamp_2025_07"],
            "course": "Web Development"
        },
        {
            "question": "What tools are used in the DevOps bootcamp?", 
            "expected_files": ["DevOps_bootcamp_2025_07"],
            "course": "DevOps"
        },
        {
            "question": "How long is the Data Analytics Remote bootcamp?",
            "expected_files": ["Data_Analytics_Remote_bootcamp_2025_07"],
            "course": "Data Analytics Remote"
        },
        {
            "question": "What's the difference between UX/UI Remote and Berlin variants?",
            "expected_files": ["UXUI_Remote_bootcamp_2025_07", "UXUI_Berlin_onsite_bootcamp_2025_07"],
            "course": "UX/UI"
        },
        {
            "question": "What prerequisites are needed for AI Engineering?",
            "expected_files": ["AI_Engineering_bootcamp_2025_07"],
            "course": "AI Engineering"
        }
    ]
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*20} Citation Test {i}/5 {'='*20}")
        print(f"📝 Question: {test_case['question']}")
        print(f"🎯 Expected files: {test_case['expected_files']}")
        print("-" * 60)
        
        try:
            # Create thread
            thread = client.beta.threads.create()
            
            # Add message
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=test_case["question"]
            )
            
            # Run assistant
            run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )
            
            # Wait for completion
            while run.status in ["queued", "in_progress"]:
                time.sleep(2)
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            if run.status == "completed":
                # Get response with annotations
                messages = client.beta.threads.messages.list(thread_id=thread.id)
                message = messages.data[0]
                response_text = message.content[0].text.value
                annotations = message.content[0].text.annotations
                
                # Analyze citations
                citation_analysis = analyze_citations(response_text, annotations, test_case)
                
                result = {
                    "question": test_case["question"],
                    "course": test_case["course"],
                    "response_text": response_text,
                    "annotations": [str(ann) for ann in annotations],
                    "analysis": citation_analysis
                }
                
                results.append(result)
                
                # Display results
                print(f"✅ Response length: {len(response_text)} chars")
                print(f"📎 Total annotations: {len(annotations)}")
                
                if citation_analysis["proper_citations"]:
                    print(f"✅ Proper citations found: {len(citation_analysis['proper_citations'])}")
                    for citation in citation_analysis["proper_citations"]:
                        print(f"   - {citation}")
                else:
                    print(f"❌ No proper citations found")
                
                if citation_analysis["citation_issues"]:
                    print(f"⚠️ Citation issues:")
                    for issue in citation_analysis["citation_issues"]:
                        print(f"   - {issue}")
                
                # Show first part of response
                print(f"\n📄 Response preview:")
                print("-" * 40)
                print(response_text[:300] + "..." if len(response_text) > 300 else response_text)
                print("-" * 40)
                
                # Show raw annotations
                if annotations:
                    print(f"\n📎 Raw annotations:")
                    for j, ann in enumerate(annotations):
                        print(f"   {j+1}. {ann}")
                
            else:
                print(f"❌ Run failed: {run.status}")
                
            time.sleep(3)  # Rate limiting
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Generate citation quality report
    generate_citation_report(results)
    
    return results

def analyze_citations(response_text, annotations, test_case):
    """Analyze the quality and accuracy of citations"""
    
    analysis = {
        "total_annotations": len(annotations),
        "proper_citations": [],
        "citation_issues": [],
        "expected_files_cited": [],
        "unexpected_files_cited": [],
        "citation_format_correct": True
    }
    
    # Parse citation patterns in response text
    citation_patterns = re.findall(r'【\d+:\d+†([^】]+)】', response_text)
    
    if annotations:
        for i, annotation in enumerate(annotations):
            annotation_str = str(annotation)
            
            # Extract file reference from annotation
            if hasattr(annotation, 'file_citation') and annotation.file_citation:
                file_id = annotation.file_citation.file_id
                # Note: We can't easily get filename from file_id without additional API call
                analysis["proper_citations"].append(f"File ID: {file_id}")
            
            # Check annotation text for file names
            for pattern in citation_patterns:
                if pattern not in [cite.split(": ")[1] if ": " in cite else cite for cite in analysis["proper_citations"]]:
                    analysis["proper_citations"].append(f"Pattern: {pattern}")
                    
                    # Check if it matches expected files
                    for expected_file in test_case["expected_files"]:
                        if expected_file in pattern:
                            analysis["expected_files_cited"].append(expected_file)
                            break
                    else:
                        # Check if it's a reasonable file name
                        if any(keyword in pattern.lower() for keyword in ["bootcamp", "2025", ".txt", ".md"]):
                            analysis["unexpected_files_cited"].append(pattern)
    else:
        analysis["citation_issues"].append("No annotations found in response")
    
    # Check if expected files are being referenced
    for expected_file in test_case["expected_files"]:
        found = any(expected_file in citation for citation in analysis["proper_citations"])
        if not found:
            analysis["citation_issues"].append(f"Expected file '{expected_file}' not cited")
    
    # Check citation format
    if citation_patterns:
        for pattern in citation_patterns:
            if not re.match(r'^[A-Za-z0-9_\-\.]+$', pattern.replace(' ', '_')):
                analysis["citation_issues"].append(f"Unusual citation format: {pattern}")
    
    return analysis

def generate_citation_report(results):
    """Generate comprehensive citation quality report"""
    
    print(f"\n{'='*60}")
    print("📊 CITATION QUALITY REPORT")
    print("=" * 60)
    
    if not results:
        print("❌ No results to analyze")
        return
    
    # Overall statistics
    total_tests = len(results)
    tests_with_citations = sum(1 for r in results if r["analysis"]["total_annotations"] > 0)
    total_citation_issues = sum(len(r["analysis"]["citation_issues"]) for r in results)
    
    print(f"📈 OVERVIEW:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Tests with Citations: {tests_with_citations}/{total_tests} ({tests_with_citations/total_tests*100:.1f}%)")
    print(f"   Total Citation Issues: {total_citation_issues}")
    
    # Detailed analysis
    print(f"\n📋 DETAILED ANALYSIS:")
    
    for i, result in enumerate(results, 1):
        analysis = result["analysis"]
        course = result["course"]
        
        print(f"\n{i}. {course}")
        
        if analysis["total_annotations"] > 0:
            print(f"   ✅ Citations: {analysis['total_annotations']}")
            
            if analysis["expected_files_cited"]:
                print(f"   ✅ Expected files cited: {analysis['expected_files_cited']}")
            
            if analysis["proper_citations"]:
                print(f"   📎 Citations found:")
                for citation in analysis["proper_citations"][:3]:  # Show first 3
                    print(f"      - {citation}")
            
        else:
            print(f"   ❌ No citations found")
        
        if analysis["citation_issues"]:
            print(f"   ⚠️ Issues:")
            for issue in analysis["citation_issues"]:
                print(f"      - {issue}")
    
    # Overall assessment
    print(f"\n🎯 OVERALL ASSESSMENT:")
    
    if tests_with_citations == total_tests and total_citation_issues == 0:
        print(f"✅ EXCELLENT: All tests have proper citations with no issues")
    elif tests_with_citations >= total_tests * 0.8:
        print(f"✅ GOOD: Most tests have citations, minor issues to address")
    elif tests_with_citations >= total_tests * 0.5:
        print(f"⚠️ FAIR: Some citation issues, needs improvement")
    else:
        print(f"❌ POOR: Major citation problems, requires attention")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if total_citation_issues > 0:
        print(f"   - Address {total_citation_issues} citation issues identified")
        print(f"   - Verify file names in citations match actual filenames")
        print(f"   - Ensure expected files are being referenced")
    
    if tests_with_citations < total_tests:
        print(f"   - Investigate why {total_tests - tests_with_citations} tests lack citations")
        print(f"   - Check if vector store is properly configured")
    
    if tests_with_citations == total_tests and total_citation_issues == 0:
        print(f"   - Citation system is working perfectly!")
        print(f"   - Continue monitoring for consistency")

def main():
    print("🔬 Citation Quality Testing")
    print("=" * 30)
    
    results = test_citations_quality()
    
    # Save results
    import json
    with open('citation_test_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: citation_test_results.json")
    print(f"✅ Citation testing complete!")

if __name__ == "__main__":
    main()
