"""
Custom RAG Slack App with Hybrid Architecture
Combines the best of both worlds:
- Responses API for reliable vector store retrieval
- Chat Completions API for controlled generation with validation
- Full Slack integration and conversation context management
"""

from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request
import openai
import os
import logging
import re
import time
import json
import tempfile
import fcntl
from collections import OrderedDict

# Set up logging - show info level for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Slack app only if running as main module
if __name__ == "__main__":
    slack_app = App(
        token=os.environ["SLACK_BOT_TOKEN"],
        signing_secret=os.environ["SLACK_SIGNING_SECRET"]
    )
    handler = SlackRequestHandler(slack_app)
else:
    # When imported as module, don't initialize Slack
    slack_app = None
    handler = None

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Vector Store ID for file search
VECTOR_STORE_ID = os.environ.get("OPENAI_VECTOR_STORE_ID", "vs_68c14625e8d88191a27acb8a3845a706")

# Load the master prompt
def load_master_prompt():
    try:
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prompt_path = os.path.join(script_dir, 'assistant_config', 'MASTER_PROMPT.md')
        with open(prompt_path, 'r') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading master prompt: {e}")
        return "You are a helpful assistant for Ironhack course information."

MASTER_PROMPT = load_master_prompt()

# Custom RAG Pipeline Class
class CustomRAGPipeline:
    def __init__(self, client, vector_store_id, master_prompt):
        self.client = client
        self.vector_store_id = vector_store_id
        self.master_prompt = master_prompt
    
    def _get_retrieval_instructions(self, query):
        """Generate enhanced retrieval instructions based on query type"""
        query_lower = query.lower()
        
        # Detect comparison queries that need multiple documents
        comparison_keywords = ['difference', 'compare', 'comparison', 'vs', 'versus', 'remote vs', 'onsite vs', 'berlin vs']
        program_variants = ['remote', 'berlin', 'onsite', 'online']
        
        is_comparison = any(keyword in query_lower for keyword in comparison_keywords)
        has_variants = any(variant in query_lower for variant in program_variants)
        
        if is_comparison or has_variants:
            return """Search for ALL relevant documents that contain information about the topics mentioned in the query. 
            For comparison queries, retrieve documents for each program variant mentioned (e.g., both Remote and Berlin versions).
            For program-specific queries, look for documents that specifically match the program format mentioned.
            Include comprehensive information from multiple sources when available."""
        
        # Detect broad overview queries that benefit from comprehensive information
        overview_keywords = ['tell me about', 'overview', 'explain', 'describe', 'what is', 'comprehensive']
        is_overview = any(keyword in query_lower for keyword in overview_keywords)
        
        if is_overview:
            return """Search for comprehensive information about the topic. Retrieve documents that provide 
            complete details including program structure, curriculum, tools, career outcomes, and any relevant specifics.
            Look for the most detailed and comprehensive sources available."""
        
        # Default instruction for specific queries
        return "Search for relevant documents and return the most accurate and complete information found."
    
    def retrieve_documents(self, query):
        """Retrieve documents using Responses API (reliable vector store access)"""
        try:
            logger.info(f"🔍 Retrieving documents from vector store for: {query}")
            
            # Enhanced instructions for better multi-document retrieval
            enhanced_instructions = self._get_retrieval_instructions(query)
            
            # Use Responses API for retrieval only
            response = self.client.responses.create(
                model="gpt-4o",
                input=[{"role": "user", "content": query}],
                instructions=enhanced_instructions,
                tools=[{
                    "type": "file_search",
                    "vector_store_ids": [self.vector_store_id]
                }]
            )
            
            # Extract retrieved content from annotations with file names
            retrieved_content = []
            sources = set()
            file_names = []
            
            if response.output:
                for output_item in response.output:
                    if hasattr(output_item, 'content'):
                        for content_item in output_item.content:
                            if hasattr(content_item, 'text'):
                                retrieved_content.append(content_item.text)
                                
                                # Extract file information directly from annotations
                                if hasattr(content_item, 'annotations'):
                                    for annotation in content_item.annotations:
                                        if hasattr(annotation, 'filename') and hasattr(annotation, 'type'):
                                            if annotation.type == 'file_citation':
                                                # Extract filename without extension for clean citation
                                                file_name = annotation.filename.replace('.txt', '')
                                                file_names.append(file_name)
                                                sources.add(file_name)
                                                logger.info(f"📄 Found specific file: {file_name}")
                                                break  # Only need one source per content block
                                
                                # Only keep real sources from API - no fallback
            
            
            logger.info(f"✅ Vector store search completed: {len(retrieved_content)} documents retrieved")
            logger.info(f"📄 Sources found: {sources}")
            
            return retrieved_content, list(sources)
            
        except Exception as e:
            logger.error(f"❌ Error retrieving documents: {e}")
            return [], []
    
    def generate_response(self, query, retrieved_docs, conversation_context=None, sources=None):
        """Generate response using Chat Completions API with retrieved documents"""
        try:
            logger.info(f"🤖 Generating response with {len(retrieved_docs)} documents")
            
            # Prepare context from retrieved documents
            context = "\n\n".join(retrieved_docs) if retrieved_docs else ""
            
            # Build messages array with conversation context
            messages = []
            
            # Build source reference for natural citations
            sources = sources or []
            if sources:
                if len(sources) == 1:
                    source_info = f"Source: {sources[0]}"
                else:
                    source_info = f"Sources: {', '.join(sources)}"
                    logger.info(f"📚 Multi-document retrieval: {len(sources)} sources found")
            else:
                source_info = "Sources: No specific documents retrieved"
            
            # System prompt with retrieval constraints
            system_prompt = f"""
{self.master_prompt}

RETRIEVED CONTEXT:
{context}

SOURCE INFORMATION:
{source_info}

CRITICAL INSTRUCTIONS:
- Use ONLY the information provided in the RETRIEVED CONTEXT above
- Be professional, helpful, and detailed in your responses while staying factual
- When multiple sources are available, synthesize information comprehensively across all documents
- For comparison queries, clearly structure differences and similarities between programs
- Include natural source references when helpful (e.g., "According to the Web Development Remote bootcamp curriculum...")
- Provide comprehensive information that helps admissions representatives answer prospect questions accurately
- If information is not in the retrieved context, say "I don't have that specific information available in our curriculum materials"
- For unavailable information, guide users: "Please reach out to the Education team on Slack - they'll have those specific details"
- NEVER say "I'd be happy to connect you" (you cannot actually connect anyone)
- Make responses comprehensive and informative for sales team use
- Focus on providing accurate, detailed information that sales reps can confidently share with prospects
- Include relevant context that helps sales reps understand and explain the information
- When multiple documents are retrieved, ensure complete coverage of all relevant information
"""
            
            messages.append({"role": "system", "content": system_prompt})
            
            # Add conversation context if available
            if conversation_context:
                for msg in conversation_context[-6:]:  # Last 3 exchanges
                    role = "user" if msg["role"] == "user" else "assistant"
                    content = msg["content"]
                    if len(content) > 800:  # Truncate long messages
                        content = content[:800] + "..."
                    messages.append({"role": role, "content": content})
            
            # Add current query
            messages.append({"role": "user", "content": query})
            
            # Generate response
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.3  # Slightly more creative for warmth while staying factual
            )
            
            generated_response = response.choices[0].message.content
            logger.info(f"✅ Generated response ({len(generated_response)} chars)")
            
            # Append source filename(s) automatically if we have specific file information
            if sources and len(sources) > 0:
                # Only append if response doesn't already contain a source citation
                if not ("Source:" in generated_response):
                    if len(sources) == 1:
                        generated_response += f"\n\nSource: {sources[0]}"
                    else:
                        # Multiple sources - list them all
                        sources_list = ", ".join(sources)
                        generated_response += f"\n\nSources: {sources_list}"
            else:
                # No real documents found - this should trigger the "not found" scenario in the prompt
                logger.warning("⚠️ No specific documents retrieved - triggering not found scenario")
                # The master prompt should handle this case by suggesting to contact Education team
            
            return generated_response
            
        except Exception as e:
            logger.error(f"❌ Error generating response: {e}")
            # Fallback response
            return "I'm having trouble accessing our curriculum materials right now. Please reach out to the Education team on Slack for the specific course details you need."
    
    def validate_response(self, response, retrieved_docs):
        """Validate response against retrieved documents using GPT-4o"""
        try:
            logger.info("🔍 Validating response against retrieved documents...")
            
            context = "\n\n".join(retrieved_docs) if retrieved_docs else "No documents retrieved"
            
            validation_prompt = f"""
Analyze if this response contains ONLY information from the provided context.

RETRIEVED CONTEXT:
{context}

RESPONSE TO VALIDATE:
{response}

Return a JSON object with:
{{
    "contains_only_retrieved_info": true/false,
    "unsupported_claims": ["claim1", "claim2"],
    "confidence": 0.0-1.0,
    "explanation": "brief explanation"
}}
"""
            
            validation_response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a strict fact-checker. Analyze responses for fabrication. Always respond in valid JSON format."},
                    {"role": "user", "content": validation_prompt}
                ],
                temperature=0
            )
            
            validation_text = validation_response.choices[0].message.content.strip()
            
            # Parse JSON response
            if validation_text.startswith('```json'):
                validation_text = validation_text.replace('```json', '').replace('```', '').strip()
            
            # Ensure proper JSON boundaries
            if not validation_text.startswith('{'):
                start = validation_text.find('{')
                if start != -1:
                    validation_text = validation_text[start:]
            if not validation_text.endswith('}'):
                end = validation_text.rfind('}')
                if end != -1:
                    validation_text = validation_text[:end+1]
            
            validation_result = json.loads(validation_text)
            logger.info(f"✅ Validation completed: {validation_result.get('confidence', 0):.2f} confidence")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ Error validating response: {e}")
            return {
                "contains_only_retrieved_info": False,
                "unsupported_claims": ["Validation failed"],
                "confidence": 0.0,
                "explanation": f"Validation error: {str(e)}"
            }
    
    def process_query(self, query, conversation_context=None):
        """Main RAG pipeline: retrieve -> generate -> validate"""
        start_time = time.time()
        
        # Step 1: Retrieve documents
        retrieved_docs, sources = self.retrieve_documents(query)
        
        # Step 2: Generate response
        response = self.generate_response(query, retrieved_docs, conversation_context, sources)
        
        # Step 3: Validate response
        validation = self.validate_response(response, retrieved_docs)
        
        total_time = time.time() - start_time
        
        # Log results
        logger.info(f"⏱️ Custom RAG pipeline completed in {total_time:.2f}s")
        logger.info(f"📊 Validation confidence: {validation.get('confidence', 0):.2f}")
        
        return {
            "response": response,
            "retrieved_docs_count": len(retrieved_docs),
            "sources": sources,
            "validation": validation,
            "processing_time": total_time
        }

