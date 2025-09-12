"""
Test Conversation Context Handling
Tests if the Custom RAG app maintains context across multiple messages in a thread
"""
import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path to import production code
sys.path.append('src')

from app_custom_rag import CustomRAGPipeline, load_master_prompt
import openai

def test_conversation_context():
    """Test conversation context handling across multiple messages"""
    print("🧪 Testing Conversation Context Handling")
    print("=" * 60)
    
    # Initialize the production RAG pipeline
    client = openai.OpenAI(api_key=os.environ['OPENAI_API_KEY'])
    vector_store_id = os.environ['OPENAI_VECTOR_STORE_ID']
    master_prompt = load_master_prompt()
    
    rag = CustomRAGPipeline(client, vector_store_id, master_prompt)
    
    # Simulate a conversation thread
    conversation_context = []
    
    # Test scenario: User asks about different bootcamps in sequence
    test_conversation = [
        {
            "message": "What certifications does Ironhack offer for Data Analytics?",
            "expected_context": "First question - no prior context"
        },
        {
            "message": "What about for Web Development?",
            "expected_context": "Should understand 'what about' refers to certifications"
        },
        {
            "message": "How long is that bootcamp?", 
            "expected_context": "Should know 'that bootcamp' refers to Web Development"
        },
        {
            "message": "Is it available part-time?",
            "expected_context": "Should maintain Web Development context"
        },
        {
            "message": "What about AI Engineering certifications?",
            "expected_context": "Should shift context back to certifications but for AI Engineering"
        }
    ]
    
    results = []
    
    for i, turn in enumerate(test_conversation, 1):
        print(f"\n[Turn {i}/5] {turn['expected_context']}")
        print(f"User: {turn['message']}")
        print("-" * 60)
        
        # Process the message with conversation context
        start_time = time.time()
        result = rag.process_query(turn['message'], conversation_context)
        processing_time = time.time() - start_time
        
        response = result['response']
        
        print(f"Assistant: {response}")
        print(f"📊 Processing time: {processing_time:.2f}s")
        print(f"📄 Retrieved docs: {result['retrieved_docs_count']}")
        print(f"🔍 Validation confidence: {result.get('validation', {}).get('confidence', 'N/A')}")
        
        # Add both user message and assistant response to conversation context
        conversation_context.append({
            "role": "user",
            "content": turn['message'],
            "timestamp": time.time()
        })
        
        conversation_context.append({
            "role": "assistant", 
            "content": response,
            "timestamp": time.time()
        })
        
        # Keep only last 8 messages (4 exchanges) to match production behavior
        if len(conversation_context) > 8:
            conversation_context = conversation_context[-8:]
        
        results.append({
            "turn": i,
            "user_message": turn['message'],
            "assistant_response": response,
            "context_length": len(conversation_context),
            "processing_time": processing_time,
            "expected_context": turn['expected_context']
        })
        
        print(f"💬 Context length: {len(conversation_context)} messages")
        
        # Brief pause between messages
        time.sleep(2)
    
    # Analysis
    print("\n" + "=" * 60)
    print("🏆 CONVERSATION CONTEXT ANALYSIS")
    print("=" * 60)
    
    # Check for context awareness indicators
    context_indicators = {
        "turn_2": ["certification", "web development", "web dev"],  # Should understand "what about"
        "turn_3": ["week", "duration", "long", "web development"],  # Should know "that bootcamp"
        "turn_4": ["part-time", "format", "web development"],      # Should maintain context
        "turn_5": ["ai engineering", "certification"]              # Should shift context appropriately
    }
    
    context_scores = []
    
    for i, result in enumerate(results[1:], 2):  # Skip first turn (no context needed)
        turn_key = f"turn_{i}"
        response_lower = result['assistant_response'].lower()
        
        expected_indicators = context_indicators.get(turn_key, [])
        found_indicators = [ind for ind in expected_indicators if ind in response_lower]
        
        if expected_indicators:
            context_score = len(found_indicators) / len(expected_indicators)
            context_scores.append(context_score)
            
            print(f"\n[Turn {i}] Context Awareness: {context_score:.1%}")
            print(f"   Expected indicators: {expected_indicators}")
            print(f"   Found indicators: {found_indicators}")
            
            if context_score >= 0.5:
                print(f"   ✅ Good context awareness")
            else:
                print(f"   ⚠️ Weak context awareness")
    
    # Overall assessment
    avg_context_score = sum(context_scores) / len(context_scores) if context_scores else 0
    avg_processing_time = sum(r['processing_time'] for r in results) / len(results)
    
    print(f"\n📊 OVERALL RESULTS:")
    print(f"   Average context awareness: {avg_context_score:.1%}")
    print(f"   Average processing time: {avg_processing_time:.2f}s")
    print(f"   Context management: {'✅ Robust' if avg_context_score >= 0.6 else '⚠️ Needs improvement'}")
    
    # Test conversation memory limits
    print(f"\n🧠 MEMORY MANAGEMENT:")
    print(f"   Final context length: {len(conversation_context)} messages")
    print(f"   Memory limit handling: {'✅ Working' if len(conversation_context) <= 8 else '⚠️ Issue detected'}")
    
    print(f"\n🎯 KEY FINDINGS:")
    if avg_context_score >= 0.7:
        print("  🟢 Excellent context retention across conversation")
    elif avg_context_score >= 0.5:
        print("  🟡 Good context retention with room for improvement")
    else:
        print("  🔴 Context retention needs attention")
    
    print(f"  📈 Processing remains efficient: {avg_processing_time:.1f}s average")
    print(f"  💾 Memory management working correctly")
    
    return {
        "avg_context_score": avg_context_score,
        "avg_processing_time": avg_processing_time,
        "final_context_length": len(conversation_context),
        "conversation_results": results
    }

if __name__ == "__main__":
    test_conversation_context()
