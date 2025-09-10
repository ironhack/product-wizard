#!/usr/bin/env python3
"""
Common utilities for testing the Product Wizard assistant
"""

import openai
import sys
import os

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import OPENAI_API_KEY, OPENAI_ASSISTANT_ID
except ImportError:
    print("❌ Error: config.py not found!")
    print("   Please copy config.example.py to config.py and fill in your API credentials")
    sys.exit(1)

def get_openai_client():
    """Get configured OpenAI client"""
    return openai.OpenAI(api_key=OPENAI_API_KEY)

def get_assistant_id():
    """Get assistant ID from config"""
    return OPENAI_ASSISTANT_ID

def create_test_thread(client, question):
    """Create a thread and add a question"""
    thread = client.beta.threads.create()
    
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=question
    )
    
    return thread

def run_assistant_test(client, thread_id, assistant_id):
    """Run assistant and wait for completion"""
    import time
    
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )
    
    # Wait for completion
    start_time = time.time()
    while run.status in ["queued", "in_progress"]:
        if time.time() - start_time > 120:  # 2 minute timeout
            raise TimeoutError("Assistant run timed out")
            
        time.sleep(2)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
        )
    
    return run

def get_assistant_response(client, thread_id):
    """Get the latest assistant response from a thread"""
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    message = messages.data[0]
    
    return {
        "text": message.content[0].text.value,
        "annotations": message.content[0].text.annotations
    }

def analyze_fabrications(response_text, fabrication_traps):
    """Analyze response for potential fabrications"""
    response_lower = response_text.lower()
    
    found_fabrications = []
    for trap in fabrication_traps:
        if trap.lower() in response_lower:
            found_fabrications.append(trap)
    
    return found_fabrications

def analyze_citations(response_text, annotations):
    """Analyze citation quality"""
    import re
    
    citation_patterns = re.findall(r'【\d+:\d+†([^】]+)】', response_text)
    
    analysis = {
        "total_annotations": len(annotations),
        "citation_patterns": citation_patterns,
        "has_meaningful_citations": False,
        "file_names": []
    }
    
    # Check for meaningful citations (not just "source")
    for pattern in citation_patterns:
        if "source" not in pattern.lower() or len(pattern) > 15:
            analysis["has_meaningful_citations"] = True
            if ".txt" in pattern or ".md" in pattern:
                analysis["file_names"].append(pattern)
    
    return analysis

def print_test_header(test_name, test_number=None, total_tests=None):
    """Print formatted test header"""
    if test_number and total_tests:
        print(f"\n{'='*20} {test_name} {test_number}/{total_tests} {'='*20}")
    else:
        print(f"\n🧪 {test_name}")
        print("=" * (len(test_name) + 5))

def print_test_results(test_name, response_length, fabrications, citations_analysis):
    """Print standardized test results"""
    print(f"✅ Response: {response_length} chars")
    
    if fabrications:
        print(f"❌ Fabrications detected: {fabrications}")
    else:
        print(f"✅ No fabrications detected")
    
    print(f"📎 Citations: {citations_analysis['total_annotations']}")
    
    if citations_analysis["has_meaningful_citations"]:
        print(f"✅ Meaningful citations found")
        if citations_analysis["file_names"]:
            print(f"   Files: {citations_analysis['file_names']}")
    else:
        print(f"⚠️ Generic citations only")

def load_prompt_file(filename):
    """Load a prompt file from the project root"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prompt_path = os.path.join(project_root, filename)
    
    try:
        with open(prompt_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

def update_assistant_prompt(client, assistant_id, prompt_content):
    """Update assistant with new prompt"""
    assistant = client.beta.assistants.update(
        assistant_id=assistant_id,
        instructions=prompt_content
    )
    return assistant

def save_test_results(results, filename):
    """Save test results to JSON file"""
    import json
    
    results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "results")
    os.makedirs(results_dir, exist_ok=True)
    
    filepath = os.path.join(results_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    return filepath
