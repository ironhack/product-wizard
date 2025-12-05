"""
Best Practice RAG Architecture v2 - LangGraph Implementation
Following research-backed best practices for sales enablement RAG systems:
- Namespace isolation via metadata filtering
- Hybrid retrieval (keyword-enhanced semantic search)
- Query enhancement for disambiguation
- Faithfulness verification dedicated node
- Iterative refinement with fallback strategies
"""

import os
import logging
import json
import re
import time
from typing import Dict, List, TypedDict, Annotated, Any, Optional
from operator import add
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request as flask_request

import openai
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# ---------------- Logging ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- Slack Event De-duplication ----------------
SEEN_EVENT_IDS: deque = deque(maxlen=512)
SEEN_ENVELOPE_IDS: deque = deque(maxlen=1024)

def _build_event_dedupe_key(event: Dict) -> Optional[str]:
    """Build a stable dedupe key for Slack events."""
    try:
        if not isinstance(event, dict):
            return None
        ev_id = event.get('event_id')
        if ev_id:
            return f"id:{ev_id}"
        client_msg_id = event.get('client_msg_id')
        if client_msg_id:
            ev_type = str(event.get('type') or '')
            return f"cmid:{ev_type}:{client_msg_id}"
        channel = str(event.get('channel', '') or '')
        ts = event.get('event_ts') or event.get('ts')
        ev_type = str(event.get('type') or '')
        thread_ts = event.get('thread_ts') or ''
        if channel and ts:
            return f"ch_ts:{ev_type}:{channel}:{ts}:{thread_ts}"
        return None
    except Exception:
        return None

def get_conversation_history(
    channel: str,
    thread_ts: str,
    limit: int = 10,
    latest_ts: Optional[str] = None
) -> List[BaseMessage]:
    """
    Retrieve conversation history from Slack thread.
    Returns a list of BaseMessage objects for use in RAG pipeline.
    
    If ``latest_ts`` is provided, the corresponding message is excluded so the
    active Slack event can be handled separately.
    
    Note: This requires the following Slack app scopes:
    - channels:history (for public channels)
    - groups:history (for private channels)  
    - mpim:history (for multi-party direct messages)
    - im:history (for direct messages)
    """
    try:
        from slack_sdk import WebClient
        from langchain_core.messages import HumanMessage, AIMessage
        
        client = WebClient(token=SLACK_BOT_TOKEN)
        
        # Get conversation history from the thread
        response = client.conversations_replies(
            channel=channel,
            ts=thread_ts,
            limit=limit
        )
        
        messages = []
        for msg in response.get("messages", []):
            msg_ts = msg.get("ts")
            
            # Skip the most recent Slack event to avoid duplicating the active query
            if latest_ts and msg_ts == latest_ts:
                continue
            
            text = msg.get("text", "")
            user_id = msg.get("user", "")
            bot_id = msg.get("bot_id", "")
            
            # Skip empty messages
            if not text.strip():
                continue
                
            # Remove bot mentions from user messages
            clean_text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
            if not clean_text:
                continue
            
            # Determine if it's a user message or bot message
            if bot_id or user_id == "USLACKBOT":
                # Bot message
                messages.append(AIMessage(content=clean_text))
            else:
                # User message
                messages.append(HumanMessage(content=clean_text))
        
        # Return messages in chronological order (oldest first)
        return messages
        
    except Exception as e:
        logger.warning(f"Failed to retrieve conversation history: {e}")
        
        # Check if it's a permissions issue
        if "missing_scope" in str(e):
            logger.warning("Missing Slack API scopes for conversation history. Required scopes: channels:history, groups:history, mpim:history, im:history")
        
        return []

def _already_processed(event: Dict) -> bool:
    """Check if event was already processed."""
    try:
        key = _build_event_dedupe_key(event)
        if not key:
            return False
        if key in SEEN_EVENT_IDS:
            logger.info(f"Duplicate event suppressed: {key}")
            return True
        SEEN_EVENT_IDS.append(key)
        return False
    except Exception:
        return False

