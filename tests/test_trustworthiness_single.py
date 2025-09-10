#!/usr/bin/env python3
"""
Single question trustworthiness test for the improved prompt.
"""
import os
import json
import time
from datetime import datetime
from openai import OpenAI
from test_config import OPENAI_API_KEY, OPENAI_ASSISTANT_ID

def ask_assistant(question):
    """Ask the assistant a question and return the response"""
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        # Create a thread
        thread = client.beta.threads.create()
        
        # Add message to thread
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=question
        )
        
        # Run the assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=OPENAI_ASSISTANT_ID
        )
        
        # Wait for completion
        while run.status in ['queued', 'in_progress', 'cancelling']:
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
        
        if run.status == 'completed':
            # Get messages
            messages = client.beta.threads.messages.list(
                thread_id=thread.id
            )
            
            # Get the assistant's response (latest message)
            for message in messages.data:
                if message.role == 'assistant':
                    return message.content[0].text.value
                    
        else:
            print(f"Run failed with status: {run.status}")
            return None
            
    except Exception as e:
        print(f"Error asking assistant: {e}")
        return None

def load_curriculum_file(filename):
    """Load a curriculum file for validation"""
    filepath = f"/Users/ruds/Documents/Ironhack-Edu/product-wizard/knowledge_base/database/{filename}"
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Warning: Could not find {filepath}")
        return None

def validate_devops_tools_answer(answer):
    """Manually validate the DevOps tools answer"""
    if not answer:
        return False, "No answer received"
    
    print(f"\n📄 ASSISTANT ANSWER:")
    print("=" * 60)
    print(answer)
    print("=" * 60)
    
    # Load actual curriculum
    curriculum = load_curriculum_file("DevOps_bootcamp_2025_07.md")
    if not curriculum:
        return False, "Could not load curriculum"
    
    print(f"\n🔍 MANUAL VALIDATION:")
    
    # Check for key tools that should be mentioned
    expected_tools = [
        "AWS Console", "AWS CLI", "EC2", "S3", "VPC", "IAM", "CloudWatch",
        "Azure Portal", "Azure CLI", "Microsoft Entra", "Storage Explorer",
        "Docker", "Kubernetes", "kubectl", "GitHub Actions", "SonarQube",
        "Prometheus", "Grafana", "Terraform", "Python", "boto3"
    ]
    
    found_tools = []
    missing_tools = []
    
    for tool in expected_tools:
        if tool.lower() in answer.lower():
            found_tools.append(tool)
        else:
            missing_tools.append(tool)
    
    print(f"✅ Found tools ({len(found_tools)}): {found_tools}")
    if missing_tools:
        print(f"❌ Missing tools ({len(missing_tools)}): {missing_tools}")
    
    # Check for problematic phrases that should be avoided
    problematic_phrases = [
        "comprehensive toolkit", "real-world workflows", "hands-on experience",
        "preparing students for", "world DevOps", "toolkit equips", "Great question"
    ]
    
    found_problematic = []
    for phrase in problematic_phrases:
        if phrase.lower() in answer.lower():
            found_problematic.append(phrase)
    
    if found_problematic:
        print(f"⚠️  Found problematic marketing phrases: {found_problematic}")
    else:
        print(f"✅ No problematic marketing phrases found")
    
    # Overall assessment
    tool_coverage = len(found_tools) / len(expected_tools)
    has_citation = "according to" in answer.lower() or "curriculum" in answer.lower()
    
    print(f"\n📊 ASSESSMENT:")
    print(f"Tool coverage: {tool_coverage:.1%}")
    print(f"Has proper citation: {has_citation}")
    print(f"Problematic phrases: {len(found_problematic)}")
    
    is_trustworthy = (
        tool_coverage >= 0.8 and  # At least 80% of tools mentioned
        has_citation and          # Has proper citation
        len(found_problematic) <= 2  # Minimal marketing language
    )
    
    if is_trustworthy:
        return True, f"TRUSTWORTHY: {tool_coverage:.1%} coverage, proper citations, minimal marketing language"
    else:
        return False, f"NOT TRUSTWORTHY: {tool_coverage:.1%} coverage, citation={has_citation}, marketing phrases={len(found_problematic)}"

def main():
    """Test the improved prompt with one question"""
    print("🧪 SINGLE QUESTION TRUSTWORTHINESS TEST")
    print("=" * 60)
    
    question = "What tools and technologies are covered in the DevOps bootcamp?"
    print(f"Question: {question}")
    
    # Ask the assistant
    answer = ask_assistant(question)
    
    # Validate the answer
    is_trustworthy, message = validate_devops_tools_answer(answer)
    
    print(f"\n🎯 FINAL RESULT:")
    if is_trustworthy:
        print(f"✅ PASSED: {message}")
    else:
        print(f"❌ FAILED: {message}")
    
    # Save result
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result = {
        'question': question,
        'answer': answer,
        'validation_result': is_trustworthy,
        'validation_message': message,
        'timestamp': datetime.now().isoformat()
    }
    
    os.makedirs("/Users/ruds/Documents/Ironhack-Edu/product-wizard/tests/results", exist_ok=True)
    filename = f"/Users/ruds/Documents/Ironhack-Edu/product-wizard/tests/results/single_test_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {filename}")
    
    return is_trustworthy

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