# Initialize Custom RAG Pipeline
custom_rag = CustomRAGPipeline(client, VECTOR_STORE_ID, MASTER_PROMPT)

# Message deduplication cache (same as original app)
class MessageDeduplicationCache:
    def __init__(self, max_size=1000, ttl_seconds=300):  # 5 minutes TTL
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache_file = os.path.join(tempfile.gettempdir(), 'message_cache_custom_rag.json')
    
    def load_cache(self):
        """Load cache from file with file locking"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                    try:
                        return json.load(f)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Error loading message cache: {str(e)}")
        return {}
    
    def save_cache(self, cache):
        """Save cache to file with file locking"""
        try:
            with open(self.cache_file, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
                try:
                    json.dump(cache, f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Error saving message cache: {str(e)}")
    
    def is_duplicate(self, message_id):
        """Check if message has been processed recently"""
        cache = self.load_cache()
        current_time = time.time()
        
        # Clean expired entries
        cache = {k: v for k, v in cache.items() if current_time - v < self.ttl_seconds}
        
        if message_id in cache:
            return True
        
        # Add new message
        cache[message_id] = current_time
        
        # Limit cache size
        if len(cache) > self.max_size:
            # Remove oldest entries
            sorted_items = sorted(cache.items(), key=lambda x: x[1])
            cache = dict(sorted_items[-self.max_size:])
        
        self.save_cache(cache)
        return False

# Initialize deduplication cache
dedup_cache = MessageDeduplicationCache()

# Conversation management (same as original app but with custom_rag suffix)
def load_conversation_mapping():
    """Load conversation mapping from file with file locking"""
    try:
        mapping_file = os.path.join(tempfile.gettempdir(), 'conversation_mapping_custom_rag.json')
        if os.path.exists(mapping_file):
            with open(mapping_file, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    return json.load(f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        logger.error(f"Error loading conversation mapping: {str(e)}")
    return {}

def save_conversation_mapping(mapping):
    """Save conversation mapping to file with file locking"""
    try:
        mapping_file = os.path.join(tempfile.gettempdir(), 'conversation_mapping_custom_rag.json')
        with open(mapping_file, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(mapping, f)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        logger.error(f"Error saving conversation mapping: {str(e)}")

def get_conversation_mapping():
    """Get current conversation mapping"""
    return load_conversation_mapping()

def update_conversation_mapping(conversation_id, conversation_data):
    """Update conversation mapping for a specific conversation"""
    mapping = load_conversation_mapping()
    mapping[conversation_id] = conversation_data
    save_conversation_mapping(mapping)
    return mapping

def add_message_to_conversation(conversation_id, role, content, timestamp=None):
    """Add a message to the conversation history"""
    if timestamp is None:
        timestamp = time.time()
    
    mapping = load_conversation_mapping()
    if conversation_id not in mapping:
        mapping[conversation_id] = {
            "messages": []
        }
    
    # Add the new message
    mapping[conversation_id]["messages"].append({
        "role": role,
        "content": content,
        "timestamp": timestamp
    })
    
    # Keep only the last 12 messages to prevent memory bloat (6 user + 6 assistant)
    if len(mapping[conversation_id]["messages"]) > 12:
        mapping[conversation_id]["messages"] = mapping[conversation_id]["messages"][-12:]
    
    save_conversation_mapping(mapping)
    return mapping

def get_conversation_context(conversation_id):
    """Get conversation context for RAG pipeline"""
    mapping = load_conversation_mapping()
    if conversation_id not in mapping or not mapping[conversation_id].get("messages"):
        return []
    
    # Return recent messages for context
    messages = mapping[conversation_id]["messages"]
    return messages[-8:] if len(messages) > 8 else messages

# Text processing utilities (same as original)
def clean_citations(text):
    """Clean up citations for Slack display"""
    # Remove markdown link syntax but keep the text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Clean up any remaining citation artifacts
    text = re.sub(r'\[([^\]]+)\]', r'\1', text)
    return text

def convert_markdown_to_slack(text):
    """Convert markdown formatting to Slack formatting"""
    # Convert bold **text** to *text*
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
    # Convert italic *text* to _text_
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'_\1_', text)
    # Convert headers # Header to *Header*
    text = re.sub(r'^#+\s*(.+)$', r'*\1*', text, flags=re.MULTILINE)
    # Convert bullet points - item to • item
    text = re.sub(r'^-\s+', '• ', text, flags=re.MULTILINE)
    return text

# Slack event handlers - only register if running as main
if __name__ == "__main__" and slack_app:
    @slack_app.event("app_mention")
    def handle_mention(event, say):
        """Handle @mentions in channels"""
        process_message(event, say)

    @slack_app.event("message")
    def handle_message(event, say):
        """Handle direct messages"""
        # Only process if it's a DM (no channel in event)
        if "channel" not in event or event.get("channel_type") == "im":
            process_message(event, say)

def process_message(event, say):
    """Process incoming messages using Custom RAG Pipeline"""
    user_message = event['text']
    
    # Get message ID for deduplication
    message_id = event.get('ts', str(time.time()))
    
    # Check for duplicates
    if dedup_cache.is_duplicate(message_id):
        logger.info(f"Duplicate message detected: {message_id}")
        return
    
    # Get conversation ID (thread or channel)
    conversation_id = event.get('thread_ts', event.get('channel'))
    
    logger.info(f"Processing message in conversation: {conversation_id}")
    logger.info(f"User message: {user_message}")
    
    # Get current conversation mapping
    current_conversation_mapping = get_conversation_mapping()
    if conversation_id not in current_conversation_mapping:
        conversation_data = {"messages": []}
        current_conversation_mapping = update_conversation_mapping(conversation_id, conversation_data)
    
    try:
        # Get conversation context
        conversation_context = get_conversation_context(conversation_id)
        
        # Process query through Custom RAG Pipeline
        logger.info("🚀 Processing with Custom RAG Pipeline...")
        rag_result = custom_rag.process_query(user_message, conversation_context)
        
        assistant_message = rag_result["response"]
        
        # Log RAG results
        logger.info(f"📊 RAG Results:")
        logger.info(f"   Retrieved docs: {rag_result['retrieved_docs_count']}")
        logger.info(f"   Sources: {rag_result['sources']}")
        logger.info(f"   Validation confidence: {rag_result['validation'].get('confidence', 0):.2f}")
        logger.info(f"   Processing time: {rag_result['processing_time']:.2f}s")
        
        # Add both user message and assistant response to conversation history
        add_message_to_conversation(conversation_id, "user", user_message)
        add_message_to_conversation(conversation_id, "assistant", assistant_message)
        
        logger.info(f"Assistant response: {assistant_message[:100]}...")
        logger.info(f"Added message exchange to conversation history for: {conversation_id}")
        
    except Exception as e:
        logger.error(f"Error processing message with Custom RAG: {str(e)}")
        say("I'm having trouble accessing our course information right now. Please reach out to the Education team on Slack for the details you need.")
        return
    
    # Clean up citations for Slack
    cleaned_message = clean_citations(assistant_message)
    
    # Convert markdown to Slack formatting
    slack_message = convert_markdown_to_slack(cleaned_message)
    
    # Reply in the same thread or channel
    try:
        say(slack_message, thread_ts=event.get('ts'))
        logger.info("Response sent successfully")
    except Exception as e:
        logger.error(f"Error sending response: {str(e)}")
        say("I'm having trouble sending my response right now. Please try again, or reach out to the Education team on Slack.")

# Flask app for Heroku - only initialize if running as main
if __name__ == "__main__":
    flask_app = Flask(__name__)

    @flask_app.route("/slack/events", methods=["POST"])
    def slack_events():
        """Handle Slack events"""
        return handler.handle(request)

    @flask_app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy", 
            "api": "custom_rag",
            "pipeline": "responses_retrieval + chat_completions_generation",
            "validation": "enabled"
        }

    flask_app.run(debug=True, port=int(os.environ.get("PORT", 3000)))
