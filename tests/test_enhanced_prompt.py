#!/usr/bin/env python3
"""
Test script for enhanced prompt with systematic tool extraction.
This tests the V6 prompt against the DevOps tools categorization question.
"""

import openai
import os
import sys
import time
import json
from datetime import datetime

# Load environment variables from .env file manually
def load_env_file():
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

load_env_file()

# Add the src directory to the path to import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def load_enhanced_prompt():
    """Load the enhanced V6 prompt"""
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'development', 'MASTER_PROMPT_V6_ENHANCED_TOOLS.md')
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read()

def create_test_assistant(enhanced_prompt):
    """Create a temporary assistant with the enhanced prompt"""
    try:
        # Get the vector store ID from the existing assistant
        existing_assistant_id = os.environ["OPENAI_ASSISTANT_ID"]
        existing_assistant = openai.beta.assistants.retrieve(assistant_id=existing_assistant_id)
        
        vector_store_ids = []
        if hasattr(existing_assistant, 'tool_resources') and existing_assistant.tool_resources:
            if hasattr(existing_assistant.tool_resources, 'file_search') and existing_assistant.tool_resources.file_search:
                vector_store_ids = existing_assistant.tool_resources.file_search.vector_store_ids
        
        # Create new test assistant with enhanced prompt
        test_assistant = openai.beta.assistants.create(
            name="Product Wizard V6 Test - Enhanced Tools",
            instructions=enhanced_prompt,
            model="gpt-4o",
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {
                    "vector_store_ids": vector_store_ids
                }
            }
        )
        
        print(f"Created test assistant: {test_assistant.id}")
        return test_assistant.id
        
    except Exception as e:
        print(f"Error creating test assistant: {e}")
        return None

