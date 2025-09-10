#!/usr/bin/env python3
"""
Slack Thread Simulation Test for Responses API
Tests the actual conversation flow that happens when users chat in Slack threads
"""

import os
import sys
import openai
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Add the src directory to the path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Load environment variables
load_dotenv()

def load_master_prompt():
    """Load the master prompt from the assistant config"""
    try:
        with open('../assistant_config/MASTER_PROMPT.md', 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading master prompt: {e}")
        return "You are a helpful assistant for Ironhack course information."

def simulate_slack_conversation():
    """Simulate a realistic Slack conversation thread"""
    
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    vector_store_id = os.environ.get("OPENAI_VECTOR_STORE_ID", "vs_68c14625e8d88191a27acb8a3845a706")
    master_prompt = load_master_prompt()
    
    print("🗣️ SLACK THREAD CONVERSATION SIMULATION")
    print("=" * 60)
    print("Simulating a realistic conversation flow where a user asks follow-up questions")
    print("in the same Slack thread, just like your actual users do.")
    print("=" * 60)
    
    # Conversation scenario: A prospective student asking about DevOps
    conversation_flow = [
        {
            "user": "Student",
            "message": "Hi! I'm interested in the DevOps bootcamp. What tools will I learn?",
            "context": "Initial question - should get comprehensive tool list"
        },
        {
            "user": "Student", 
            "message": "That's a lot of tools! How long is the DevOps course?",
            "context": "Follow-up about duration - should reference previous context"
        },
        {
            "user": "Student",
            "message": "And what about AWS specifically? What AWS services are covered?",
            "context": "Drilling down on specific topic mentioned before"
        },
        {
            "user": "Student",
            "message": "Is there any overlap with the Data Science bootcamp?",
            "context": "Comparison question - should distinguish between courses"
        },
        {
            "user": "Student",
            "message": "Perfect! What are the prerequisites for DevOps?",
            "context": "Practical question about enrollment requirements"
        }
    ]
    
    conversation_data = {"previous_response_id": None}
    all_responses = []
    success_count = 0
    
    for i, turn in enumerate(conversation_flow, 1):
        print(f"\n💬 Turn {i}/5: {turn['context']}")
        print(f"👤 {turn['user']}: {turn['message']}")
        print("🤖 Product Wizard: ", end="", flush=True)
        
        try:
            # Prepare request (same as actual Slack app)
            request_params = {
                "model": "gpt-4o",
                "input": turn['message'],
                "instructions": master_prompt,
                "tools": [
                    {
                        "type": "file_search",
                        "vector_store_ids": [vector_store_id]
                    }
                ]
            }
            
            # Add previous_response_id for context (critical for thread continuity)
            if conversation_data.get("previous_response_id"):
                request_params["previous_response_id"] = conversation_data["previous_response_id"]
            
            start_time = time.time()
            
            # Make the Responses API call
            response = client.responses.create(**request_params)
            
            response_time = time.time() - start_time
            
            # Extract the assistant's response (same logic as app_responses.py)
            assistant_message = "I apologize, but I couldn't generate a proper response."
            
            if response.output and len(response.output) > 0:
                for output_item in response.output:
                    if hasattr(output_item, 'type') and output_item.type == 'message':
                        if hasattr(output_item, 'content') and len(output_item.content) > 0:
                            content = output_item.content[0]
                            if hasattr(content, 'text'):
                                assistant_message = content.text
                                break
            
            # Update conversation data (same as app_responses.py)
            conversation_data["previous_response_id"] = response.id
            
            # Show response preview
            preview = assistant_message[:150] + "..." if len(assistant_message) > 150 else assistant_message
            print(preview)
            
            # Analyze response quality
            response_analysis = analyze_response_quality(turn, assistant_message, i)
            
            print(f"⏱️  Response time: {response_time:.2f}s")
            print(f"📊 Quality score: {response_analysis['quality_score']:.1%}")
            print(f"🔗 Context awareness: {'✅' if response_analysis['context_aware'] else '❌'}")
            
            if response_analysis['quality_score'] >= 0.7:
                success_count += 1
            
            # Store for detailed analysis
            turn_result = {
                "turn": i,
                "user_message": turn['message'],
                "assistant_response": assistant_message,
                "response_time": response_time,
                "response_id": response.id,
                "previous_response_id": request_params.get("previous_response_id"),
                "analysis": response_analysis
            }
            all_responses.append(turn_result)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            all_responses.append({
                "turn": i,
                "user_message": turn['message'],
                "error": str(e),
                "response_time": 0,
                "analysis": {"quality_score": 0, "context_aware": False}
            })
    
    print("\n" + "=" * 60)
    print("📈 CONVERSATION ANALYSIS")
    print("=" * 60)
    
    # Analyze conversation flow
    analyze_conversation_flow(all_responses)
    
    # Overall assessment
    success_rate = success_count / len(conversation_flow)
    avg_response_time = sum(r.get('response_time', 0) for r in all_responses) / len(all_responses)
    
    print(f"\n🎯 OVERALL SLACK THREAD SIMULATION RESULTS:")
    print(f"Success Rate: {success_count}/{len(conversation_flow)} ({success_rate:.1%})")
    print(f"Average Response Time: {avg_response_time:.2f}s")
    
    # Context chain validation
    context_chain_valid = validate_context_chain(all_responses)
    print(f"Context Chain Integrity: {'✅ PASS' if context_chain_valid else '❌ FAIL'}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"results/slack_thread_simulation_{timestamp}.json"
    
    os.makedirs("results", exist_ok=True)
    
    simulation_results = {
        "timestamp": timestamp,
        "api_type": "Responses API",
        "scenario": "Slack thread conversation simulation",
        "success_rate": success_rate,
        "average_response_time": avg_response_time,
        "context_chain_valid": context_chain_valid,
        "conversation_turns": all_responses
    }
    
    with open(results_file, 'w') as f:
        json.dump(simulation_results, f, indent=2)
    
    print(f"📁 Detailed results saved to: {results_file}")
    
    # Final recommendation
    if success_rate >= 0.8 and context_chain_valid:
        print(f"\n✅ SLACK THREAD SIMULATION PASSED")
        print(f"   The Responses API handles threaded conversations well!")
        print(f"   Your users will have a seamless experience.")
        return True
    else:
        print(f"\n⚠️ SLACK THREAD SIMULATION NEEDS ATTENTION")
        print(f"   Some issues detected in conversation flow.")
        return False

def analyze_response_quality(turn, response, turn_number):
    """Analyze the quality and appropriateness of a response"""
    
    analysis = {
        "quality_score": 0,
        "context_aware": False,
        "relevant_keywords": [],
        "issues": []
    }
    
    if not response or len(response) < 10:
        analysis["issues"].append("Response too short")
        return analysis
    
    # Check for turn-specific expectations
    if turn_number == 1:  # Initial tools question
        expected_keywords = ["AWS", "Docker", "Kubernetes", "tools", "DevOps"]
        found_keywords = [kw for kw in expected_keywords if kw.lower() in response.lower()]
        analysis["relevant_keywords"] = found_keywords
        analysis["quality_score"] = len(found_keywords) / len(expected_keywords)
        
    elif turn_number == 2:  # Duration question
        expected_keywords = ["hours", "duration", "long", "time"]
        found_keywords = [kw for kw in expected_keywords if kw.lower() in response.lower()]
        analysis["relevant_keywords"] = found_keywords
        analysis["quality_score"] = min(1.0, len(found_keywords) / 2)  # Need at least 2
        
    elif turn_number == 3:  # AWS specific question
        expected_keywords = ["AWS", "EC2", "S3", "IAM", "services"]
        found_keywords = [kw for kw in expected_keywords if kw.lower() in response.lower()]
        analysis["relevant_keywords"] = found_keywords
        analysis["quality_score"] = len(found_keywords) / len(expected_keywords)
        # Check if it references previous context
        if "mentioned" in response.lower() or "covered" in response.lower():
            analysis["context_aware"] = True
            
    elif turn_number == 4:  # Comparison question
        expected_keywords = ["Data Science", "different", "DevOps", "overlap"]
        found_keywords = [kw for kw in expected_keywords if kw.lower() in response.lower()]
        analysis["relevant_keywords"] = found_keywords
        analysis["quality_score"] = len(found_keywords) / len(expected_keywords)
        
    elif turn_number == 5:  # Prerequisites question
        # This should ideally say "no specific information" since prerequisites aren't in curriculum
        if "don't have that specific information" in response.lower():
            analysis["quality_score"] = 1.0
            analysis["context_aware"] = True
        else:
            analysis["quality_score"] = 0.5  # Partial credit if it tries to answer
    
    # Check for proper citations
    if "curriculum" in response.lower() or "documentation" in response.lower():
        analysis["quality_score"] = min(1.0, analysis["quality_score"] + 0.2)
    
    # Check for context awareness (references to previous conversation)
    context_indicators = ["as mentioned", "previously", "earlier", "that", "those tools", "the tools"]
    if any(indicator in response.lower() for indicator in context_indicators) and turn_number > 1:
        analysis["context_aware"] = True
    
    return analysis

def analyze_conversation_flow(responses):
    """Analyze the overall conversation flow and coherence"""
    
    print("🔍 Conversation Flow Analysis:")
    
    for i, response in enumerate(responses, 1):
        if 'error' in response:
            print(f"Turn {i}: ❌ FAILED - {response['error']}")
            continue
            
        analysis = response.get('analysis', {})
        quality = analysis.get('quality_score', 0)
        context_aware = analysis.get('context_aware', False)
        keywords = analysis.get('relevant_keywords', [])
        
        status = "✅ GOOD" if quality >= 0.7 else "⚠️ WEAK" if quality >= 0.4 else "❌ POOR"
        context_status = "🔗" if context_aware else "🔸"
        
        print(f"Turn {i}: {status} (Q:{quality:.2f}) {context_status} Keywords: {keywords}")

def validate_context_chain(responses):
    """Validate that the conversation maintains proper context chain"""
    
    print(f"\n🔗 Context Chain Validation:")
    
    # Check that each response (except first) has a previous_response_id
    for i, response in enumerate(responses):
        if 'error' in response:
            continue
            
        if i == 0:
            # First response shouldn't have previous_response_id
            if response.get('previous_response_id'):
                print(f"Turn {i+1}: ⚠️ Unexpected previous_response_id in first turn")
            else:
                print(f"Turn {i+1}: ✅ First turn correctly has no previous context")
        else:
            # Subsequent responses should have previous_response_id
            if response.get('previous_response_id'):
                print(f"Turn {i+1}: ✅ Has previous_response_id: {response['previous_response_id'][:20]}...")
            else:
                print(f"Turn {i+1}: ❌ Missing previous_response_id")
                return False
    
    # Check that response_ids form a proper chain
    response_ids = [r.get('response_id') for r in responses if 'response_id' in r]
    previous_ids = [r.get('previous_response_id') for r in responses if 'previous_response_id' in r]
    
    # Each previous_id should match a previous response_id
    chain_valid = True
    for i, prev_id in enumerate(previous_ids):
        if prev_id not in response_ids[:i+1]:  # Should be in earlier responses
            print(f"Turn {i+2}: ❌ Previous response ID not found in chain")
            chain_valid = False
    
    if chain_valid:
        print("✅ Context chain integrity validated")
    
    return chain_valid

if __name__ == "__main__":
    success = simulate_slack_conversation()
    sys.exit(0 if success else 1)