# ---------------- Environment Setup ----------------
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
VECTOR_STORE_ID = os.environ.get("OPENAI_VECTOR_STORE_ID", "vs_xxx")

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ---------------- Config Loaders ----------------
def load_config_file(filename):
    """Load configuration file from assistant_config directory."""
    try:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(script_dir, 'assistant_config', filename)
        with open(file_path, 'r', encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.info(f"Config {filename} not found. Using defaults. Detail: {e}")
        return ""

# Load all configuration files
MASTER_PROMPT = load_config_file('MASTER_PROMPT.md') or "You are a helpful assistant for Ironhack course information."
GENERATION_INSTRUCTIONS = load_config_file('GENERATION_INSTRUCTIONS.md')
COMPARISON_INSTRUCTIONS = load_config_file('COMPARISON_INSTRUCTIONS.md')
VALIDATION_INSTRUCTIONS = load_config_file('VALIDATION_INSTRUCTIONS.md')
RETRIEVAL_INSTRUCTIONS = load_config_file('RETRIEVAL_INSTRUCTIONS.md')
DOCUMENT_FILTERING_INSTRUCTIONS = load_config_file('DOCUMENT_FILTERING_INSTRUCTIONS.md')
COVERAGE_CLASSIFICATION_PROMPT = load_config_file('COVERAGE_CLASSIFICATION.md')
COVERAGE_VERIFICATION_PROMPT = load_config_file('COVERAGE_VERIFICATION.md')
FALLBACK_CLASSIFIER_PROMPT = load_config_file('FALLBACK_CLASSIFIER.md')
FUN_FALLBACK_GENERATION_SYSTEM = load_config_file('FUN_FALLBACK_GENERATION_SYSTEM.md')
FUN_FALLBACK_GENERATION_USER = load_config_file('FUN_FALLBACK_GENERATION_USER.md')
FUN_FALLBACK_TEMPLATES = load_config_file('FUN_FALLBACK_TEMPLATES.md')
TEAM_ROUTING_RULES = load_config_file('TEAM_ROUTING_RULES.md')

# New configuration files
QUERY_ENHANCEMENT_PROMPT = load_config_file('QUERY_ENHANCEMENT.md')
PROGRAM_DETECTION_PROMPT = load_config_file('PROGRAM_DETECTION.md')
HYBRID_RETRIEVAL_PROMPT = load_config_file('HYBRID_RETRIEVAL.md')
RELEVANCE_ASSESSMENT_PROMPT = load_config_file('RELEVANCE_ASSESSMENT.md')
FAITHFULNESS_VERIFICATION_PROMPT = load_config_file('FAITHFULNESS_VERIFICATION.md')
REFINEMENT_STRATEGIES_PROMPT = load_config_file('REFINEMENT_STRATEGIES.md')
EXPANSION_INSTRUCTIONS = load_config_file('EXPANSION_INSTRUCTIONS.md')

# Load program synonyms
PROGRAM_SYNONYMS_TEXT = load_config_file('PROGRAM_SYNONYMS.json') or '{}'
try:
    PROGRAM_SYNONYMS = json.loads(PROGRAM_SYNONYMS_TEXT)
except Exception:
    PROGRAM_SYNONYMS = {}

# ---------------- RAG State Schema ----------------
class RAGState(TypedDict, total=False):
    # Input
    query: str
    conversation_history: List[BaseMessage]
    
    # Conversation context metadata
    is_follow_up: bool
    conversation_stage: str
    
    # Query Enhancement
    enhanced_query: str
    query_intent: str
    ambiguity_score: float
    
    # Program Detection & Namespace
    detected_programs: List[str]
    namespace_filter: Optional[Dict[str, Any]]
    
    # Retrieval
    retrieval_query: str
    retrieved_docs: List[Dict]
    retrieval_stats: Dict
    
    # Slack Integration (stored separately to avoid serialization issues)
    slack_channel: Optional[str] = None
    slack_thread_ts: Optional[str] = None
    
    # Relevance & Filtering
    relevance_scores: List[float]
    filtered_docs: List[Dict]
    rejection_reasons: List[str]
    
    # Coverage Detection
    is_coverage_question: bool
    coverage_verification: Dict
    
    # Generation
    generated_response: str
    source_citations: List[str]
    
    # Faithfulness Verification
    faithfulness_score: float
    faithfulness_violations: List[str]
    is_grounded: bool
    
    # Fallback & Iteration
    is_fallback: bool
    iteration_count: int
    refinement_strategy: str
    
    # Final
    final_response: str
    metadata: Dict
    
    # Error handling
    error: Optional[str]

# ---------------- Slack Update Helper ----------------

# Global variables to store the current say function and progress message (avoid serialization issues)
_current_say_function = None
_current_progress_message_ts = None
_progress_steps = [
    "🔍 Analyzing your question...",
    "🎯 Detecting program focus...", 
    "📚 Searching curriculum documents...",
    "⚖️ Assessing document relevance...",
    "🔍 Filtering best matches...",
    "❓ Checking if this is a coverage question...",
    "✅ Verifying topic presence...",
    "🤖 Generating response...",
    "🔍 Verifying answer accuracy...",
    "✅ Finalizing response..."
]
_current_step = 0

def set_slack_say_function(say_func):
    """Set the current Slack say function for updates."""
    global _current_say_function, _current_progress_message_ts, _current_step
    _current_say_function = say_func
    _current_progress_message_ts = None
    _current_step = 0

def clear_slack_say_function():
    """Clear the current Slack say function."""
    global _current_say_function, _current_progress_message_ts, _current_step
    _current_say_function = None
    _current_progress_message_ts = None
    _current_step = 0

def send_slack_update(state: RAGState, step_name: str):
    """Safely send/update Slack progress message with step numbering."""
    try:
        if _current_say_function and state.get("slack_channel"):
            global _current_step, _current_progress_message_ts
            
            # Find the step index
            step_index = next((i for i, step in enumerate(_progress_steps) if step_name in step), _current_step)
            _current_step = step_index
            
            # Create progress message with numbering
            total_steps = len(_progress_steps)
            progress_text = f"({_current_step + 1}/{total_steps}) {_progress_steps[_current_step]}"
            
            if _current_progress_message_ts:
                # Update existing message using Slack Web API
                try:
                    from slack_sdk import WebClient
                    client = WebClient(token=SLACK_BOT_TOKEN)
                    client.chat_update(
                        channel=state.get("slack_channel"),
                        ts=_current_progress_message_ts,
                        text=progress_text,
                        thread_ts=state.get("slack_thread_ts")
                    )
                except Exception as update_error:
                    logger.warning(f"Failed to update message, sending new one: {update_error}")
                    # Fallback to sending new message
                    response = _current_say_function(
                        text=progress_text,
                        thread_ts=state.get("slack_thread_ts"),
                        channel=state.get("slack_channel")
                    )
                    # Try to extract timestamp from response
                    if hasattr(response, 'get') and response.get('ts'):
                        _current_progress_message_ts = response.get('ts')
                    elif hasattr(response, 'ts'):
                        _current_progress_message_ts = response.ts
            else:
                # Send new message and store timestamp
                response = _current_say_function(
                    text=progress_text,
                    thread_ts=state.get("slack_thread_ts"),
                    channel=state.get("slack_channel")
                )
                # Try to extract timestamp from response
                if hasattr(response, 'get') and response.get('ts'):
                    _current_progress_message_ts = response.get('ts')
                elif hasattr(response, 'ts'):
                    _current_progress_message_ts = response.ts
                    
    except Exception as e:
        logger.warning(f"Failed to send Slack update: {e}")

# ---------------- Utility Functions ----------------

def format_conversation_history(messages: List[BaseMessage], limit: int = 5) -> str:
    """Format conversation history for prompts."""
    if not messages:
        return "No previous conversation."
    
    recent_messages = messages[-limit:]
    formatted = []
    for msg in recent_messages:
        if isinstance(msg, HumanMessage):
            formatted.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            formatted.append(f"Assistant: {msg.content}")
    
    return "\n".join(formatted) if formatted else "No previous conversation."

def call_openai_json(system_prompt: str, user_prompt: str, model: str = "gpt-4o") -> Dict:
    """Call OpenAI API and parse JSON response."""
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"OpenAI JSON call failed: {e}")
        return {}

def call_openai_text(system_prompt: str, user_prompt: str, model: str = "gpt-4o") -> str:
    """Call OpenAI API and get text response."""
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI text call failed: {e}")
        return ""

# ---------------- Node 1: Query Enhancement ----------------

def query_enhancement_node(state: RAGState) -> RAGState:
    """
    Disambiguate and enhance user query.
    - Clarify vague questions using conversation context
    - Classify query intent
    - Score ambiguity level
    """
    logger.info("=== Query Enhancement Node ===")
    send_slack_update(state, "Analyzing your question")
    
    query = state.get("query", "")
    conversation_history = state.get("conversation_history", [])
    conversation_stage = state.get("conversation_stage", "initial")
    
    if conversation_stage == "follow_up":
        stage_description = "follow-up message within an existing Slack thread"
    else:
        stage_description = "new question kicking off a Slack thread"
    
    # Format conversation context
    conv_context = format_conversation_history(conversation_history, limit=5)
    
    user_prompt = f"""
Conversation Stage: {stage_description}

Original Query: "{query}"

Conversation Context:
{conv_context}

Analyze and enhance this query following the guidelines.
"""
    
    result = call_openai_json(QUERY_ENHANCEMENT_PROMPT, user_prompt)
    
    enhanced_query = result.get("enhanced_query", query)
    query_intent = result.get("query_intent", "general_info")
    ambiguity_score = result.get("ambiguity_score", 0.5)
    
    logger.info(f"Enhanced: '{enhanced_query}' | Intent: {query_intent} | Ambiguity: {ambiguity_score}")
    
    return {
        **state,
        "enhanced_query": enhanced_query,
        "query_intent": query_intent,
        "ambiguity_score": ambiguity_score
    }

# ---------------- Node 2: Program Detection ----------------

def program_detection_node(state: RAGState) -> RAGState:
    """
    Detect which programs the query is about.
    - Extract program names
    - Map synonyms
    - Build namespace metadata filter
    """
    logger.info("=== Program Detection Node ===")
    send_slack_update(state, "Detecting program focus")
    
    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    conversation_history = state.get("conversation_history", [])
    query_intent = state.get("query_intent", "general_info")
    
    conv_context = format_conversation_history(conversation_history, limit=3)
    
    user_prompt = f"""
Query: "{enhanced_query}"
Query Intent: {query_intent}

Conversation Context:
{conv_context}

Program Synonyms Available:
{json.dumps(PROGRAM_SYNONYMS, indent=2)}

Detect which programs this query is about and build appropriate namespace filter.
"""
    
    result = call_openai_json(PROGRAM_DETECTION_PROMPT, user_prompt)
    
    detected_programs = result.get("detected_programs", [])
    namespace_filter = result.get("namespace_filter")
    confidence = result.get("confidence", 0.5)
    
    logger.info(f"Detected Programs: {detected_programs} | Confidence: {confidence}")
    logger.info(f"Namespace Filter: {namespace_filter}")
    
    return {
        **state,
        "detected_programs": detected_programs,
        "namespace_filter": namespace_filter
    }

# ---------------- Helper Functions ----------------

# ---------------- Node 3: Hybrid Retrieval ----------------

