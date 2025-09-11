#!/usr/bin/env python3

"""
CONVERSATION SIMULATION TEST
Tests the enhanced context retention by simulating a real conversation flow
where each question builds on the previous exchange.
"""

import os
import sys
import json
import time
from datetime import datetime

# Add the parent directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from tools.prompt_optimization_template import PromptOptimizationFramework

def test_conversation_simulation():
    """Test conversation simulation with progressive context building."""
    
    framework = PromptOptimizationFramework()
    
    print("🔗 Testing Conversation Simulation")
    print("=" * 60)
    print("Simulating a real conversation flow to test context retention")
    print()
    
    # Simulate a conversation by making sequential calls
    conversation_flow = [
        {
            "question": "Can you give me the full list of tools used in the DevOps bootcamp?",
            "expected_behavior": "Should provide comprehensive DevOps tools list"
        },
        {
            "question": "Are these all the tools mentioned in the curriculum?",
            "expected_behavior": "Should maintain DevOps context and clarify additional lab tools"
        },
        {
            "question": "What about tools for other programs?",
            "expected_behavior": "Should ask for clarification rather than expand scope"
        },
        {
            "question": "How are the DevOps tools organized in the curriculum?", 
            "expected_behavior": "Should remember we're discussing DevOps and provide unit structure"
        },
        {
            "question": "Which of those tools are specifically for monitoring?",
            "expected_behavior": "Should extract monitoring tools from DevOps context"
        }
    ]
    
    results = []
    for i, exchange in enumerate(conversation_flow, 1):
        print(f"\n[Exchange {i}/5] {exchange['question']}")
        print(f"Expected: {exchange['expected_behavior']}")
        
        # Make the API call
        start_time = time.time()
        assistant_response = framework.ask_assistant_with_master_prompt(exchange['question'])
        end_time = time.time()
        
        print(f"✅ Response received ({end_time - start_time:.1f}s)")
        print(f"📝 Response preview: {assistant_response[:200]}...")
        
        # Quick analysis for context issues
        response_lower = assistant_response.lower()
        has_scope_creep = any(program in response_lower for program in [
            'web development', 'data science', 'cybersecurity', 'marketing'
        ])
        
        maintains_devops_focus = 'devops' in response_lower or (
            i == 1 or any(tool in response_lower for tool in [
                'terraform', 'ansible', 'kubernetes', 'docker', 'prometheus'
            ])
        )
        
        results.append({
            'exchange': i,
            'question': exchange['question'],
            'response': assistant_response,
            'has_scope_creep': has_scope_creep,
            'maintains_devops_focus': maintains_devops_focus,
            'response_time': end_time - start_time
        })
        
        if has_scope_creep:
            print("⚠️  Scope creep detected!")
        if maintains_devops_focus:
            print("✅ Maintains DevOps focus")
        else:
            print("❌ Lost DevOps context")
        
        # Small delay to allow context to be processed
        time.sleep(1)
    
    # Analyze overall conversation quality
    print(f"\n📊 CONVERSATION ANALYSIS")
    print("=" * 40)
    
    scope_creep_count = sum(1 for r in results if r['has_scope_creep'])
    context_retention_count = sum(1 for r in results if r['maintains_devops_focus'])
    avg_response_time = sum(r['response_time'] for r in results) / len(results)
    
    print(f"• Scope Creep Issues: {scope_creep_count}/{len(results)}")
    print(f"• Context Retention: {context_retention_count}/{len(results)}")
    print(f"• Average Response Time: {avg_response_time:.1f}s")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"tests/results/conversation_simulation_{timestamp}.json"
    
    os.makedirs("tests/results", exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'test_type': 'Conversation Simulation',
            'scope_creep_issues': scope_creep_count,
            'context_retention_score': context_retention_count,
            'avg_response_time': avg_response_time,
            'exchanges': results
        }, f, indent=2)
    
    print(f"• Results saved to: {results_file}")
    
    # Determine success
    if scope_creep_count == 0 and context_retention_count >= 4:
        quality = "EXCELLENT"
        print(f"\n✅ CONVERSATION QUALITY: {quality}")
        print("Context retention is working well across conversation flow!")
    elif scope_creep_count <= 1 and context_retention_count >= 3:
        quality = "GOOD"
        print(f"\n✅ CONVERSATION QUALITY: {quality}")
        print("Good context retention with minor issues.")
    else:
        quality = "NEEDS_IMPROVEMENT"
        print(f"\n❌ CONVERSATION QUALITY: {quality}")
        print("Context retention issues detected in conversation flow.")
    
    return quality, scope_creep_count, context_retention_count, results

if __name__ == "__main__":
    print("🚀 Conversation Simulation Testing")
    print("Testing real conversation flow with context retention")
    print()
    
    quality, scope_issues, context_score, results = test_conversation_simulation()
    
    print(f"\n🎯 SIMULATION SUMMARY")
    print(f"Quality: {quality}")
    print(f"Scope Issues: {scope_issues}")
    print(f"Context Score: {context_score}/5")
    
    if quality == "EXCELLENT":
        print("\n🎉 Enhanced context retention is working!")
    elif quality == "GOOD":
        print("\n👍 Solid improvement achieved!")
    else:
        print("\n⚠️  More work needed on context retention.")
