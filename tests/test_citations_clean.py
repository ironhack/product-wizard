#!/usr/bin/env python3
"""
Test if files are being quoted properly with correct names and sections
Updated to use centralized configuration and utilities
"""

import sys
import os
import time

# Add tools directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tools'))

from test_utils import (
    get_openai_client, 
    get_assistant_id,
    create_test_thread,
    run_assistant_test,
    get_assistant_response,
    analyze_citations,
    print_test_header,
    print_test_results,
    save_test_results
)

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
    
    client = get_openai_client()
    assistant_id = get_assistant_id()
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print_test_header(f"Citation Test - {test_case['course']}", i, len(test_cases))
        print(f"📝 Question: {test_case['question']}")
        print(f"🎯 Expected files: {test_case['expected_files']}")
        print("-" * 60)
        
        try:
            # Create thread and run test
            thread = create_test_thread(client, test_case["question"])
            run = run_assistant_test(client, thread.id, assistant_id)
            
            if run.status == "completed":
                # Get response
                response_data = get_assistant_response(client, thread.id)
                response_text = response_data["text"]
                annotations = response_data["annotations"]
                
                # Analyze citations
                citation_analysis = analyze_citations(response_text, annotations)
                
                # Analyze expected files
                files_analysis = analyze_expected_files(response_text, annotations, test_case)
                
                result = {
                    "question": test_case["question"],
                    "course": test_case["course"],
                    "response_text": response_text,
                    "annotations": [str(ann) for ann in annotations],
                    "citation_analysis": citation_analysis,
                    "files_analysis": files_analysis
                }
                
                results.append(result)
                
                # Display results
                print_test_results(
                    test_case["course"], 
                    len(response_text), 
                    [],  # No fabrication check here
                    citation_analysis
                )
                
                # Show specific citation findings
                if citation_analysis["file_names"]:
                    print(f"✅ File citations found: {citation_analysis['file_names']}")
                
                if files_analysis["missing_expected_files"]:
                    print(f"⚠️ Missing expected files: {files_analysis['missing_expected_files']}")
                
                # Show response preview
                print(f"\n📄 Response preview:")
                print("-" * 40)
                preview_length = 300
                print(response_text[:preview_length] + "..." if len(response_text) > preview_length else response_text)
                print("-" * 40)
                
            else:
                print(f"❌ Run failed: {run.status}")
                
            time.sleep(3)  # Rate limiting
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Generate and save report
    generate_citation_report(results)
    
    # Save detailed results
    save_path = save_test_results(results, "citation_quality_test.json")
    print(f"\n💾 Detailed results saved to: {save_path}")
    
    return results

def analyze_expected_files(response_text, annotations, test_case):
    """Analyze if expected files are properly cited"""
    
    analysis = {
        "expected_files_found": [],
        "missing_expected_files": [],
        "unexpected_files_found": []
    }
    
    # Check response text and annotations for expected files
    response_lower = response_text.lower()
    
    for expected_file in test_case["expected_files"]:
        file_variations = [
            expected_file.lower(),
            expected_file.lower().replace("_", " "),
            expected_file.lower().replace("_", "-")
        ]
        
        found = False
        for variation in file_variations:
            if variation in response_lower:
                analysis["expected_files_found"].append(expected_file)
                found = True
                break
        
        if not found:
            analysis["missing_expected_files"].append(expected_file)
    
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
    tests_with_citations = sum(1 for r in results if r["citation_analysis"]["total_annotations"] > 0)
    tests_with_meaningful_citations = sum(1 for r in results if r["citation_analysis"]["has_meaningful_citations"])
    
    print(f"📈 OVERVIEW:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Tests with Citations: {tests_with_citations}/{total_tests} ({tests_with_citations/total_tests*100:.1f}%)")
    print(f"   Tests with Meaningful Citations: {tests_with_meaningful_citations}/{total_tests} ({tests_with_meaningful_citations/total_tests*100:.1f}%)")
    
    # Detailed analysis
    print(f"\n📋 DETAILED ANALYSIS:")
    
    for i, result in enumerate(results, 1):
        citation_analysis = result["citation_analysis"]
        files_analysis = result["files_analysis"]
        course = result["course"]
        
        print(f"\n{i}. {course}")
        
        if citation_analysis["total_annotations"] > 0:
            print(f"   ✅ Citations: {citation_analysis['total_annotations']}")
            
            if citation_analysis["has_meaningful_citations"]:
                print(f"   ✅ Meaningful citations: YES")
                if citation_analysis["file_names"]:
                    print(f"   📎 Files cited: {citation_analysis['file_names']}")
            else:
                print(f"   ⚠️ Meaningful citations: NO (generic only)")
                
        else:
            print(f"   ❌ No citations found")
        
        if files_analysis["expected_files_found"]:
            print(f"   ✅ Expected files found: {files_analysis['expected_files_found']}")
        
        if files_analysis["missing_expected_files"]:
            print(f"   ⚠️ Missing expected files: {files_analysis['missing_expected_files']}")
    
    # Overall assessment
    print(f"\n🎯 OVERALL ASSESSMENT:")
    
    if tests_with_meaningful_citations == total_tests:
        print(f"✅ EXCELLENT: All tests have meaningful citations with proper file names")
    elif tests_with_meaningful_citations >= total_tests * 0.8:
        print(f"✅ GOOD: Most tests have meaningful citations")
    elif tests_with_citations >= total_tests * 0.8:
        print(f"⚠️ FAIR: Citations present but many are generic")
    else:
        print(f"❌ POOR: Major citation problems detected")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if tests_with_meaningful_citations < total_tests:
        missing_count = total_tests - tests_with_meaningful_citations
        print(f"   - Improve {missing_count} tests to show specific file names in citations")
        print(f"   - Review prompt instructions for better source attribution")
    
    if tests_with_meaningful_citations == total_tests:
        print(f"   - Citation system is working excellently!")
        print(f"   - Continue monitoring for consistency")

def main():
    print("🔬 Citation Quality Testing (Clean Version)")
    print("=" * 45)
    
    try:
        results = test_citations_quality()
        print(f"\n✅ Citation testing complete!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