def hybrid_retrieval_node(state: RAGState) -> RAGState:
    """
    Retrieve documents using keyword-enhanced semantic search.
    - Apply namespace filtering
    - Enhance query with keywords
    - Perform vector search
    - Boost keyword matches
    """
    logger.info("=== Hybrid Retrieval Node ===")
    send_slack_update(state, "Searching curriculum documents")
    
    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    detected_programs = state.get("detected_programs", [])
    namespace_filter = state.get("namespace_filter")
    query_intent = state.get("query_intent", "general_info")
    iteration_count = state.get("iteration_count", 0)
    refinement_strategy = state.get("refinement_strategy", "")
    
    # Build keyword-enhanced query
    keyword_additions = []
    
    # Add program names
    for prog_id in detected_programs:
        prog_info = PROGRAM_SYNONYMS.get(prog_id, {})
        filenames = prog_info.get("filenames", [])
        if filenames:
            keyword_additions.append(filenames[0].replace("_", " ").replace(".txt", ""))
    
    # Add intent-specific keywords
    intent_keywords = {
        "coverage": "curriculum teaches includes covers contains",
        "certification": "certification credentials certificate industry",
        "duration": "hours weeks schedule duration time format",
        "technical_detail": "tools technologies frameworks libraries platforms",
        "requirements": "prerequisites requirements computer specs hardware software"
    }
    keyword_additions.append(intent_keywords.get(query_intent, ""))
    
    # Build enhanced retrieval query
    keywords = " ".join(keyword_additions)
    
    # For certification queries, explicitly include program name in query
    if query_intent == "certification" and detected_programs:
        valid_programs = [p for p in detected_programs if p in PROGRAM_SYNONYMS]
        if valid_programs:
            # Add program name variations to keywords
            for prog_id in valid_programs:
                prog_info = PROGRAM_SYNONYMS.get(prog_id, {})
                aliases = prog_info.get("aliases", [])
                if aliases:
                    keywords += " " + " ".join(aliases[:2])  # Add first 2 aliases
    
    retrieval_query = f"{enhanced_query} | KEYWORDS: {keywords}".strip()
    
    # Determine top_k based on query type and iteration
    top_k = 10
    if query_intent == "comparison":
        top_k = 15
    elif query_intent == "certification":
        top_k = 15  # Certification queries need both universal doc + program doc
    if "EXPAND_CHUNKS" in refinement_strategy:
        top_k = 15 if iteration_count == 1 else 20
    
    logger.info(f"Retrieval Query: {retrieval_query[:100]}...")
    logger.info(f"Top-K: {top_k} | Namespace Filter: {namespace_filter}")
    logger.info(f"Vector Store ID: {VECTOR_STORE_ID}")
    
    # Validate vector store ID
    if not VECTOR_STORE_ID or VECTOR_STORE_ID == "vs_xxx":
        logger.error(f"❌ Invalid vector store ID: {VECTOR_STORE_ID}")
        return {
            **state,
            "retrieval_query": retrieval_query,
            "retrieved_docs": [],
            "retrieval_stats": {"error": "Invalid vector store ID"}
        }
    
    # Perform vector search using OpenAI's Responses API (same as working system)
    try:
        # Use OpenAI's Responses API for vector search (non-deprecated approach)
        instructions = """Retrieve relevant curriculum information from the knowledge base. Focus on:
- Program details (duration, topics, technologies)
- Specific course content and learning objectives  
- Prerequisites and requirements
- Certifications and outcomes
- Exact quotes from curriculum documents when possible"""
        
        # Apply namespace filtering through instructions if needed
        if detected_programs:
            # Filter out non-program IDs like "certifications" 
            valid_program_hints = [p for p in detected_programs if p in PROGRAM_SYNONYMS]
            if valid_program_hints:
                program_names = []
                for prog_id in valid_program_hints:
                    prog_info = PROGRAM_SYNONYMS.get(prog_id, {})
                    # Get the main program name
                    filenames = prog_info.get("filenames", [])
                    if filenames:
                        program_names.append(filenames[0].replace("_", " ").replace(".txt", "").replace(".md", ""))
                    else:
                        program_names.append(prog_id.replace("_", " "))
                
                instructions = f"PROGRAM_HINT: {', '.join(program_names)}\n\n" + instructions
        
        # For certification queries, emphasize finding specific certification names
        if query_intent == "certification":
            valid_programs = [p for p in detected_programs if p in PROGRAM_SYNONYMS]
            if valid_programs:
                program_name = valid_programs[0].replace("_", " ")
                instructions += f"\n\nIMPORTANT: For certification queries, retrieve chunks from the Certifications document that specifically mention '{program_name}' or 'Web Development' certifications. Look for chunks containing specific certification names like 'Node.js Application Developer Certification' or 'MongoDB Developer Certification'."
        
        logger.info(f"🔍 Calling OpenAI Responses API with vector store search...")
        resp = openai_client.responses.create(
            model="gpt-4o-mini",
            input=[{"role": "user", "content": retrieval_query}],
            instructions=instructions,
            tools=[{
                "type": "file_search",
                "vector_store_ids": [VECTOR_STORE_ID],
                "max_num_results": top_k
            }],
            tool_choice={"type": "file_search"},
            include=["file_search_call.results"]
        )
        
        logger.info(f"✅ Received response from OpenAI Responses API")
        logger.debug(f"Response type: {type(resp)}")
        logger.debug(f"Response attributes: {dir(resp)}")
        
        # Extract hits from response (same logic as working system)
        hits = []
        response_output = getattr(resp, "output", [])
        logger.info(f"Response output structure: {type(response_output)}, length: {len(response_output) if response_output else 0}")
        
        for out in response_output:
            res = getattr(out, "results", None)
            if res:
                hits = res
                logger.info(f"Found hits in output.results: {len(hits)}")
                break
            fsc = getattr(out, "file_search_call", None)
            if fsc:
                if getattr(fsc, "results", None):
                    hits = fsc.results
                    logger.info(f"Found hits in file_search_call.results: {len(hits)}")
                    break
                if getattr(fsc, "search_results", None):
                    hits = fsc.search_results
                    logger.info(f"Found hits in file_search_call.search_results: {len(hits)}")
                    break
        
        # Also check response-level attributes
        if not hits:
            if hasattr(resp, "results"):
                hits = resp.results
                logger.info(f"Found hits in response.results: {len(hits)}")
            elif hasattr(resp, "file_search_call"):
                fsc = resp.file_search_call
                if hasattr(fsc, "results"):
                    hits = fsc.results
                    logger.info(f"Found hits in response.file_search_call.results: {len(hits)}")
        
        logger.info(f"Total hits extracted from vector store: {len(hits)}")
        
        # Process hits into retrieved_docs format
        retrieved_docs = []
        for idx, r in enumerate(hits):
            fname = getattr(r, "filename", None) or getattr(getattr(r, "document", None), "filename", None)
            fid = getattr(r, "file_id", None) or getattr(getattr(r, "document", None), "id", None)
            score = float(getattr(r, "score", 0.0) or 0.0)
            
            text = ""
            if hasattr(r, "text") and r.text:
                text = r.text
            elif hasattr(r, "content") and r.content:
                text = r.content
            elif hasattr(r, "document") and hasattr(r.document, "content"):
                text = r.document.content
            
            if text and len(text.strip()) > 50:  # Minimum content length
                retrieved_docs.append({
                    "content": text.strip(),
                    "source": fname or fid or "unknown",
                    "quote": text[:200] + "..." if len(text) > 200 else text,
                    "score": score
                })
                logger.debug(f"Processed hit {idx+1}: source={fname or fid}, score={score:.3f}, length={len(text)}")
            else:
                logger.warning(f"Skipped hit {idx+1}: insufficient content (length={len(text) if text else 0})")
        
        logger.info(f"Successfully processed {len(retrieved_docs)} documents from vector store")
        
        # Log warning if no hits found - system will handle empty results gracefully
        if not retrieved_docs:
            logger.warning(f"⚠️  Vector store returned no results for query: {retrieval_query[:100]}")
            logger.warning(f"⚠️  Vector Store ID: {VECTOR_STORE_ID}")
            logger.warning(f"⚠️  System will handle empty results gracefully (no fake documents generated)")
        
        retrieval_stats = {
            "total_retrieved": len(retrieved_docs),
            "top_k": top_k,
            "namespace_filter_applied": namespace_filter is not None,
            "programs_targeted": detected_programs,
            "vector_store_used": True,
            "fallback_used": False
        }
        
        if retrieved_docs:
            logger.info(f"✅ Retrieved {len(retrieved_docs)} documents from vector store")
            # Log sample sources
            sources = [doc.get("source", "unknown") for doc in retrieved_docs[:3]]
            logger.info(f"   Sample sources: {', '.join(sources)}")
        else:
            logger.warning(f"⚠️  No documents retrieved from vector store")
        
    except Exception as e:
        logger.error(f"❌ Vector store retrieval failed: {e}")
        logger.error(f"❌ Query: {retrieval_query[:100]}")
        logger.error(f"❌ Vector Store ID: {VECTOR_STORE_ID}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Return empty results - system will handle gracefully (no fake documents)
        retrieved_docs = []
        retrieval_stats = {
            "error": str(e),
            "fallback_used": False,
            "total_retrieved": 0
        }
        logger.warning(f"⚠️  Returning empty results - system will handle gracefully")
    
    return {
        **state,
        "retrieval_query": retrieval_query,
        "retrieved_docs": retrieved_docs,
        "retrieval_stats": retrieval_stats
    }

# ---------------- Node 4: Relevance Assessment ----------------

def relevance_assessment_node(state: RAGState) -> RAGState:
    """
    AI-powered relevance scoring for each retrieved document.
    - Score 0-1 for each chunk
    - Filter out low-relevance docs
    - Detect cross-contamination
    """
    logger.info("=== Relevance Assessment Node ===")
    send_slack_update(state, "Assessing document relevance")
    
    retrieved_docs = state.get("retrieved_docs", [])
    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    detected_programs = state.get("detected_programs", [])
    query_intent = state.get("query_intent", "general_info")
    
    if not retrieved_docs:
        logger.warning("No documents to assess")
        return {
            **state,
            "filtered_docs": [],
            "relevance_scores": [],
            "rejection_reasons": ["No documents retrieved"]
        }
    
    # Assess relevance for each chunk in parallel
    def assess_single_doc(idx_doc_pair):
        """Assess a single document's relevance."""
        idx, doc = idx_doc_pair
        doc_content = doc.get("content", "")[:500]  # Preview
        doc_source = doc.get("source", "unknown")
        
        user_prompt = f"""
Query: "{enhanced_query}"
Query Intent: {query_intent}
Detected Programs: {detected_programs}

Document Chunk {idx+1}:
Source: {doc_source}
Content Preview: {doc_content}

Assess this chunk's relevance to the query.
"""
        
        try:
            assessment = call_openai_json(RELEVANCE_ASSESSMENT_PROMPT, user_prompt)
            
            relevance_score = assessment.get("relevance_score", 0.5)
            should_include = assessment.get("should_include", False)
            red_flags = assessment.get("red_flags", [])
            
            return {
                "idx": idx,
                "doc": doc,
                "relevance_score": relevance_score,
                "should_include": should_include and relevance_score >= 0.3,
                "red_flags": red_flags,
                "reasoning": assessment.get("reasoning", "Low relevance"),
                "error": None
            }
        except Exception as e:
            logger.error(f"Assessment failed for doc {idx+1}: {e}")
            # On error, include the doc with medium score
            return {
                "idx": idx,
                "doc": doc,
                "relevance_score": 0.6,
                "should_include": True,
                "red_flags": [],
                "reasoning": f"Error: {str(e)}",
                "error": str(e)
            }
    
    # Parallelize assessments using ThreadPoolExecutor
    assessed_docs = []
    relevance_scores = []
    rejection_reasons = []
    
    docs_to_assess = list(enumerate(retrieved_docs[:15]))  # Limit assessment to top 15
    
    # Use ThreadPoolExecutor with max_workers (OpenAI API can handle concurrent requests)
    # Limit to 5 concurrent requests to avoid rate limits
    max_workers = min(5, len(docs_to_assess))
    
    if len(docs_to_assess) > 1:
        logger.info(f"Parallelizing relevance assessment: {len(docs_to_assess)} docs with {max_workers} workers")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all assessment tasks
        future_to_idx = {executor.submit(assess_single_doc, idx_doc): idx_doc[0] 
                        for idx_doc in docs_to_assess}
        
        # Collect results as they complete
        results = []
        for future in as_completed(future_to_idx):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                idx = future_to_idx[future]
                logger.error(f"Future failed for doc {idx+1}: {e}")
                # Include doc with medium score on future failure
                if idx < len(retrieved_docs):
                    results.append({
                        "idx": idx,
                        "doc": retrieved_docs[idx],
                        "relevance_score": 0.6,
                        "should_include": True,
                        "red_flags": [],
                        "reasoning": f"Future error: {str(e)}",
                        "error": str(e)
                    })
        
        # Sort results by original index to maintain order
        results.sort(key=lambda x: x["idx"])
        
        # Process results
        for result in results:
            idx = result["idx"]
            doc = result["doc"]
            relevance_score = result["relevance_score"]
            should_include = result["should_include"]
            red_flags = result["red_flags"]
            reasoning = result["reasoning"]
            
            if should_include:
                assessed_docs.append(doc)
                relevance_scores.append(relevance_score)
            else:
                rejection_reasons.append(f"Doc {idx+1}: {reasoning}")
                if red_flags:
                    logger.warning(f"Red flags for doc {idx+1}: {red_flags}")
    
    # If no docs passed assessment, include top 3 docs anyway as fallback
    if not assessed_docs and retrieved_docs:
        logger.warning("No docs passed relevance assessment, using fallback strategy")
        assessed_docs = retrieved_docs[:3]
        relevance_scores = [0.6] * len(assessed_docs)  # Give them medium scores
    
    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    logger.info(f"Assessed {len(assessed_docs)} docs | Avg Relevance: {avg_relevance:.2f}")
    
    return {
        **state,
        "filtered_docs": assessed_docs,
        "relevance_scores": relevance_scores,
        "rejection_reasons": rejection_reasons
    }

# ---------------- Node 5: Document Filtering ----------------

def document_filtering_node(state: RAGState) -> RAGState:
    """
    Enhanced document filtering with cross-contamination detection.
    - First pass: Filter by document source (keep only chunks from relevant program documents)
    - Second pass: AI-based filtering for fine-grained relevance
    """
    logger.info("=== Document Filtering Node ===")
    send_slack_update(state, "Filtering best matches")
    
    filtered_docs = state.get("filtered_docs", [])
    detected_programs = state.get("detected_programs", [])
    query_intent = state.get("query_intent", "general_info")
    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    
    if not filtered_docs:
        return state
    
    # STEP 1: Source-based filtering - keep only chunks from relevant program documents
    # Universal documents that apply to all programs (always include these)
    UNIVERSAL_DOCUMENTS = [
        "certifications_2025_07",
        "course_design_overview_2025_07",
        "computer_specs_min_requirements",
        "ironhack_portfolio_overview_2025_07"
    ]
    
    # Filter detected_programs to only include actual programs (not document names like "certifications")
    valid_programs = [prog_id for prog_id in detected_programs if prog_id in PROGRAM_SYNONYMS]
    
    # Always keep universal documents regardless of detected programs
    source_filtered_docs = []
    universal_docs = []
    program_docs = []
    
    for doc in filtered_docs:
        source = doc.get("source", "").lower()
        
        # Check if this is a universal document
        is_universal = False
        for universal_doc in UNIVERSAL_DOCUMENTS:
            if universal_doc in source:
                is_universal = True
                universal_docs.append(doc)
                source_filtered_docs.append(doc)
                logger.debug(f"Keeping universal document: {doc.get('source', 'unknown')}")
                break
        
        if is_universal:
            continue
        
        # For program-specific documents, only keep if they match detected programs
        if valid_programs:
            # Build list of expected document filename patterns for detected programs
            expected_sources = set()
            for prog_id in valid_programs:
                prog_info = PROGRAM_SYNONYMS.get(prog_id, {})
                filenames = prog_info.get("filenames", [])
                for filename in filenames:
                    # Add both .txt and .md variants, and handle case variations
                    expected_sources.add(filename.lower())
                    expected_sources.add(filename.replace(".txt", "").lower())
                    expected_sources.add(filename.replace(".md", "").lower())
            
            # Check if source matches any expected program document
            matches = False
            for expected in expected_sources:
                if expected in source:
                    matches = True
                    break
            
            # Also check if source contains program name keywords
            if not matches:
                for prog_id in valid_programs:
                    prog_info = PROGRAM_SYNONYMS.get(prog_id, {})
                    # Check program name variations
                    if prog_id.replace("_", " ") in source or prog_id.replace("_", "_") in source:
                        matches = True
                        break
            
            if matches:
                program_docs.append(doc)
                source_filtered_docs.append(doc)
            else:
                logger.debug(f"Filtered out chunk from wrong document: {doc.get('source', 'unknown')}")
        else:
            # No valid programs detected, but keep universal docs (already added above)
            # Also keep any docs if no program filtering needed
            if not detected_programs:
                source_filtered_docs.append(doc)
    
    # Log filtering results (outside the loop)
    logger.info(f"Source-based filtering: {len(filtered_docs)} → {len(source_filtered_docs)} docs "
               f"({len(program_docs)} program-specific, {len(universal_docs)} universal)")
    
    # If source filtering removed too many, be more permissive
    if len(source_filtered_docs) < 2 and len(filtered_docs) >= 2:
        logger.warning(f"Source filtering too strict ({len(source_filtered_docs)} docs), keeping top 3 by relevance")
        source_filtered_docs = filtered_docs[:3]
    elif len(source_filtered_docs) == 0:
        logger.warning(f"Source filtering removed all docs, keeping top 3 as fallback")
        source_filtered_docs = filtered_docs[:3]
    
    filtered_docs = source_filtered_docs
    
    # STEP 2: AI-based fine-grained filtering (only if we have enough docs after source filtering)
    if len(filtered_docs) > 3:
        # Prepare document context for AI filtering
        docs_summary = []
        for idx, doc in enumerate(filtered_docs[:15]):
            docs_summary.append({
                "chunk_id": idx + 1,
                "source": doc.get("source", "unknown"),
                "content_preview": doc.get("content", "")[:200]
            })
        
        user_prompt = f"""
Query: "{enhanced_query}"
Query Intent: {query_intent}
Detected Programs: {detected_programs}

Retrieved Document Chunks (already filtered by source):
{json.dumps(docs_summary, indent=2)}

Apply fine-grained relevance filtering. These chunks are already from the correct program documents.
Return the IDs of chunks that should be KEPT (others will be rejected).
Return as JSON: {{"kept_chunk_ids": [1, 2, 5, ...], "reasoning": "explanation"}}
"""
        
        try:
            result = call_openai_json(DOCUMENT_FILTERING_INSTRUCTIONS, user_prompt)
            kept_ids = result.get("kept_chunk_ids", [])
            
            # Filter docs based on kept IDs - but be more permissive if too few docs
            final_docs = [doc for idx, doc in enumerate(filtered_docs) if (idx + 1) in kept_ids]
            
            # If AI filtering removed too many docs, be more permissive
            if len(final_docs) < 2 and len(filtered_docs) >= 2:
                # Keep top 3 docs even if filtering was strict
                final_docs = filtered_docs[:3]
                logger.info(f"AI filtering too strict, keeping top 3 docs instead")
            
            filtered_docs = final_docs
            logger.info(f"AI filtering: {len(filtered_docs)} docs after fine-grained filtering")
        
        except Exception as e:
            logger.error(f"AI document filtering failed: {e}, keeping source-filtered docs")
            # On error, keep source-filtered docs
    
    logger.info(f"Final filtering result: {len(state.get('filtered_docs', []))} → {len(filtered_docs)} docs")
    
    return {
        **state,
        "filtered_docs": filtered_docs
    }

# ---------------- Node 6: Coverage Classification ----------------

def coverage_classification_node(state: RAGState) -> RAGState:
    """
    Detect if query is asking about curriculum coverage.
    """
    logger.info("=== Coverage Classification Node ===")
    send_slack_update(state, "Checking if this is a coverage question")
    
    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    query_intent = state.get("query_intent", "general_info")
    
    # Quick heuristic check first
    coverage_keywords = ["does", "is", "include", "cover", "teach", "contain", "have"]
    has_coverage_keyword = any(kw in enhanced_query.lower() for kw in coverage_keywords)
    
    if not has_coverage_keyword and query_intent != "coverage":
        return {
            **state,
            "is_coverage_question": False
        }
    
    # AI classification
    user_prompt = f"""
Query: "{enhanced_query}"
Query Intent: {query_intent}

Is this a curriculum coverage question (asking if a program includes/teaches specific topics)?
Return JSON: {{"is_coverage_question": true/false, "reasoning": "explanation"}}
"""
    
    result = call_openai_json(COVERAGE_CLASSIFICATION_PROMPT, user_prompt)
    is_coverage = result.get("is_coverage_question", False)
    
    logger.info(f"Coverage Question: {is_coverage}")
    
    return {
        **state,
        "is_coverage_question": is_coverage
    }

# ---------------- Node 7: Coverage Verification ----------------

def coverage_verification_node(state: RAGState) -> RAGState:
    """
    Verify if topic is explicitly present in retrieved documents.
    """
    logger.info("=== Coverage Verification Node ===")
    send_slack_update(state, "Verifying topic presence")
    
    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    filtered_docs = state.get("filtered_docs", [])
    detected_programs = state.get("detected_programs", [])
    
    # Compile document content
    docs_content = "\n\n---\n\n".join([
        f"Source: {doc.get('source', 'unknown')}\n{doc.get('content', '')[:800]}"
        for doc in filtered_docs[:10]
    ])
    
    user_prompt = f"""
Query: "{enhanced_query}"
Programs: {detected_programs}

Retrieved Documents:
{docs_content}

Verify if the queried topic is explicitly mentioned in these documents.
Return JSON: {{"is_present": true/false, "topic": "extracted topic", "evidence": "quote from docs if present"}}
"""
    
    result = call_openai_json(COVERAGE_VERIFICATION_PROMPT, user_prompt)
    
    coverage_verification = {
        "is_present": result.get("is_present", False),
        "topic": result.get("topic", ""),
        "evidence": result.get("evidence", "")
    }
    
    logger.info(f"Coverage Verification: {coverage_verification}")
    
    return {
        **state,
        "coverage_verification": coverage_verification
    }

# ---------------- Node 8: Generate Response ----------------

def generate_response_node(state: RAGState) -> RAGState:
    """
    Generate answer from filtered, relevant documents.
    - Enforce citation requirements
    - Constrained generation
    """
    logger.info("=== Generate Response Node ===")
    send_slack_update(state, "Generating response")
    
    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    filtered_docs = state.get("filtered_docs", [])
    conversation_history = state.get("conversation_history", [])
    detected_programs = state.get("detected_programs", [])
    query_intent = state.get("query_intent", "general_info")
    
    if not filtered_docs:
        logger.warning("No documents available for generation")
        return {
            **state,
            "generated_response": "I don't have sufficient information in the curriculum documents to answer this question accurately.",
            "source_citations": [],
            "is_fallback": True
        }
    
    # Compile context from filtered documents
    context_chunks = []
    for idx, doc in enumerate(filtered_docs[:10]):
        source = doc.get("source", "unknown")
        content = doc.get("content", "")
        context_chunks.append(f"[Chunk {idx+1} - Source: {source}]\n{content}")
    
    context = "\n\n---\n\n".join(context_chunks)
    conv_context = format_conversation_history(conversation_history, limit=3)
    
    # Use comparison instructions for comparison queries
    if query_intent == "comparison" and COMPARISON_INSTRUCTIONS:
        additional_instructions = COMPARISON_INSTRUCTIONS
    else:
        additional_instructions = ""
    
    system_prompt = f"""{MASTER_PROMPT}

{GENERATION_INSTRUCTIONS}

{additional_instructions}

CRITICAL: Generate answers ONLY from the provided document context. Never use external knowledge.
"""
    
    user_prompt = f"""
User Query: "{enhanced_query}"
Query Intent: {query_intent}
Programs: {detected_programs}

Conversation Context:
{conv_context}

Retrieved Document Context:
{context}

Generate a comprehensive, accurate answer with proper source citations.
"""
    
    generated_response = call_openai_text(system_prompt, user_prompt)
    
    # Extract citations from response
    citations = []
    for doc in filtered_docs:
        source = doc.get("source", "")
        if source and source in generated_response:
            citations.append(source)
    
    logger.info(f"Generated response: {len(generated_response)} chars | Citations: {len(citations)}")
    
    return {
        **state,
        "generated_response": generated_response,
        "source_citations": citations
    }

# ---------------- Node 9: Faithfulness Verification ----------------

def faithfulness_verification_node(state: RAGState) -> RAGState:
    """
    Verify that generated answer is grounded in retrieved documents.
    - Detect hallucinations
    - Score faithfulness
    - Flag violations
    """
    logger.info("=== Faithfulness Verification Node ===")
    send_slack_update(state, "Verifying answer accuracy")
    
    generated_response = state.get("generated_response", "")
    filtered_docs = state.get("filtered_docs", [])
    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    query_intent = state.get("query_intent", "general_info")
    
    if not generated_response or not filtered_docs:
        return {
            **state,
            "faithfulness_score": 0.0,
            "is_grounded": False,
            "faithfulness_violations": ["No response or documents to verify"]
        }
    
    # Compile retrieved documents for verification
    # Include full content for certification queries to ensure proper verification
    content_limit = 1000 if query_intent == "certification" else 600
    docs_text = "\n\n".join([
        f"[{doc.get('source', 'unknown')}]\n{doc.get('content', '')[:content_limit]}"
        for doc in filtered_docs[:8]
    ])
    
    logger.debug(f"Faithfulness verification: checking {len(filtered_docs)} docs, content limit {content_limit} chars")
    
    user_prompt = f"""
User Query: "{enhanced_query}"

Retrieved Documents:
{docs_text}

Generated Answer:
{generated_response}

Verify that every claim in the generated answer is grounded in the retrieved documents.
"""
    
    result = call_openai_json(FAITHFULNESS_VERIFICATION_PROMPT, user_prompt)
    
    faithfulness_score = result.get("faithfulness_score", 0.5)
    is_grounded = result.get("is_grounded", False)
    violations = result.get("violations", [])
    recommendation = result.get("recommendation", "approve")
    
    logger.info(f"Faithfulness: {faithfulness_score:.2f} | Grounded: {is_grounded} | Violations: {len(violations)}")
    
    return {
        **state,
        "faithfulness_score": faithfulness_score,
        "is_grounded": is_grounded,
        "faithfulness_violations": [v.get("claim", "") for v in violations] if violations else []
    }

# ---------------- Node 10: Fallback Detection ----------------

def fallback_detection_node(state: RAGState) -> RAGState:
    """
    Detect if response is insufficient/non-substantive.
    """
    logger.info("=== Fallback Detection Node ===")
    
    generated_response = state.get("generated_response", "")
    
    if not generated_response or len(generated_response) < 50:
        return {
            **state,
            "is_fallback": True
        }
    
    user_prompt = f"""
Generated Response:
{generated_response}

Is this a substantive answer or an insufficient/fallback response?
Return JSON: {{"is_fallback": true/false, "reasoning": "explanation"}}
"""
    
    result = call_openai_json(FALLBACK_CLASSIFIER_PROMPT, user_prompt)
    is_fallback = result.get("is_fallback", False)
    
    logger.info(f"Fallback Detected: {is_fallback}")
    
    return {
        **state,
        "is_fallback": is_fallback
    }

# ---------------- Node 11: Iterative Refinement ----------------

def iterative_refinement_node(state: RAGState) -> RAGState:
    """
    Determine and apply refinement strategy.
    - Expand chunks
    - Relax filters
    - Enhance query
    - Generate fun fallback
    """
    logger.info("=== Iterative Refinement Node ===")
    
    iteration_count = state.get("iteration_count", 0)
    faithfulness_score = state.get("faithfulness_score", 1.0)
    is_fallback = state.get("is_fallback", False)
    filtered_docs = state.get("filtered_docs", [])
    relevance_scores = state.get("relevance_scores", [])
    
    # Prevent infinite loops - check query intent for max iterations
    query_intent = state.get("query_intent", "general_info")
    max_allowed_iterations = 3 if query_intent == "comparison" else 2
    
    if iteration_count >= max_allowed_iterations:
        logger.warning(f"Max iterations reached ({iteration_count}), forcing fun fallback")
        return {
            **state,
            "refinement_strategy": "FUN_FALLBACK",
            "iteration_count": iteration_count + 1
        }
    
    # Analyze failure mode
    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    num_docs = len(filtered_docs)
    
    failure_analysis = {
        "iteration_count": iteration_count,
        "faithfulness_score": faithfulness_score,
        "is_fallback": is_fallback,
        "num_docs_retrieved": num_docs,
        "avg_relevance": avg_relevance
    }
    
    user_prompt = f"""
Failure Analysis:
{json.dumps(failure_analysis, indent=2)}

Determine the best refinement strategy to improve results.
"""
    
    result = call_openai_json(REFINEMENT_STRATEGIES_PROMPT, user_prompt)
    
    selected_strategy = result.get("selected_strategy", "FUN_FALLBACK")
    refinement_params = result.get("parameters", {})
    
    logger.info(f"Refinement Strategy: {selected_strategy} | Iteration: {iteration_count + 1}")
    
    # Update state with refinement decision
    return {
        **state,
        "iteration_count": iteration_count + 1,
        "refinement_strategy": selected_strategy,
        "metadata": {
            **state.get("metadata", {}),
            "refinement_applied": selected_strategy,
            "refinement_params": refinement_params
        }
    }

# ---------------- Node 12: Generate Fun Fallback ----------------

def generate_fun_fallback_node(state: RAGState) -> RAGState:
    """
    Generate contextual fun fallback message with team routing.
    """
    logger.info("=== Generate Fun Fallback Node ===")
    
    enhanced_query = state.get("enhanced_query", state.get("query", ""))
    detected_programs = state.get("detected_programs", [])
    
    system_prompt = f"""{FUN_FALLBACK_GENERATION_SYSTEM}

{FUN_FALLBACK_TEMPLATES}

{TEAM_ROUTING_RULES}
"""
    
    user_prompt = f"""{FUN_FALLBACK_GENERATION_USER}

User Query: "{enhanced_query}"
Programs: {detected_programs}

Generate an appropriate fun fallback response.
"""
    
    fallback_response = call_openai_text(system_prompt, user_prompt)
    
    logger.info("Generated fun fallback response")
    
    return {
        **state,
        "final_response": fallback_response
    }

# ---------------- Node 13: Finalize Response ----------------

def finalize_response_node(state: RAGState) -> RAGState:
    """
    Format final response with citations and metadata.
    """
    logger.info("=== Finalize Response Node ===")
    send_slack_update(state, "Finalizing response")
    
    generated_response = state.get("generated_response", "")
    source_citations = state.get("source_citations", [])
    faithfulness_score = state.get("faithfulness_score", 0.0)
    detected_programs = state.get("detected_programs", [])
    
    # Format citations if not already in response
    if source_citations and "[Source:" not in generated_response:
        citation_text = "\n\nSources: " + ", ".join(set(source_citations))
        final_response = generated_response + citation_text
    else:
        final_response = generated_response
    
    metadata = {
        **state.get("metadata", {}),
        "detected_programs": detected_programs,
        "faithfulness_score": faithfulness_score,
        "num_sources": len(source_citations),
        "iteration_count": state.get("iteration_count", 0)
    }
    
    logger.info(f"Finalized response: {len(final_response)} chars")
    
    return {
        **state,
        "final_response": final_response,
        "metadata": metadata
    }

# ---------------- Routing Functions ----------------

def route_after_query_enhancement(state: RAGState) -> str:
    """Route after query enhancement based on ambiguity."""
    ambiguity_score = state.get("ambiguity_score", 0.5)
    
    # If extremely ambiguous, might need clarification
    # For now, always proceed to program detection
    return "program_detection"

def route_after_coverage_classification(state: RAGState) -> str:
    """Route to coverage verification or generation."""
    # Skip coverage verification for comparison queries - they need full generation
    query_intent = state.get("query_intent", "general_info")
    if query_intent == "comparison":
        return "generate_response"
    if state.get("is_coverage_question", False):
        return "coverage_verification"
    return "generate_response"

def route_after_coverage_verification(state: RAGState) -> str:
    """Route to appropriate response generation based on coverage."""
    coverage_verification = state.get("coverage_verification", {})
    is_present = coverage_verification.get("is_present", False)
    
    if is_present:
        return "generate_response"
    else:
        # Generate negative coverage response
        return "generate_negative_coverage"

def route_after_faithfulness_verification(state: RAGState) -> str:
    """Route based on faithfulness and iteration count."""
    is_grounded = state.get("is_grounded", False)
    faithfulness_score = state.get("faithfulness_score", 0.0)
    iteration_count = state.get("iteration_count", 0)
    query_intent = state.get("query_intent", "general_info")
    
    # Adjust threshold based on query type
    # Comparison queries synthesize multiple documents, so lower threshold
    if query_intent == "comparison":
        threshold = 0.5
        max_iterations = 2
    elif query_intent in ["duration", "technical_detail", "certification"]:
        threshold = 0.6  # Lower for queries requiring synthesis of details
        max_iterations = 1
    else:
        threshold = 0.7
        max_iterations = 1
    
    # Production gate: require faithfulness >= threshold to finalize
    # For comparison queries, also accept if score >= threshold even if not fully grounded
    if query_intent == "comparison" and faithfulness_score >= threshold:
        return "finalize_response"
    elif is_grounded and faithfulness_score >= threshold:
        return "finalize_response"
    # Allow refinement attempts based on query type
    elif iteration_count < max_iterations:
        return "iterative_refinement"
    else:
        # Max iterations reached - force fun fallback
        logger.warning(f"Max iterations ({max_iterations}) reached for {query_intent} query, routing to fun fallback")
        return "generate_fun_fallback"

def route_after_refinement(state: RAGState) -> str:
    """Route based on selected refinement strategy."""
    strategy = state.get("refinement_strategy", "FUN_FALLBACK")
    
    if strategy == "EXPAND_CHUNKS":
        return "hybrid_retrieval"
    elif strategy == "RELAX_NAMESPACE_FILTER":
        return "hybrid_retrieval"
    elif strategy == "ENHANCE_QUERY_KEYWORDS":
        return "query_enhancement"
    elif strategy == "SWITCH_TO_COVERAGE_PATH":
        return "coverage_verification"
    else:  # FUN_FALLBACK
        return "generate_fun_fallback"

# ---------------- Negative Coverage Response ----------------

def generate_negative_coverage_node(state: RAGState) -> RAGState:
    """Generate clear 'No' response for negative coverage."""
    logger.info("=== Generate Negative Coverage Response ===")
    
    coverage_verification = state.get("coverage_verification", {})
    topic = coverage_verification.get("topic", "the requested topic")
    detected_programs = state.get("detected_programs", [])
    program_name = detected_programs[0] if detected_programs else "the program"
    filtered_docs = state.get("filtered_docs", [])
    retrieved_docs = state.get("retrieved_docs", [])
    
    # For negative coverage, we MUST cite the correct program's document
    # Even if it wasn't retrieved (because the topic isn't in it)
    citations = []
    primary_program = detected_programs[0] if detected_programs else None
    
    # First, try to find the correct program document in retrieved_docs
    if primary_program and primary_program in PROGRAM_SYNONYMS:
        prog_info = PROGRAM_SYNONYMS[primary_program]
        filenames = prog_info.get("filenames", [])
        
        # Check all retrieved documents (not just filtered) for correct program document
        for doc in retrieved_docs:
            source = doc.get("source", "")
            for filename in filenames:
                # Match filename (with or without extension, case-insensitive)
                base_filename = filename.replace(".txt", "").replace(".md", "")
                if base_filename.lower() in source.lower() or filename.lower() in source.lower():
                    if source not in citations:
                        citations.append(source)
                        logger.debug(f"Found correct program citation in retrieved docs: {source}")
                        break
    
    # If not found in retrieved docs, use expected filename from PROGRAM_SYNONYMS
    # This ensures we cite the correct document even if it wasn't retrieved
    if not citations and primary_program and primary_program in PROGRAM_SYNONYMS:
        prog_info = PROGRAM_SYNONYMS[primary_program]
        filenames = prog_info.get("filenames", [])
        if filenames:
            # Use the expected filename as citation (prefer .md format for consistency)
            expected_filename = filenames[0].replace(".txt", ".md").replace(".md.md", ".md")
            citations.append(expected_filename)
            logger.info(f"Using expected program document citation: {expected_filename}")
    
    # Build response with correct citation
    # For negative coverage, we just need to state clearly that the topic is not included
    # and cite the correct program document - no need for extra context
    if citations:
        primary_source = citations[0]
        response = f"No, {program_name} does not include {topic}. Based on the curriculum documents, this topic is not part of the program. [Source: {primary_source}]"
    else:
        response = f"No, {program_name} does not include {topic}. Based on the curriculum documents, this topic is not part of the program."
    
    logger.info(f"Generated negative coverage response: {len(response)} chars | Citations: {len(citations)}")
    
    return {
        **state,
        "generated_response": response,
        "final_response": response,
        "source_citations": citations
    }

# ---------------- Build Workflow ----------------

def build_workflow() -> StateGraph:
    """Build the LangGraph workflow with all nodes and routing."""
    logger.info("Building RAG workflow...")
    
    workflow = StateGraph(RAGState)
    
    # Add all nodes
    workflow.add_node("query_enhancement", query_enhancement_node)
    workflow.add_node("program_detection", program_detection_node)
    workflow.add_node("hybrid_retrieval", hybrid_retrieval_node)
    workflow.add_node("relevance_assessment", relevance_assessment_node)
    workflow.add_node("document_filtering", document_filtering_node)
    workflow.add_node("coverage_classification", coverage_classification_node)
    workflow.add_node("coverage_verification", coverage_verification_node)
    workflow.add_node("generate_response", generate_response_node)
    workflow.add_node("faithfulness_verification", faithfulness_verification_node)
    workflow.add_node("fallback_detection", fallback_detection_node)
    workflow.add_node("iterative_refinement", iterative_refinement_node)
    workflow.add_node("generate_fun_fallback", generate_fun_fallback_node)
    workflow.add_node("generate_negative_coverage", generate_negative_coverage_node)
    workflow.add_node("finalize_response", finalize_response_node)
    
    # Set entry point
    workflow.set_entry_point("query_enhancement")
    
    # Add edges
    workflow.add_edge("query_enhancement", "program_detection")
    workflow.add_edge("program_detection", "hybrid_retrieval")
    workflow.add_edge("hybrid_retrieval", "relevance_assessment")
    workflow.add_edge("relevance_assessment", "document_filtering")
    workflow.add_edge("document_filtering", "coverage_classification")
    
    # Conditional routing after coverage classification
    workflow.add_conditional_edges(
        "coverage_classification",
        route_after_coverage_classification,
        {
            "coverage_verification": "coverage_verification",
            "generate_response": "generate_response"
        }
    )
    
    # Routing after coverage verification
    workflow.add_conditional_edges(
        "coverage_verification",
        route_after_coverage_verification,
        {
            "generate_response": "generate_response",
            "generate_negative_coverage": "generate_negative_coverage"
        }
    )
    
    # Negative coverage goes straight to END
    workflow.add_edge("generate_negative_coverage", END)
    
    # Generation goes to faithfulness verification
    workflow.add_edge("generate_response", "faithfulness_verification")
    
    # Routing after faithfulness verification
    workflow.add_conditional_edges(
        "faithfulness_verification",
        route_after_faithfulness_verification,
        {
            "finalize_response": "finalize_response",
            "iterative_refinement": "iterative_refinement",
            "generate_fun_fallback": "generate_fun_fallback"
        }
    )
    
    # Routing after refinement
    workflow.add_conditional_edges(
        "iterative_refinement",
        route_after_refinement,
        {
            "hybrid_retrieval": "hybrid_retrieval",
            "query_enhancement": "query_enhancement",
            "coverage_verification": "coverage_verification",
            "generate_fun_fallback": "generate_fun_fallback"
        }
    )
    
    # Fun fallback and finalize both go to END
    workflow.add_edge("generate_fun_fallback", END)
    workflow.add_edge("finalize_response", END)
    
    # Compile with memory
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

# ---------------- Initialize Workflow ----------------
rag_workflow = build_workflow()
logger.info("RAG workflow initialized successfully")

# ---------------- Slack Integration ----------------

def handle_mention(event, say):
    """Handle @mentions in Slack."""
    if _already_processed(event):
        return
    
    text = event.get("text", "")
    user_id = event.get("user", "unknown")
    channel = event.get("channel", "")
    event_ts = event.get("ts") or event.get("event_ts", "")
    thread_ts = event.get("thread_ts", event_ts)
    channel_type = event.get("channel_type")
    
    # Remove bot mention from text
    query = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
    
    logger.info(f"Processing mention from {user_id} in {channel} ({channel_type}): {query}")

    try:
        # Set the current say function for progress updates
        set_slack_say_function(say)
        
        # Retrieve conversation history from the thread
        conversation_history = get_conversation_history(
            channel,
            thread_ts,
            limit=10,
            latest_ts=event_ts
        )
        prior_message_count = len(conversation_history)
        is_follow_up = prior_message_count > 0
        conversation_stage = "follow_up" if is_follow_up else "initial"
        logger.info(
            "Retrieved %s prior messages (conversation_stage=%s)",
            prior_message_count,
            conversation_stage
        )
        
        # Run the RAG workflow
        config = {"configurable": {"thread_id": thread_ts}}
        initial_state = {
            "query": query,
            "conversation_history": conversation_history,
            "is_follow_up": is_follow_up,
            "conversation_stage": conversation_stage,
            "iteration_count": 0,
            "metadata": {
                "slack_user_id": user_id,
                "slack_channel_type": channel_type,
                "is_follow_up": is_follow_up,
                "conversation_stage": conversation_stage,
                "prior_message_count": prior_message_count
            },
            # Slack context for progress updates (no say function to avoid serialization)
            "slack_channel": channel,
            "slack_thread_ts": thread_ts
        }
        
        result = rag_workflow.invoke(initial_state, config)
        
        response = result.get("final_response", "I encountered an error processing your question.")
        
        # Update the progress message with the final answer
        if _current_progress_message_ts:
            try:
                from slack_sdk import WebClient
                client = WebClient(token=SLACK_BOT_TOKEN)
                client.chat_update(
                    channel=channel,
                    ts=_current_progress_message_ts,
                    text=response,
                    thread_ts=thread_ts
                )
            except Exception as e:
                logger.warning(f"Failed to update progress message with final answer: {e}")
                # Fallback to sending new message
                say(text=response, thread_ts=thread_ts, channel=channel)
        else:
            # Send response in thread
            say(text=response, thread_ts=thread_ts, channel=channel)
        
    except Exception as e:
        logger.error(f"Error processing mention: {e}")
        say(text="I encountered an error processing your question. Please try again.", thread_ts=thread_ts, channel=channel)
    finally:
        # Clean up the say function
        clear_slack_say_function()

def handle_message(event, say):
    """Handle DMs."""
    if event.get("subtype") or event.get("bot_id"):
        return
    
    channel_type = event.get("channel_type")
    if channel_type not in {"im", "mpim"}:
        logger.debug("Ignoring message in channel_type=%s without mention", channel_type)
        return
    
    if _already_processed(event):
        return
    
    query = event.get("text", "")
    channel = event.get("channel", "")
    event_ts = event.get("ts") or event.get("event_ts", "")
    thread_ts = event.get("thread_ts", event_ts)
    user_id = event.get("user", "unknown")
    
    logger.info(f"Processing DM from {user_id} ({channel_type}): {query}")
    
    try:
        # Set the current say function for progress updates
        set_slack_say_function(say)
        
        # Retrieve conversation history from the thread
        conversation_history = get_conversation_history(
            channel,
            thread_ts,
            limit=10,
            latest_ts=event_ts
        )
        prior_message_count = len(conversation_history)
        is_follow_up = prior_message_count > 0
        conversation_stage = "follow_up" if is_follow_up else "initial"
        logger.info(
            "Retrieved %s prior messages in DM (conversation_stage=%s)",
            prior_message_count,
            conversation_stage
        )
        
        config = {"configurable": {"thread_id": thread_ts}}
        initial_state = {
            "query": query,
            "conversation_history": conversation_history,
            "is_follow_up": is_follow_up,
            "conversation_stage": conversation_stage,
            "iteration_count": 0,
            "metadata": {
                "slack_user_id": user_id,
                "slack_channel_type": channel_type,
                "is_follow_up": is_follow_up,
                "conversation_stage": conversation_stage,
                "prior_message_count": prior_message_count
            },
            # Slack context for progress updates (no say function to avoid serialization)
            "slack_channel": channel,
            "slack_thread_ts": thread_ts
        }
        
        result = rag_workflow.invoke(initial_state, config)
        response = result.get("final_response", "I encountered an error processing your question.")
        
        # Update the progress message with the final answer
        if _current_progress_message_ts:
            try:
                from slack_sdk import WebClient
                client = WebClient(token=SLACK_BOT_TOKEN)
                client.chat_update(
                    channel=channel,
                    ts=_current_progress_message_ts,
                    text=response
                )
            except Exception as e:
                logger.warning(f"Failed to update progress message with final answer: {e}")
                # Fallback to sending new message
                say(text=response, channel=channel)
        else:
            # Send response
            say(text=response, channel=channel)
        
    except Exception as e:
        logger.error(f"Error processing DM: {e}")
        say(text="I encountered an error processing your question. Please try again.", channel=channel)
    finally:
        # Clean up the say function
        clear_slack_say_function()

# ---------------- Flask App Initialization ----------------

# Initialize Flask app first
flask_app = Flask(__name__)

# Initialize Slack app with error handling
try:
    slack_app = App(
        token=SLACK_BOT_TOKEN,
        signing_secret=SLACK_SIGNING_SECRET
    )
    
    # Register Slack event handlers
    slack_app.event("app_mention")(handle_mention)
    slack_app.event("message")(handle_message)
    
    slack_handler = SlackRequestHandler(slack_app)
    logger.info("Slack app initialized successfully")
    
except Exception as e:
    logger.warning(f"Failed to initialize Slack app: {e}")
    # Create a dummy handler for when Slack is not available
    slack_app = None
    slack_handler = None

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle Slack events."""
    if slack_handler:
        return slack_handler.handle(flask_request)
    else:
        return {"error": "Slack integration not available"}, 503

@flask_app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "rag-v2",
        "vector_store_id": VECTOR_STORE_ID
    }

# ---------------- Main ----------------

if __name__ == "__main__":
    # Start the server
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting RAG v2 application on port {port}")
    flask_app.run(host="0.0.0.0", port=port)