def test_devops_tools_question(assistant_id):
    """Test the DevOps tools categorization question"""
    test_question = "can you give me the full list of tools used in the DevOps bootcamp? grouped into four categories."
    
    try:
        # Create a new thread
        thread = openai.beta.threads.create()
        
        # Add the test question
        openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=test_question
        )
        
        # Run the assistant
        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id
        )
        
        print(f"Created run: {run.id}")
        print("Waiting for response...")
        
        # Wait for completion
        while run.status in ["queued", "in_progress"]:
            time.sleep(2)
            run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            print(f"Run status: {run.status}")
        
        if run.status == "completed":
            # Get the response
            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            response = messages.data[0].content[0].text.value
            
            return {
                "question": test_question,
                "response": response,
                "status": "success",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "question": test_question,
                "error": f"Run failed with status: {run.status}",
                "status": "failed",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        return {
            "question": test_question,
            "error": str(e),
            "status": "error",
            "timestamp": datetime.now().isoformat()
        }

def cleanup_test_assistant(assistant_id):
    """Clean up the test assistant"""
    try:
        openai.beta.assistants.delete(assistant_id)
        print(f"Deleted test assistant: {assistant_id}")
    except Exception as e:
        print(f"Error deleting test assistant: {e}")

def analyze_response(response_text):
    """Analyze the response for completeness"""
    print("\n" + "="*80)
    print("RESPONSE ANALYSIS")
    print("="*80)
    
    # Tools that should be present based on curriculum review
    expected_tools = {
        "Infrastructure & Cloud": [
            "AWS Console", "AWS CLI", "EC2", "S3", "VPC", "IAM", "CloudWatch", 
            "ELB", "RDS", "Lambda", "CloudFormation", "Azure", "Azure CLI", 
            "Azure Portal", "Microsoft Entra", "Storage Explorer", "AzCopy", 
            "Terraform", "Python", "boto3"
        ],
        "Containerization & Orchestration": [
            "Docker", "Docker Compose", "Kubernetes", "kubectl", "Minikube", 
            "k9s", "Amazon EKS", "Azure Kubernetes Service", "eksctl"
        ],
        "CI/CD & Automation": [
            "GitHub Actions", "SonarQube", "Git", "GitHub", "Ansible", 
            "YAML", "Jinja2"
        ],
        "Monitoring & Observability": [
            "Prometheus", "Grafana", "Grafana Loki", "cAdvisor"
        ]
    }
    
    # Check for presence of tools
    found_tools = {category: [] for category in expected_tools.keys()}
    missing_tools = {category: [] for category in expected_tools.keys()}
    
    response_lower = response_text.lower()
    
    for category, tools in expected_tools.items():
        for tool in tools:
            if tool.lower() in response_lower:
                found_tools[category].append(tool)
            else:
                missing_tools[category].append(tool)
    
    # Print analysis
    for category in expected_tools.keys():
        print(f"\n{category}:")
        print(f"  Found ({len(found_tools[category])}): {', '.join(found_tools[category])}")
        if missing_tools[category]:
            print(f"  Missing ({len(missing_tools[category])}): {', '.join(missing_tools[category])}")
    
    # Calculate completeness score
    total_expected = sum(len(tools) for tools in expected_tools.values())
    total_found = sum(len(tools) for tools in found_tools.values())
    completeness_score = (total_found / total_expected) * 100
    
    print(f"\nCompleteness Score: {completeness_score:.1f}% ({total_found}/{total_expected} tools)")
    
    # Check for systematic extraction indicators
    systematic_indicators = [
        "systematically reviewed",
        "all units",
        "complete list",
        "all tools specified",
        "reviewed all units"
    ]
    
    found_indicators = [indicator for indicator in systematic_indicators if indicator in response_lower]
    print(f"Systematic Extraction Indicators: {found_indicators}")
    
    return {
        "completeness_score": completeness_score,
        "total_found": total_found,
        "total_expected": total_expected,
        "found_tools": found_tools,
        "missing_tools": missing_tools,
        "systematic_indicators": found_indicators
    }

def main():
    """Main test function"""
    print("Enhanced Prompt Testing - DevOps Tools Categorization")
    print("="*60)
    
    # Load enhanced prompt
    print("Loading enhanced V6 prompt...")
    enhanced_prompt = load_enhanced_prompt()
    print(f"Loaded prompt ({len(enhanced_prompt)} characters)")
    
    # Create test assistant
    print("\nCreating test assistant...")
    test_assistant_id = create_test_assistant(enhanced_prompt)
    
    if not test_assistant_id:
        print("Failed to create test assistant. Exiting.")
        return
    
    try:
        # Test the question
        print("\nTesting DevOps tools question...")
        result = test_devops_tools_question(test_assistant_id)
        
        # Save results
        results_path = os.path.join(os.path.dirname(__file__), 'results', 'enhanced_prompt_test.json')
        os.makedirs(os.path.dirname(results_path), exist_ok=True)
        
        if result["status"] == "success":
            print("\n" + "="*80)
            print("RESPONSE:")
            print("="*80)
            print(result["response"])
            
            # Analyze the response
            analysis = analyze_response(result["response"])
            result["analysis"] = analysis
            
            print(f"\nOverall Assessment:")
            if analysis["completeness_score"] >= 90:
                print("✅ EXCELLENT - High completeness score")
            elif analysis["completeness_score"] >= 75:
                print("✅ GOOD - Acceptable completeness score")
            elif analysis["completeness_score"] >= 50:
                print("⚠️  FAIR - Some tools missing")
            else:
                print("❌ POOR - Many tools missing")
                
            if analysis["systematic_indicators"]:
                print("✅ SYSTEMATIC - Shows evidence of systematic extraction")
            else:
                print("⚠️  UNSYSTEMATIC - No clear evidence of systematic extraction")
        
        else:
            print(f"Test failed: {result.get('error', 'Unknown error')}")
        
        with open(results_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\nResults saved to: {results_path}")
        
    finally:
        # Cleanup
        print(f"\nCleaning up test assistant...")
        cleanup_test_assistant(test_assistant_id)
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()
