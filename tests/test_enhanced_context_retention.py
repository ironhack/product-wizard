#!/usr/bin/env python3

"""
ENHANCED CONTEXT RETENTION TEST
Tests the improved Responses API implementation with conversation history tracking.

This test validates that the enhanced conversation context fixes the issues identified
in the original context retention test.
"""

import os
import sys
import json
from datetime import datetime

# Add the parent directory to the path to import the framework
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from tools.prompt_optimization_template import PromptOptimizationFramework

def test_enhanced_context_retention():
    """Test enhanced context retention with conversation history tracking."""
    
    framework = PromptOptimizationFramework()
    
    # Test cases designed to simulate a realistic conversation flow
    test_cases = [
        {
            "id": "initial_devops_request",
            "question": "Can you give me the full list of tools used in the DevOps bootcamp?",
            "expected_answer": "The DevOps bootcamp includes tools across multiple categories: Linux, Git, GitHub, AWS services (Console, CLI, EC2, S3, VPC, IAM, CloudWatch, ELB, RDS, Lambda, CloudFormation), Azure services (including AKS, CLI, Portal, Microsoft Entra), Terraform, Ansible, Docker, Docker Compose, Kubernetes, kubectl, Minikube, eksctl, GitHub Actions, SonarQube, Prometheus, Grafana, Trello/Jira, Python & boto3, YAML, Jinja2 templates. These tools are distributed across 8 units covering fundamentals, cloud computing, IaC, containerization, orchestration, CI/CD, and monitoring.",
            "rationale": "Tests initial comprehensive response quality - should work well as baseline"
        },
        {
            "id": "follow_up_with_context",
            "question": "Are these all the tools mentioned in the curriculum?",
            "expected_answer": "The list I provided covers the main tools from the DevOps bootcamp curriculum. However, there are some additional tools mentioned in specific lab contexts throughout the units, including: k9s (Kubernetes management), Tshark (network analysis), MySQL (containerization labs), NGINX (deployment and Ingress controllers), Storage Explorer & AzCopy (Azure tools), Grafana Loki (log aggregation), and cAdvisor (container monitoring). These appear in various hands-on exercises across the 8 units.",
            "rationale": "Tests follow-up clarification with maintained DevOps context - should no longer show scope creep"
        },
        {
            "id": "scope_boundary_test",
            "question": "What about tools for other programs?",
            "expected_answer": "You were asking about DevOps bootcamp tools specifically. If you'd like information about tools used in other Ironhack programs like Web Development, Data Science, Cybersecurity, or others, I'd be happy to help with those separately. Should I focus on a specific program, or would you like me to continue with DevOps-related questions?",
            "rationale": "Tests ability to maintain boundaries and ask for clarification rather than expanding scope"
        },
        {
            "id": "context_carryover_test",
            "question": "How are the DevOps tools organized in the curriculum?",
            "expected_answer": "The DevOps bootcamp tools are organized across 8 main units: Unit 0 (Prework): Linux, Git, AWS, Azure; Unit 1: Git, GitHub, Linux CLI, Trello/Jira; Unit 2: AWS Console, CLI, EC2, S3, VPC, IAM, CloudWatch, Python & boto3; Unit 3: Terraform, Ansible, YAML, Jinja2; Unit 4: Docker, Docker Compose, Node.js, Java, MySQL; Unit 5: Kubernetes, kubectl, Minikube, k9s; Unit 6: Amazon EKS, eksctl, GitHub Actions, SonarQube; Units 7-8: Azure services, AKS, Prometheus, Grafana, monitoring tools. Each unit builds on previous knowledge with hands-on projects applying these tools.",
            "rationale": "Tests whether assistant remembers DevOps context from conversation history"
        },
        {
            "id": "specific_subset_extraction",
            "question": "Which of those tools are specifically for monitoring?",
            "expected_answer": "From the DevOps bootcamp tools we discussed, the monitoring-specific tools are: Prometheus (for metrics collection and alerting), Grafana (for visualization and dashboards, including both self-hosted and Azure Managed versions), Grafana Loki (for log aggregation), AWS CloudWatch (for AWS resource monitoring), and cAdvisor (for container monitoring). These are primarily covered in Units 2, 6, and 8 of the curriculum.",
            "rationale": "Tests ability to extract specific subset while maintaining conversation context"
        }
    ]
    
    print("🔍 Testing Enhanced Context Retention")
    print("=" * 60)
    print("Testing improved Responses API with conversation history tracking")
    print("Expected improvements:")
    print("✅ Maintain DevOps context across multiple exchanges")  
    print("✅ No scope creep to other programs")
    print("✅ Proper follow-up question handling")
    print("✅ Context carryover for organizational questions")
    print()
    
    # Run the tests
    success, avg_score, results = framework.run_optimization_tests(
        test_cases, 
        "Enhanced Context Retention Test"
    )
    
    # Enhanced analysis for context retention
    print("\n📋 ENHANCED CONTEXT RETENTION ANALYSIS")
    print("=" * 40)
    
    scope_issues = 0
    context_issues = 0
    improvement_detected = 0
    
    for result in results:
        evaluation = result.get('evaluation', {})
        score = evaluation.get('score', 0)
        bias_risk = evaluation.get('bias_risk', 'UNKNOWN')
        
        # Check for scope creep (adding unrequested programs)
        response_lower = result.get('assistant_response', '').lower()
        if any(program in response_lower for program in ['web development', 'data science', 'cybersecurity', 'marketing']):
            scope_issues += 1
            print(f"⚠️  Scope creep detected in {result['test_id']}")
        
        # Check for context retention issues  
        if score < 7:
            context_issues += 1
            print(f"⚠️  Context issue in {result['test_id']}: Score {score}/10")
        else:
            improvement_detected += 1
            print(f"✅  Good context retention in {result['test_id']}: Score {score}/10")
    
    print(f"\n📊 Enhanced Context Retention Metrics:")
    print(f"• Scope Creep Issues: {scope_issues}/{len(test_cases)} (Target: 0)")
    print(f"• Context Retention Issues: {context_issues}/{len(test_cases)} (Target: <2)")
    print(f"• Improved Responses: {improvement_detected}/{len(test_cases)}")
    print(f"• Overall Average Score: {avg_score:.1f}/10 (Target: >7.5)")
    
    # Compare with previous baseline
    baseline_score = 4.2  # From previous test
    improvement = avg_score - baseline_score
    print(f"• Improvement vs Baseline: {improvement:+.1f} points")
    
    # Determine context retention quality
    if avg_score >= 8.0 and scope_issues == 0 and context_issues <= 1:
        context_quality = "EXCELLENT"
        success_message = "✅ ENHANCED CONTEXT RETENTION: EXCELLENT"
        detail_message = "Conversation history tracking successfully resolved context issues!"
    elif avg_score >= 7.0 and scope_issues <= 1 and context_issues <= 2:
        context_quality = "GOOD" 
        success_message = "✅ ENHANCED CONTEXT RETENTION: GOOD"
        detail_message = "Significant improvement achieved, minor issues remain."
    else:
        context_quality = "NEEDS_MORE_WORK"
        success_message = "❌ ENHANCED CONTEXT RETENTION: NEEDS MORE WORK"
        detail_message = "Some improvement detected, but more work needed."
    
    print(f"• Enhanced Context Quality: {context_quality}")
    
    return success, avg_score, results, scope_issues, context_issues, improvement

if __name__ == "__main__":
    print("🚀 Enhanced Context Retention Testing Framework")
    print("Testing improved Responses API with conversation history")
    print()
    
    success, score, results, scope_issues, context_issues, improvement = test_enhanced_context_retention()
    
    print(f"\n🎯 FINAL ASSESSMENT")
    print("=" * 40)
    print(f"Average Score: {score:.1f}/10")
    print(f"Improvement: {improvement:+.1f} points from baseline")
    print(f"Scope Creep: {scope_issues} issues")
    print(f"Context Issues: {context_issues} issues")
    
    if score >= 8.0 and scope_issues == 0:
        print("\n✅ SUCCESS: Enhanced context retention working excellently!")
    elif score >= 7.0 and scope_issues <= 1:
        print("\n✅ GOOD: Significant improvement achieved!")
    else:
        print("\n⚠️  PARTIAL: Some improvement, but more work needed.")
