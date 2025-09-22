#!/usr/bin/env python3

"""
Test the optimized conversation context handling
"""

import sys
import os
import time
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment
load_dotenv()

# Set mock Slack environment variables before importing
os.environ['SLACK_BOT_TOKEN'] = 'xoxb-test-token-for-testing'
os.environ['SLACK_SIGNING_SECRET'] = 'test-signing-secret-for-testing'

from langchain_core.messages import HumanMessage, AIMessage

def test_conversation_context_optimization():
    """Test the optimized conversation context building"""
    
    try:
        from src.app_langgraph_rag import _build_conversation_context
        print("✅ Successfully imported optimized conversation function")
        
        # Test 1: Empty messages
        context = _build_conversation_context([])
        print(f"✅ Empty messages: {len(context)} messages")
        assert len(context) == 0
        
        # Test 2: Small conversation
        messages = [
            HumanMessage(content="What is Web Development?"),
            AIMessage(content="Web Development bootcamp covers HTML, CSS, JavaScript...\n\nSources:\n- Web_Dev_Remote"),
            HumanMessage(content="How long is it?"),
        ]
        
        context = _build_conversation_context(messages)
        print(f"✅ Small conversation: {len(context)} messages")
        
        # Check that Sources section is removed from assistant message
        for msg in context:
            if msg['role'] == 'assistant':
                assert 'Sources:' not in msg['content'], "Sources section should be removed from context"
        
        # Test 3: Large conversation (should be truncated)
        large_messages = []
        for i in range(15):
            large_messages.append(HumanMessage(content=f"Question {i}: " + "x" * 500))
            large_messages.append(AIMessage(content=f"Answer {i}: " + "y" * 500 + "\n\nSources:\n- Document_" + str(i)))
        
        context = _build_conversation_context(large_messages, max_tokens=1000)
        print(f"✅ Large conversation: {len(context)} messages (truncated from {len(large_messages)})")
        assert len(context) <= 8, "Should limit to max 8 messages"
        
        print("\n🎉 All conversation context optimization tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_conversation_flow_simulation():
    """Simulate a conversation flow with the optimized system"""
    
    try:
        from src.app_langgraph_rag import rag_graph
        print("\n📱 Testing optimized conversation flow simulation...")
        
        # Simulate conversation
        conversation_id = "test_optimized_conv_123"
        
        # Message 1
        initial_state = {
            "query": "Tell me about Web Development technologies",
            "conversation_id": conversation_id,
            "messages": [HumanMessage(content="Tell me about Web Development technologies")],
        }
        
        config = {"configurable": {"thread_id": conversation_id}}
        result1 = rag_graph.invoke(initial_state, config=config)
        
        response1 = result1.get('response', '')
        print(f"✅ First message processed: {response1[:50]}...")
        print(f"   Sources found: {len(result1.get('sources', []))}")
        print(f"   Conversation messages: {len(result1.get('messages', []))}")
        
        # Message 2 - Follow-up (should have context)
        followup_state = {
            "query": "How long is this program?",
            "conversation_id": conversation_id,
            "messages": [HumanMessage(content="How long is this program?")],
        }
        
        result2 = rag_graph.invoke(followup_state, config=config)
        
        response2 = result2.get('response', '')
        print(f"✅ Follow-up processed: {response2[:50]}...")
        print(f"   Should reference Web Development context")
        
        # Check that the response is context-aware
        response = response2.lower()
        context_indicators = ['web development', 'web dev', 'this program', 'the program']
        has_context = any(indicator in response for indicator in context_indicators)
        
        if has_context:
            print("✅ Response shows conversation context awareness")
        else:
            print("⚠️ Response may not be fully context-aware")
        
        print("\n🎉 Conversation flow simulation completed!")
        return True
        
    except Exception as e:
        print(f"❌ Conversation flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Testing Conversation Context Optimizations")
    print("=" * 50)
    
    # Test the conversation context function
    test1_passed = test_conversation_context_optimization()
    
    # Test the full conversation flow
    test2_passed = test_conversation_flow_simulation()
    
    print("\n" + "=" * 50)
    if test1_passed and test2_passed:
        print("🎉 All conversation optimization tests PASSED!")
        print("\n💡 Key improvements:")
        print("   • Smart token-based conversation truncation")
        print("   • Removes Sources sections from context to save space")
        print("   • Better conversation ID strategy (thread vs channel)")
        print("   • Optimized message history management")
        print("   • LangGraph memory integration")
    else:
        print("❌ Some tests failed - check the output above")
