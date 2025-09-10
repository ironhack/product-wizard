#!/usr/bin/env python3
"""
Comprehensive trustworthiness test for the OpenAI Assistant.
This test asks questions and validates answers against the knowledge base.
"""
import os
import json
import time
from datetime import datetime
from openai import OpenAI
from test_config import OPENAI_API_KEY, OPENAI_ASSISTANT_ID

class TrustworthinessValidator:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.assistant_id = OPENAI_ASSISTANT_ID
        self.test_results = []
        self.knowledge_base_path = "/Users/ruds/Documents/Ironhack-Edu/product-wizard/knowledge_base/database"
        
    def load_knowledge_base_file(self, filename):
        """Load a specific knowledge base file for validation"""
        filepath = os.path.join(self.knowledge_base_path, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Warning: Could not find {filepath}")
            return None
            
    def ask_assistant(self, question):
        """Ask the assistant a question and return the response"""
        try:
            # Create a thread
            thread = self.client.beta.threads.create()
            
            # Add message to thread
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=question
            )
            
            # Run the assistant
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id
            )
            
            # Wait for completion
            while run.status in ['queued', 'in_progress', 'cancelling']:
                time.sleep(1)
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            if run.status == 'completed':
                # Get messages
                messages = self.client.beta.threads.messages.list(
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
    
    def validate_tools_answer(self, answer, course_file):
        """Validate if tools mentioned in answer are actually in the course file"""
        if not answer:
            return False, "No answer received"
            
        course_content = self.load_knowledge_base_file(course_file)
        if not course_content:
            return False, f"Could not load {course_file}"
        
        # Extract tools mentioned in the answer
        # Look for tools in common patterns
        import re
        
        # Common tool extraction patterns
        tool_patterns = [
            r'(?:Tools?:?\s*)([\w\s,.\-&/()]+?)(?:\n|$)',
            r'(?:including|using|with|learn|covers?)\s+([A-Z][a-zA-Z0-9\s,.\-&/()]+?)(?:\.|,|\n|$)',
            r'([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)',
        ]
        
        mentioned_tools = set()
        for pattern in tool_patterns:
            matches = re.findall(pattern, answer, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                # Split on common separators
                tools = re.split(r'[,;]\s*', match.strip())
                for tool in tools:
                    tool = tool.strip()
                    if len(tool) > 2 and tool not in ['The', 'This', 'These', 'All', 'And']:
                        mentioned_tools.add(tool)
        
        # Check if mentioned tools are in the course content
        missing_tools = []
        for tool in mentioned_tools:
            if tool.lower() not in course_content.lower():
                missing_tools.append(tool)
        
        if missing_tools:
            return False, f"Tools not found in curriculum: {missing_tools}"
        
        return True, "All mentioned tools found in curriculum"
    
    def validate_duration_answer(self, answer, course_files):
        """Validate duration information against course files"""
        if not answer:
            return False, "No answer received"
        
        # Extract duration numbers from answer
        import re
        duration_pattern = r'(\d+)\s*hours?'
        mentioned_durations = re.findall(duration_pattern, answer, re.IGNORECASE)
        
        # Check each course file for duration information
        found_durations = []
        for course_file in course_files:
            course_content = self.load_knowledge_base_file(course_file)
            if course_content:
                course_durations = re.findall(duration_pattern, course_content, re.IGNORECASE)
                found_durations.extend(course_durations)
        
        # Verify mentioned durations exist in course files
        for duration in mentioned_durations:
            if duration not in found_durations:
                return False, f"Duration {duration} hours not found in course files"
        
        return True, "All mentioned durations found in course files"
    
    def validate_citation_quality(self, answer):
        """Check if answer includes proper citations"""
        if not answer:
            return False, "No answer received"
        
        citation_indicators = [
            "according to",
            "based on",
            "curriculum documentation",
            "bootcamp syllabus",
            "curriculum specifies",
            "remote curriculum",
            "berlin curriculum",
            "variant"
        ]
        
        citations_found = sum(1 for indicator in citation_indicators if indicator.lower() in answer.lower())
        
        if citations_found == 0:
            return False, "No proper citations found in answer"
        elif citations_found >= 2:
            return True, "Good citation quality"
        else:
            return True, "Minimal citation present"
    
    def run_test(self, question, validation_func, validation_args=None):
        """Run a single test: ask question, get answer, validate"""
        print(f"\n🔍 Testing: {question}")
        
        # Ask the assistant
        answer = self.ask_assistant(question)
        
        if not answer:
            result = {
                'question': question,
                'answer': None,
                'validation_result': False,
                'validation_message': "Failed to get answer from assistant",
                'timestamp': datetime.now().isoformat()
            }
            self.test_results.append(result)
            print("❌ FAILED: No answer received")
            return False
        
        print(f"📝 Answer received: {answer[:200]}...")
        
        # Validate the answer
        if validation_args:
            is_valid, message = validation_func(answer, *validation_args)
        else:
            is_valid, message = validation_func(answer)
        
        result = {
            'question': question,
            'answer': answer,
            'validation_result': is_valid,
            'validation_message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        self.test_results.append(result)
        
        if is_valid:
            print(f"✅ PASSED: {message}")
            return True
        else:
            print(f"❌ FAILED: {message}")
            return False
    
    def run_comprehensive_tests(self):
        """Run a comprehensive set of trustworthiness tests"""
        print("🚀 Starting Comprehensive Trustworthiness Tests")
        print("=" * 60)
        
        # Test 1: DevOps tools accuracy
        test1_passed = self.run_test(
            "What tools and technologies are covered in the DevOps bootcamp?",
            self.validate_tools_answer,
            ["DevOps_bootcamp_2025_07.md"]
        )
        
        # Test 2: Web Development variants handling
        test2_passed = self.run_test(
            "Does the Web Development bootcamp cover SQL?",
            self.validate_citation_quality
        )
        
        # Test 3: Data Analytics duration accuracy
        test3_passed = self.run_test(
            "How long is the Data Analytics bootcamp?",
            self.validate_duration_answer,
            [["Data_Analytics_Remote_bootcamp_2025_07.md", "Data_Analytics_Berlin_onsite_bootcamp_2025_07.md"]]
        )
        
        # Test 4: UX/UI tools specificity
        test4_passed = self.run_test(
            "What design tools will I learn in the UX/UI bootcamp?",
            self.validate_tools_answer,
            ["UXUI_Remote_bootcamp_2025_07.md"]
        )
        
        # Test 5: AI Engineering program details
        test5_passed = self.run_test(
            "What programming languages are taught in the AI Engineering bootcamp?",
            self.validate_tools_answer,
            ["AI_Engineering_bootcamp_2025_07.md"]
        )
        
        # Count successful tests
        passed_tests = sum([test1_passed, test2_passed, test3_passed, test4_passed, test5_passed])
        
        print(f"\n📊 Test Results Summary:")
        print(f"Passed: {passed_tests}/5 tests")
        print(f"Success Rate: {(passed_tests/5)*100:.1f}%")
        
        return passed_tests >= 3, self.test_results
    
    def save_results(self, filename=None):
        """Save test results to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"/Users/ruds/Documents/Ironhack-Edu/product-wizard/tests/results/trustworthiness_test_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {filename}")
        return filename

def main():
    """Main test execution"""
    validator = TrustworthinessValidator()
    
    # Run tests until we get 3 good answers in a row
    consecutive_successes = 0
    max_iterations = 10
    iteration = 0
    
    while consecutive_successes < 3 and iteration < max_iterations:
        iteration += 1
        print(f"\n🔄 Iteration {iteration}")
        
        success, results = validator.run_comprehensive_tests()
        
        if success:
            consecutive_successes += 1
            print(f"✅ Success! {consecutive_successes}/3 consecutive good test sets")
        else:
            consecutive_successes = 0
            print(f"❌ Failed this iteration. Resetting counter.")
        
        # Save results for this iteration
        validator.save_results()
        
        if consecutive_successes < 3:
            print(f"\n⏱️  Waiting 30 seconds before next iteration...")
            time.sleep(30)
    
    if consecutive_successes >= 3:
        print(f"\n🎉 SUCCESS! Achieved 3 consecutive successful test sets.")
    else:
        print(f"\n⚠️  Did not achieve 3 consecutive successes in {max_iterations} iterations.")
    
    return consecutive_successes >= 3

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
