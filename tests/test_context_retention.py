#!/usr/bin/env python3

"""
CONTEXT RETENTION TEST
Tests the assistant's ability to maintain context and properly scope responses 
based on the conversation history from our DevOps tools discussion.

Problem: The assistant showed inconsistent context retention:
- First response: Good categorization, incomplete tools list
- Second response: Scope creep - added unrequested programs  
- Third response: Excellent recovery and focus

Hypothesis: The assistant may struggle with:
1. Maintaining conversation scope across multiple exchanges
2. Understanding when to expand vs. restrict information
3. Proper context carryover in follow-up questions
"""

import os
import sys
import json
from datetime import datetime

# Add the parent directory to the path to import the framework
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from tools.prompt_optimization_template import PromptOptimizationFramework

def test_context_retention():
    """Test context retention capabilities using scenarios from the DevOps conversation."""
    
    framework = PromptOptimizationFramework()
    
    # Test cases based on the actual conversation patterns that showed issues
    test_cases = [
        {
            "id": "scope_maintenance_after_initial_response",
            "question": "Can you give me the full list of tools used in the DevOps bootcamp?",
            "expected_answer": "The DevOps bootcamp includes tools across multiple categories: Linux, Git, GitHub, AWS services (Console, CLI, EC2, S3, VPC, IAM, CloudWatch, ELB, RDS, Lambda, CloudFormation), Azure services (including AKS, CLI, Portal, Microsoft Entra), Terraform, Ansible, Docker, Docker Compose, Kubernetes, kubectl, Minikube, eksctl, GitHub Actions, SonarQube, Prometheus, Grafana, Trello/Jira, Python & boto3, YAML, Jinja2 templates. These tools are distributed across 8 units covering fundamentals, cloud computing, IaC, containerization, orchestration, CI/CD, and monitoring.",
            "rationale": "Tests initial comprehensive response quality for DevOps tools without scope creep"
        },
        {
            "id": "follow_up_scope_retention",
            "question": "Are these all the tools?",
            "expected_answer": "I should clarify that my previous response may have missed some tools mentioned in the DevOps curriculum. Let me provide a more complete list focusing specifically on the DevOps bootcamp tools from all units, including additional tools like k9s, Tshark, MySQL, NGINX, Storage Explorer, AzCopy, Grafana Loki, and cAdvisor that appear in various lab contexts throughout the curriculum.",
            "rationale": "Tests ability to handle follow-up clarification requests while maintaining DevOps-only scope"
        },
        {
            "id": "context_boundary_enforcement", 
            "question": "What about other bootcamp tools?",
            "expected_answer": "You were asking about DevOps bootcamp tools specifically. If you'd like information about tools used in other Ironhack programs like Web Development, Data Science, Cybersecurity, or others, I'd be happy to help with those separately. Should I focus on a specific program, or would you like me to continue with DevOps-related questions?",
            "rationale": "Tests ability to maintain conversation boundaries and ask for clarification rather than assuming scope expansion"
        },
        {
            "id": "conversational_context_carryover",
            "question": "How are these organized in the curriculum structure?",
            "expected_answer": "The DevOps bootcamp tools are organized across 8 main units: Unit 0 (Prework): Linux, Git, AWS, Azure; Unit 1: Git, GitHub, Linux CLI, Trello/Jira; Unit 2: AWS Console, CLI, EC2, S3, VPC, IAM, CloudWatch, Python & boto3; Unit 3: Terraform, Ansible, YAML, Jinja2; Unit 4: Docker, Docker Compose, Node.js, Java, MySQL; Unit 5: Kubernetes, kubectl, Minikube, k9s; Unit 6: Amazon EKS, eksctl, GitHub Actions, SonarQube; Units 7-8: Azure services, AKS, Prometheus, Grafana, monitoring tools. Each unit builds on previous knowledge with hands-on projects applying these tools.",
            "rationale": "Tests whether assistant remembers we're discussing DevOps tools and can provide structural context without explicit reminder"
        },
        {
            "id": "precision_over_expansion",
            "question": "Which tools are used for monitoring?",
            "expected_answer": "For monitoring in the DevOps bootcamp, the main tools are: Prometheus (for metrics collection and alerting), Grafana (for visualization and dashboards, including both self-hosted and Azure Managed versions), Grafana Loki (for log aggregation), AWS CloudWatch (for AWS resource monitoring), and cAdvisor (for container monitoring). These are primarily covered in Units 2, 6, and 8 of the curriculum.",
            "rationale": "Tests ability to extract specific subset from established context without losing focus or adding unrelated programs"
        }
    ]
    
    print("🔍 Testing Context Retention Capabilities")
    print("=" * 60)
    print("Based on DevOps tools conversation patterns that showed:")
    print("✅ Good: Initial categorization and third response recovery")  
    print("❌ Poor: Second response scope creep and unrequested information")
    print()
    
    # Run the tests
    success, avg_score, results = framework.run_optimization_tests(
        test_cases, 
        "Context Retention Test"
    )
    
    # Additional analysis specific to context retention
    print("\n📋 CONTEXT RETENTION ANALYSIS")
    print("=" * 40)
    
    scope_issues = 0
    context_issues = 0
    
    for result in results:
        evaluation = result.get('evaluation', {})
        added_info = evaluation.get('added_info', [])
        score = evaluation.get('score', 0)
        
        # Check for scope creep (adding unrequested programs)
        response_lower = result.get('assistant_response', '').lower()
        if any(program in response_lower for program in ['web development', 'data science', 'cybersecurity', 'marketing']):
            scope_issues += 1
            print(f"⚠️  Scope creep detected in {result['test_id']}")
        
        # Check for context retention issues  
        if score < 7:
            context_issues += 1
            print(f"⚠️  Context issue in {result['test_id']}: Score {score}/10")
    
    print(f"\n📊 Context Retention Metrics:")
    print(f"• Scope Creep Issues: {scope_issues}/{len(test_cases)}")
    print(f"• Context Retention Issues: {context_issues}/{len(test_cases)}")
    print(f"• Overall Average Score: {avg_score:.1f}/10")
    
    # Determine context retention quality
    context_quality = "EXCELLENT" if avg_score >= 9 and scope_issues == 0 else \
                     "GOOD" if avg_score >= 8 and scope_issues <= 1 else \
                     "NEEDS_IMPROVEMENT"
    
    print(f"• Context Retention Quality: {context_quality}")
    
    return success, avg_score, results, scope_issues, context_issues

if __name__ == "__main__":
    print("🚀 Context Retention Testing Framework")
    print("Testing assistant's ability to maintain conversation scope and context")
    print()
    
    success, score, results, scope_issues, context_issues = test_context_retention()
    
    if success and scope_issues == 0:
        print("\n✅ CONTEXT RETENTION: EXCELLENT")
        print("Assistant properly maintains conversation scope and context.")
    else:
        print("\n❌ CONTEXT RETENTION: NEEDS IMPROVEMENT") 
        print("Assistant shows context retention or scope management issues.")
