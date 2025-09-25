"""
Test Slack Threading Behavior
Tests the corrected threading logic to ensure proper conversation flow
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

import unittest
from unittest.mock import Mock, patch
import time

# Import the process_message function from the actual app
from app_langgraph_rag import process_message

class TestSlackThreading(unittest.TestCase):
    """Test the Slack threading behavior to ensure proper conversation flow"""
    
    def setUp(self):
        """Set up test cases and patch SlackUpdateManager"""
        self.mock_say = Mock()
        self.slack_manager_patcher = patch('app_langgraph_rag.SlackUpdateManager')
        self.MockManager = self.slack_manager_patcher.start()
        # Configure instance methods we care about
        self.mock_manager_instance = self.MockManager.return_value
        self.mock_manager_instance.post_initial = Mock()
        self.mock_manager_instance.finalize = Mock()
        self.mock_manager_instance.error = Mock()

    def tearDown(self):
        try:
            self.slack_manager_patcher.stop()
        except Exception:
            pass
        
    def test_initial_mention_creates_thread(self):
        """Test that initial @productwizard mention creates a new thread"""
        
        # Simulate an initial mention event (no thread_ts)
        event = {
            'text': '@productwizard What bootcamps do you offer?',
            'ts': '1234567890.123456',  # Message timestamp
            'channel': 'C1234567890',
            'user': 'U1234567890'
            # No 'thread_ts' - this is a new mention
        }
        
        # Mock the LangGraph execution to focus on threading logic
        with patch('app_langgraph_rag.rag_graph.invoke') as mock_invoke:
            mock_invoke.return_value = {
                'response': 'We offer several bootcamps including Web Development, Data Science, and UX/UI Design.',
                'retrieved_docs_count': 3,
                'sources': ['Web_Dev_Remote_bootcamp_2025_07.txt'],
                'confidence': 0.9,
                'error_count': 0,
                'degraded_mode': False,
                'error_history': []
            }
            
            # Process the message
            process_message(event, self.mock_say)
            
            # Verify SlackUpdateManager was constructed with expected channel/thread_ts
            self.MockManager.assert_called()
            args, kwargs = self.MockManager.call_args
            # args: (client, channel, thread_ts)
            self.assertEqual(args[1], 'C1234567890')
            self.assertEqual(args[2], '1234567890.123456')
            # Finalize should have been called once with the assistant message
            self.mock_manager_instance.finalize.assert_called_once()
            
            print("✅ Initial mention correctly creates new thread")
    
    def test_thread_reply_continues_thread_when_mentioning_bot(self):
        """Test that replies in an existing thread continue the conversation when @mentioning the bot"""
        
        # Simulate a reply in an existing thread
        event = {
            'text': '@productwizard Tell me more about the Web Development bootcamp',
            'ts': '1234567890.234567',  # New message timestamp
            'thread_ts': '1234567890.123456',  # Original thread timestamp
            'channel': 'C1234567890',
            'user': 'U1234567890'
        }
        
        # Mock the LangGraph execution
        with patch('app_langgraph_rag.rag_graph.invoke') as mock_invoke:
            mock_invoke.return_value = {
                'response': 'The Web Development bootcamp covers HTML, CSS, JavaScript, React, Node.js, and more.',
                'retrieved_docs_count': 2,
                'sources': ['Web_Dev_Remote_bootcamp_2025_07.txt'],
                'confidence': 0.95,
                'error_count': 0,
                'degraded_mode': False,
                'error_history': []
            }
            
            # Process the message
            process_message(event, self.mock_say)
            
            # Verify SlackUpdateManager was constructed with the original thread timestamp
            self.MockManager.assert_called()
            args, kwargs = self.MockManager.call_args
            self.assertEqual(args[1], 'C1234567890')
            self.assertEqual(args[2], '1234567890.123456')
            # Finalize should have been called
            self.mock_manager_instance.finalize.assert_called_once()
            
            print("✅ Thread reply with @mention correctly continues existing thread")
    
    def test_conversation_id_consistency(self):
        """Test that conversation IDs are consistent for thread management"""
        
        # Test initial mention
        event1 = {
            'text': '@productwizard What is Data Science?',
            'ts': '1234567890.111111',
            'channel': 'C1234567890',
            'user': 'U1234567890'
        }
        
        # Test thread reply
        event2 = {
            'text': 'What technologies are covered?',
            'ts': '1234567890.222222',
            'thread_ts': '1234567890.111111',  # Reply to first message
            'channel': 'C1234567890',
            'user': 'U1234567890'
        }
        
        conversation_ids = []
        
        # Mock LangGraph to capture conversation IDs
        def capture_conversation_id(state, config):
            conversation_ids.append(config['configurable']['thread_id'])
            return {
                'response': 'Test response',
                'retrieved_docs_count': 1,
                'sources': [],
                'confidence': 0.8,
                'error_count': 0,
                'degraded_mode': False,
                'error_history': []
            }
        
        # Patch stream to capture conversation_id from config and yield a terminal result
        def fake_stream(initial_state, config=None):
            conversation_ids.append(config['configurable']['thread_id'])
            yield {'__end__': {
                'response': 'Test response',
                'retrieved_docs_count': 1,
                'sources': [],
                'confidence': 0.8,
                'error_count': 0,
                'degraded_mode': False,
                'error_history': []
            }}
        with patch('app_langgraph_rag.rag_graph.stream', side_effect=fake_stream):
            # Process both messages
            process_message(event1, self.mock_say)
            process_message(event2, self.mock_say)
            
            # Both should use the same conversation ID (based on the thread)
            self.assertEqual(len(conversation_ids), 2)
            expected_thread_id = 'thread_1234567890.111111'
            self.assertEqual(conversation_ids[0], expected_thread_id)
            self.assertEqual(conversation_ids[1], expected_thread_id)
            
            print(f"✅ Conversation ID consistency: {expected_thread_id}")
    
    def test_error_handling_preserves_threading(self):
        """Test that error messages are also sent to the correct thread"""
        
        event = {
            'text': '@productwizard This should cause an error',
            'ts': '1234567890.333333',
            'channel': 'C1234567890',
            'user': 'U1234567890'
        }
        
        # Mock LangGraph stream to raise an exception to trigger error path
        with patch('app_langgraph_rag.rag_graph.stream', side_effect=Exception("Test error")):
            process_message(event, self.mock_say)
            
            # Verify SlackUpdateManager constructed with correct thread_ts
            self.MockManager.assert_called()
            args, kwargs = self.MockManager.call_args
            self.assertEqual(args[1], 'C1234567890')
            self.assertEqual(args[2], '1234567890.333333')
            
            # Verify error method used to post error to thread
            self.mock_manager_instance.error.assert_called_once()
            
            print("✅ Error handling preserves threading")

def run_threading_tests():
    """Run all threading tests and provide a summary"""
    print("🧪 Testing Slack Threading Behavior\n")
    
    # Create test suite
    suite = unittest.TestSuite()
    suite.addTest(TestSlackThreading('test_initial_mention_creates_thread'))
    suite.addTest(TestSlackThreading('test_thread_reply_continues_thread_when_mentioning_bot'))
    suite.addTest(TestSlackThreading('test_conversation_id_consistency'))
    suite.addTest(TestSlackThreading('test_error_handling_preserves_threading'))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    result = runner.run(suite)
    
    # Provide summary
    print(f"\n📊 Threading Test Results:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   {test}: {traceback}")
    
    if result.errors:
        print("\n💥 Errors:")
        for test, traceback in result.errors:
            print(f"   {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n🎉 All threading tests passed! The Slack threading logic should work correctly.")
        print("\n📋 Expected Behavior Summary:")
        print("   1. @productwizard mentions create new threads")
        print("   2. Replies in threads continue the conversation")
        print("   3. LangGraph memory maintains context across thread messages")
        print("   4. Error messages are sent to the correct thread")
    else:
        print("\n⚠️  Some tests failed. Check the implementation.")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    run_threading_tests()
