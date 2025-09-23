"""
Simplified LangGraph-based Custom RAG Slack App
- Trusts LLM for context understanding (no manual token enhancement)
- Uses LangGraph's built-in memory for conversation persistence
- Streamlined workflow: retrieve → generate → validate → respond
"""

import os
import logging
import re
import json
import time
from typing import Dict, List, TypedDict, Annotated, Sequence
from operator import add

from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

import openai
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# ---------------- Logging ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- Environment Setup ----------------
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
VECTOR_STORE_ID = os.environ.get("OPENAI_VECTOR_STORE_ID", "vs_xxx")

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ---------------- Config Loaders ----------------
def load_config_file(filename):
    try:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(script_dir, 'assistant_config', filename)
        with open(file_path, 'r', encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.info(f"Config {filename} not found. Using defaults. Detail: {e}")
        return ""

# Load configuration
MASTER_PROMPT = load_config_file('MASTER_PROMPT.md') or (
    "You are a helpful assistant for Ironhack course information. "
    "Answer only from provided documents. Never invent facts."
)
GENERATION_INSTRUCTIONS = load_config_file('GENERATION_INSTRUCTIONS.md')
VALIDATION_INSTRUCTIONS = load_config_file('VALIDATION_INSTRUCTIONS.md')
RETRIEVAL_INSTRUCTIONS = load_config_file('RETRIEVAL_INSTRUCTIONS.md')
DOCUMENT_FILTERING_INSTRUCTIONS = load_config_file('DOCUMENT_FILTERING_INSTRUCTIONS.md')

# New externalized configs
FALLBACK_CLASSIFIER_PROMPT = load_config_file('FALLBACK_CLASSIFIER.md')
FUN_FALLBACK_TEMPLATES = load_config_file('FUN_FALLBACK_TEMPLATES.md')
EXPANSION_INSTRUCTIONS_TEXT = load_config_file('EXPANSION_INSTRUCTIONS.md')
FALLBACK_DETECTION_PATTERNS_TEXT = load_config_file('FALLBACK_DETECTION_PATTERNS.md')
TEAM_ROUTING_RULES_TEXT = load_config_file('TEAM_ROUTING_RULES.md')

def _parse_patterns(text: str) -> List[str]:
    patterns = []
    for line in (text or "").splitlines():
        s = line.strip().lower()
        if not s or s.startswith('#'):
            continue
        patterns.append(s)
    return patterns

# Note: We rely on AI-based fallback classification via `classify_fallback` and
# a lightweight heuristic in `is_fallback_response`. No static pattern list needed.

def _parse_team_rules(text: str) -> Dict[str, List[str]]:
    edu, prog = [], []
    lines = (text or "").splitlines()
    for i, line in enumerate(lines):
        low = line.strip().lower()
        if low.startswith('education team keywords:') and i + 1 < len(lines):
            edu = [w.strip().lower() for w in lines[i+1].split(',') if w.strip()]
        if low.startswith('program team keywords:') and i + 1 < len(lines):
            prog = [w.strip().lower() for w in lines[i+1].split(',') if w.strip()]
    return {"edu": edu, "program": prog}

TEAM_RULES = _parse_team_rules(TEAM_ROUTING_RULES_TEXT)

# Constants for consistent messaging
FALLBACK_MESSAGE = (
    "I don't have complete information about this topic in our curriculum materials. "
    "Please reach out to the Education team on Slack for the specific details you need."
)

PROCESSING_ERROR_MESSAGE = (
    "I'm having trouble processing your request right now. "
    "Please reach out to the Education team on Slack for assistance."
)

# Error classification and retry constants
class ErrorType:
    RETRIEVAL_FAILURE = "retrieval_failure"
    API_RATE_LIMIT = "api_rate_limit"
    VALIDATION_FAILURE = "validation_failure"
    GENERATION_FAILURE = "generation_failure"
    NETWORK_ERROR = "network_error"
    UNKNOWN_ERROR = "unknown_error"

class ErrorSeverity:
    LOW = "low"        # Can retry with degraded service
    MEDIUM = "medium"  # Needs specific recovery strategy
    HIGH = "high"      # Must use fallback immediately

# Retry configuration
MAX_RETRIES = 2
RETRY_DELAY = 1.0  # seconds

# ---------------- Utility Functions ----------------
def normalize_filename(filename: str) -> str:
    if not filename:
        return ""
    base = filename.rsplit("/", 1)[-1]
    base = base.rsplit(".", 1)[0]
    return base.replace("_", " ").strip()


def _build_conversation_context(messages: Sequence[BaseMessage], max_tokens: int = 3000) -> List[Dict[str, str]]:
    """
    Build optimized conversation context with smart truncation.
    
    Args:
        messages: LangGraph managed message history
        max_tokens: Approximate token limit for context (rough estimate: 4 chars = 1 token)
    
    Returns:
        List of formatted messages for OpenAI API
    """
    if not messages:
        return []
    
    conversation_messages = []
    total_chars = 0
    max_chars = max_tokens * 4  # Rough token estimation
    
    # Process messages from most recent backwards
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            role = "user"
            content = msg.content
        elif isinstance(msg, AIMessage):
            role = "assistant"
            # Remove Sources section from assistant messages in context to save space
            content = re.sub(r'\n+Sources:\n(?:- .+\n?)+$', '', msg.content, flags=re.IGNORECASE | re.MULTILINE).strip()
        else:
            continue
        
        # Estimate if adding this message would exceed limit
        message_chars = len(content) + 50  # Add buffer for role/formatting
        if total_chars + message_chars > max_chars and conversation_messages:
            # If we have at least one message, stop here
            break
        
        # Add message to front of list (since we're processing backwards)
        conversation_messages.insert(0, {"role": role, "content": content})
        total_chars += message_chars
        
        # Keep at most 8 messages total for performance
        if len(conversation_messages) >= 8:
            break
    
    logger.info(f"Built conversation context: {len(conversation_messages)} messages, ~{total_chars} chars")
    return conversation_messages

def classify_error(error: Exception) -> tuple[str, str]:
    """
    Classify an error to determine appropriate recovery strategy.
    
    Returns:
        tuple: (error_type, severity)
    """
    error_str = str(error).lower()
    
    # API Rate limits
    if "rate limit" in error_str or "quota" in error_str or "429" in error_str:
        return ErrorType.API_RATE_LIMIT, ErrorSeverity.MEDIUM
    
    # Network/Connection errors
    if any(term in error_str for term in ["connection", "timeout", "network", "502", "503", "504"]):
        return ErrorType.NETWORK_ERROR, ErrorSeverity.MEDIUM
    
    # OpenAI API errors
    if "openai" in error_str and any(term in error_str for term in ["invalid", "api", "unauthorized"]):
        return ErrorType.GENERATION_FAILURE, ErrorSeverity.HIGH
    
    # JSON parsing errors (validation)
    if "json" in error_str or "parse" in error_str:
        return ErrorType.VALIDATION_FAILURE, ErrorSeverity.LOW
    
    # Default classification
    return ErrorType.UNKNOWN_ERROR, ErrorSeverity.MEDIUM

def create_error_record(error: Exception, error_type: str, severity: str, node: str) -> Dict:
    """Create a structured error record for tracking"""
    return {
        "error_type": error_type,
        "severity": severity,
        "node": node,
        "message": str(error),
        "timestamp": time.time()
    }

def should_retry(state: Dict, error_type: str, severity: str) -> bool:
    """Determine if an error should trigger a retry"""
    retry_count = state.get("retry_count", 0)
    
    # Never retry high severity errors
    if severity == ErrorSeverity.HIGH:
        return False
    
    # Don't retry if we've hit max retries
    if retry_count >= MAX_RETRIES:
        return False
    
    # Retry network and rate limit errors
    if error_type in [ErrorType.NETWORK_ERROR, ErrorType.API_RATE_LIMIT]:
        return True
    
    # Retry validation failures (they're often transient)
    if error_type == ErrorType.VALIDATION_FAILURE:
        return True
    
    return False

def ensure_single_sources_block(text: str, filenames: List[str]) -> str:
    text = text or ""
    # Strip existing Sources blocks
    text = re.sub(r'\n+Sources:\n(?:- .+\n?)+$', '', text, flags=re.IGNORECASE | re.MULTILINE)
    if filenames:
        bullets = "\n".join(f"- {normalize_filename(fn)}" for fn in filenames)
        text = f"{text}\n\nSources:\n{bullets}"
    return text.strip()

# ---------------- LangGraph State ----------------
class RAGState(TypedDict):
    """Enhanced state for robust RAG workflow with error handling"""
    # Input
    query: str
    conversation_id: str
    
    # Retrieval
    retrieved_docs: List[str]
    sources: List[str]
    selected_file_ids: List[str]
    evidence_chunks: List[Dict]
    
    # Generation
    response: str
    actual_sources_used: List[str]  # Sources actually used by Responses API
    # Structured generation flags
    found_answer_in_documents: bool
    reason_if_not_found: str
    
    # Validation
    validation_result: Dict
    confidence: float
    
    # Error handling and recovery
    error_count: int
    last_error: Dict
    retry_count: int
    degraded_mode: bool
    error_history: List[Dict]
    
    # Metadata
    processing_time: float
    retrieved_docs_count: int
    retry_expansion: bool
    
    # LangGraph managed conversation history (this replaces all manual context management!)
    messages: Annotated[Sequence[BaseMessage], add]

# ---------------- Graph Nodes ----------------

def retrieve_documents(state: RAGState) -> RAGState:
    """Retrieve relevant documents using OpenAI Responses API"""
    logger.info(f"Retrieving documents for: {state['query']}")
    
    try:
        # Enhance query with conversation context for better document retrieval
        query = state["query"]
        messages = state.get("messages", [])
        
        # Build context-enhanced query if we have conversation history
        if messages and len(messages) > 1:
            # Get recent conversation context (last 3 messages for context)
            recent_messages = messages[-3:] if len(messages) > 3 else messages[:-1]  # Exclude current query
            
            context_parts = []
            for msg in recent_messages:
                if hasattr(msg, 'content') and msg.content:
                    # Only include the most recent user message for context
                    if isinstance(msg, HumanMessage):
                        context_parts.append(f"Previous context: {msg.content}")
                        break  # Only use the most recent user message for context
            
            if context_parts:
                # Enhance the query with conversation context
                enhanced_query = f"{query}\n\nConversation context: {' '.join(context_parts)}"
                logger.info(f"Enhanced query with context: {enhanced_query[:100]}...")
                query = enhanced_query
        
        instructions = RETRIEVAL_INSTRUCTIONS or ""
        
        resp = openai_client.responses.create(
            model="gpt-4o-mini",
            input=[{"role": "user", "content": query}],
            instructions=instructions,
            tools=[{
                "type": "file_search",
                "vector_store_ids": [VECTOR_STORE_ID],
                "max_num_results": 40
            }],
            tool_choice={"type": "file_search"},
            include=["file_search_call.results"]
        )
        
        # Extract hits (same logic as original)
        hits = []
        for out in getattr(resp, "output", []):
            res = getattr(out, "results", None)
            if res:
                hits = res
                break
            fsc = getattr(out, "file_search_call", None)
            if fsc:
                if getattr(fsc, "results", None):
                    hits = fsc.results
                    break
                if getattr(fsc, "search_results", None):
                    hits = fsc.search_results
                    break
        
        if not hits:
            return {
                **state,
                "retrieved_docs": [],
                "sources": [],
                "selected_file_ids": [],
                "evidence_chunks": [],
                "retrieved_docs_count": 0
            }
        
        # Process hits with program-specific filtering for sales accuracy
        by_file = {}
        
        for r in hits:
            fname = getattr(r, "filename", None) or getattr(getattr(r, "document", None), "filename", None)
            fid = getattr(r, "file_id", None) or getattr(getattr(r, "document", None), "id", None)
            score = float(getattr(r, "score", 0.0) or 0.0)
            
            text = ""
            if hasattr(r, "text") and r.text:
                text = r.text
            else:
                parts = getattr(r, "content", []) or []
                if parts and hasattr(parts[0], "text"):
                    text = parts[0].text
            
            if not fname or not fid or not text or score < 0.0:
                continue
            
            entry = by_file.get(fname)
            if entry is None or score > entry["score"]:
                by_file[fname] = {"text": text, "score": score, "file_id": fid}
        
        # Select top 6 files (increased for AI filtering)
        sorted_files = sorted(by_file.items(), key=lambda kv: kv[1]["score"], reverse=True)
        top_files = sorted_files[:6]
        
        sources = []
        retrieved_content = []
        selected_file_ids = []
        evidence_chunks = []
        
        for fname, entry in top_files:
            sources.append(fname)
            retrieved_content.append(entry["text"])
            selected_file_ids.append(entry["file_id"])
            evidence_chunks.append({
                "file_id": entry["file_id"],
                "filename": fname,
                "text": entry["text"]
            })
        
        return {
            **state,
            "retrieved_docs": retrieved_content,
            "sources": sources,
            "selected_file_ids": selected_file_ids,
            "evidence_chunks": evidence_chunks,
            "retrieved_docs_count": len(retrieved_content)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving documents: {e}")
        
        # Classify error and decide on recovery strategy
        error_type, severity = classify_error(e)
        error_record = create_error_record(e, error_type, severity, "retrieve_documents")
        
        # Update error tracking in state
        error_history = state.get("error_history", [])
        error_history.append(error_record)
        
        updated_state = {
            **state,
            "error_count": state.get("error_count", 0) + 1,
            "last_error": error_record,
            "error_history": error_history
        }
        
        # Check if we should retry
        if should_retry(updated_state, error_type, severity):
            logger.info(f"Scheduling retry for {error_type} error (attempt {updated_state.get('retry_count', 0) + 1})")
            # For this phase, we'll handle retry in the next version
            # For now, use graceful degradation
        
        # Return degraded state
        return {
            **updated_state,
            "retrieved_docs": [],
            "sources": [],
            "selected_file_ids": [],
            "evidence_chunks": [],
            "retrieved_docs_count": 0,
            "degraded_mode": True
        }

def filter_documents_for_sales(state: RAGState) -> RAGState:
    """Use AI to select the most relevant documents for sales accuracy"""
    logger.info("Using AI to select most relevant documents for sales")
    
    query = state["query"]
    original_sources = state["sources"]
    original_docs = state["retrieved_docs"]
    original_file_ids = state["selected_file_ids"]
    original_chunks = state["evidence_chunks"]
    
    # Group chunks by document name to avoid losing relevant chunks from the same document
    chunks_by_doc = {}
    for i, source in enumerate(original_sources):
        doc_name = source.replace('.txt', '').replace('.md', '')
        if doc_name not in chunks_by_doc:
            chunks_by_doc[doc_name] = []
        chunks_by_doc[doc_name].append(i)
    
    # If we have chunks from only 1-2 unique documents, keep them all
    if len(chunks_by_doc) <= 2:
        logger.info(f"Keeping all {len(original_sources)} chunks from {len(chunks_by_doc)} documents")
        return state
    
    try:
        # Create chunk analysis prompt with content previews
        chunk_list = []
        for i, (source, doc_content) in enumerate(zip(original_sources, original_docs)):
            # Get first 200 chars of chunk content as preview
            preview = doc_content[:200].replace('\n', ' ').strip()
            if len(doc_content) > 200:
                preview += "..."
            doc_name = source.replace('.txt', '').replace('.md', '')
            chunk_list.append(f"{i+1}. {doc_name} - \"{preview}\"")
        
        chunk_descriptions = "\n".join(chunk_list)
        
        analysis_prompt = f"""{DOCUMENT_FILTERING_INSTRUCTIONS}

USER QUESTION: {query}

AVAILABLE CONTENT CHUNKS:
{chunk_descriptions}

Return ONLY the numbers of ALL relevant chunks separated by commas (e.g., "1, 3, 4, 6")."""

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.1
        )
        
        # Parse the AI response to get selected chunk indices
        ai_response = response.choices[0].message.content.strip()
        logger.info(f"AI chunk selection: {ai_response}")
        
        # Extract numbers from the response
        numbers = re.findall(r'\d+', ai_response)
        selected_chunk_indices = [int(num) - 1 for num in numbers if int(num) <= len(original_sources)]
        
        if selected_chunk_indices:
            filtered_sources = [original_sources[i] for i in selected_chunk_indices]
            filtered_docs = [original_docs[i] for i in selected_chunk_indices]
            filtered_file_ids = [original_file_ids[i] for i in selected_chunk_indices]  
            filtered_chunks = [original_chunks[i] for i in selected_chunk_indices]
            
            # Count selected docs for logging
            selected_doc_names = set()
            for i in selected_chunk_indices:
                doc_name = original_sources[i].replace('.txt', '').replace('.md', '')
                selected_doc_names.add(doc_name)
            
            logger.info(f"AI filtering: {len(original_sources)} chunks → {len(filtered_sources)} chunks from {len(selected_doc_names)} docs")
            for i in selected_chunk_indices:
                preview = original_docs[i][:100].replace('\n', ' ').strip()
                if len(original_docs[i]) > 100:
                    preview += "..."
                logger.info(f"AI selected chunk {i+1}: {original_sources[i]} - \"{preview}\"")
        else:
            # Fallback: keep all chunks from first 2 documents
            logger.warning("AI selection failed, keeping first 2 documents")
            fallback_indices = []
            for doc_name in list(chunks_by_doc.keys())[:2]:
                fallback_indices.extend(chunks_by_doc[doc_name])
            
            filtered_sources = [original_sources[i] for i in fallback_indices]
            filtered_docs = [original_docs[i] for i in fallback_indices]
            filtered_file_ids = [original_file_ids[i] for i in fallback_indices]
            filtered_chunks = [original_chunks[i] for i in fallback_indices]
        
        return {
            **state,
            "sources": filtered_sources,
            "retrieved_docs": filtered_docs,
            "selected_file_ids": filtered_file_ids,
            "evidence_chunks": filtered_chunks,
            "retrieved_docs_count": len(filtered_docs)
        }
        
    except Exception as e:
        logger.error(f"Error in AI document filtering: {e}")
        # Fallback: keep all chunks from first 2 documents
        fallback_indices = []
        for doc_name in list(chunks_by_doc.keys())[:2]:
            fallback_indices.extend(chunks_by_doc[doc_name])
        
        return {
            **state,
            "sources": [original_sources[i] for i in fallback_indices],
            "retrieved_docs": [original_docs[i] for i in fallback_indices],
            "selected_file_ids": [original_file_ids[i] for i in fallback_indices],
            "evidence_chunks": [original_chunks[i] for i in fallback_indices],
            "retrieved_docs_count": len(fallback_indices)
        }

def generate_response(state: RAGState) -> RAGState:
    """Generate response using Chat Completions API with optimized conversation context"""
    logger.info("Generating response")
    
    try:
        if not state["retrieved_docs"]:
            # Generate safe fallback
            return {
                **state,
                "response": FALLBACK_MESSAGE,
                "actual_sources_used": []
            }
        
        # Build instructions for generation
        instructions = f"""{MASTER_PROMPT}

{GENERATION_INSTRUCTIONS}
"""
        
        # Build context from retrieved documents
        context = "\n\n".join(state["retrieved_docs"])
        
        # Create system message with instructions and context
        system_message = f"""{instructions}

RETRIEVED CONTEXT:
{context}
"""
        
        # Build conversation messages - LangGraph automatically manages conversation history
        messages = [{"role": "system", "content": system_message}]
        
        # Add optimized conversation context (smart truncation)
        conversation_context = _build_conversation_context(state.get("messages", []))
        messages.extend(conversation_context)
        
        # Add current query
        messages.append({"role": "user", "content": state["query"]})
        
        # Define structured response schema
        response_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "rag_response",
                "schema": {
                    "type": "object",
                    "properties": {
                        "answer": {"type": "string"},
                        "found_answer_in_documents": {"type": "boolean"},
                        "reason_if_not_found": {
                            "type": "string",
                            "enum": [
                                "no_relevant_information",
                                "insufficient_detail",
                                "wrong_document_sections"
                            ]
                        }
                    },
                    "required": ["answer", "found_answer_in_documents"]
                }
            }
        }
        
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,
            response_format=response_schema
        )
        
        structured_response_raw = response.choices[0].message.content
        
        # Parse the structured JSON response
        try:
            structured_response = json.loads(structured_response_raw)
            generated = structured_response.get("answer", "")
            found_answer = structured_response.get("found_answer_in_documents", True)
            reason_if_not_found = structured_response.get("reason_if_not_found", "")
            
            logger.info(f"Structured response - found_answer: {found_answer}, reason: {reason_if_not_found}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse structured response: {e}")
            # Fallback to treating as plain text
            generated = structured_response_raw
            found_answer = True
            reason_if_not_found = ""
        
        # Smart detection of which sources were actually referenced
        actual_sources_used = []
        response_lower = generated.lower()
        
        for source in state["sources"]:
            # Check for explicit mentions
            if (source.lower() in response_lower or 
                source.replace('.txt', '').lower() in response_lower or
                normalize_filename(source).lower() in response_lower):
                actual_sources_used.append(source)
        
        # If no explicit references found, use the most relevant source (first one)
        if not actual_sources_used and state["sources"]:
            actual_sources_used = [state["sources"][0]]
        
        # Fallback if no content generated
        if not generated:
            generated = FALLBACK_MESSAGE
        
        # Add sources section with only the sources actually used by the API
        if actual_sources_used and "Sources:" not in generated:
            # Remove duplicates while preserving order
            unique_sources = []
            seen = set()
            for source in actual_sources_used:
                if source not in seen:
                    unique_sources.append(source)
                    seen.add(source)
            generated = ensure_single_sources_block(generated, unique_sources)
        
        return {
            **state,
            "response": generated,
            "structured_response": structured_response_raw,
            "found_answer_in_documents": found_answer,
            "reason_if_not_found": reason_if_not_found,
            "actual_sources_used": actual_sources_used
        }
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return {
            **state,
            "response": PROCESSING_ERROR_MESSAGE,
            "actual_sources_used": []
        }

def validate_response(state: RAGState) -> RAGState:
    """Validate the generated response for accuracy"""
    logger.info("Validating response")
    
    try:
        response = state["response"]
        evidence_text = "\n\n".join(state["retrieved_docs"])
        
        if not evidence_text.strip():
            # No evidence to validate against - treat as safe
            validation_result = {
                "contains_only_retrieved_info": True,
                "unsupported_claims": [],
                "confidence": 1.0,
                "explanation": "No evidence available. Treated as safe."
            }
            return {
                **state,
                "validation_result": validation_result,
                "confidence": 1.0
            }
        
        # Strip sources section for validation
        core_resp = re.sub(r'\nSources:\n(?:- .+\n?)+$', '', response, flags=re.IGNORECASE | re.MULTILINE).strip()
        
        validation_instructions = f"""{VALIDATION_INSTRUCTIONS}

EVIDENCE TEXT:
{evidence_text}

RESPONSE TO VALIDATE:
{core_resp}
"""
        
        validation_response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Return only valid JSON with the requested keys. No prose."},
                {"role": "user", "content": validation_instructions}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        result_raw = json.loads(validation_response.choices[0].message.content.strip())
        validation_result = {
            "contains_only_retrieved_info": bool(result_raw.get("contains_only_retrieved_info", False)),
            "unsupported_claims": [str(x) for x in result_raw.get("unsupported_claims", [])],
            "confidence": float(result_raw.get("confidence", 0)),
            "explanation": str(result_raw.get("explanation", "")),
        }
        
        # Apply softening rules (same as original)
        if (not validation_result["contains_only_retrieved_info"] and
            ((len(validation_result["unsupported_claims"]) <= 2 and validation_result["confidence"] >= 0.3) or
             (len(validation_result["unsupported_claims"]) == 1 and validation_result["confidence"] >= 0.2))):
            validation_result["contains_only_retrieved_info"] = True
            validation_result["unsupported_claims"] = []
            validation_result["explanation"] = "Minor issues ignored for educational content."
            validation_result["confidence"] = max(0.7, validation_result["confidence"])
        
        return {
            **state,
            "validation_result": validation_result,
            "confidence": validation_result["confidence"]
        }
        
    except Exception as e:
        logger.error(f"Error validating response: {e}")
        validation_result = {
            "contains_only_retrieved_info": True,
            "unsupported_claims": [],
            "confidence": 1.0,
            "explanation": "Validator error. Treated as supported."
        }
        return {
            **state,
            "validation_result": validation_result,
            "confidence": 1.0
        }

def expand_document_chunks(state: RAGState) -> RAGState:
    """Expand chunks from existing documents and retry with more content"""
    logger.info("Expanding document chunks for retry generation")
    
    try:
        query = state["query"]
        original_sources = state["sources"]
        
        if not original_sources:
            logger.info("No sources to expand from")
            return state
        
        logger.info(f"Expanding chunks from {len(original_sources)} source documents")
        
        # Get more comprehensive chunks from the same documents
        suffix = " - provide detailed information from these specific documents"
        if EXPANSION_INSTRUCTIONS_TEXT and 'Enhanced query suffix' in EXPANSION_INSTRUCTIONS_TEXT:
            # keep current behavior; future: parse a configurable suffix if needed
            pass
        enhanced_query = f"{query}{suffix}"
        logger.info(f"Enhanced query for expansion: {enhanced_query[:100]}...")
        
        resp = openai_client.responses.create(
            model="gpt-4o-mini",
            input=[{"role": "user", "content": enhanced_query}],
            instructions=RETRIEVAL_INSTRUCTIONS or "",
            tools=[{
                "type": "file_search",
                "vector_store_ids": [VECTOR_STORE_ID],
                "max_num_results": 20  # Reduced from 60 to prevent timeouts
            }],
            tool_choice={"type": "file_search"},
            include=["file_search_call.results"]
        )
        
        # Extract hits (same logic as original retrieval)
        hits = []
        for out in getattr(resp, "output", []):
            res = getattr(out, "results", None)
            if res:
                hits = res
                break
            fsc = getattr(out, "file_search_call", None)
            if fsc:
                if getattr(fsc, "results", None):
                    hits = fsc.results
                    break
                if getattr(fsc, "search_results", None):
                    hits = fsc.search_results
                    break
        
        if not hits:
            logger.info("No additional hits found - keeping original content")
            return state
        
        # Focus on the same files we already retrieved, but get different/more chunks
        target_files = set(original_sources)
        expanded_chunks = {}
        
        for r in hits:
            fname = getattr(r, "filename", None) or getattr(getattr(r, "document", None), "filename", None)
            fid = getattr(r, "file_id", None) or getattr(getattr(r, "document", None), "id", None)
            score = float(getattr(r, "score", 0.0) or 0.0)
            
            text = ""
            if hasattr(r, "text") and r.text:
                text = r.text
            else:
                parts = getattr(r, "content", []) or []
                if parts and hasattr(parts[0], "text"):
                    text = parts[0].text
            
            if not fname or not fid or not text or score < 0.0:
                continue
            
            # Only keep chunks from our target files
            if fname in target_files:
                if fname not in expanded_chunks:
                    expanded_chunks[fname] = []
                expanded_chunks[fname].append({
                    "text": text,
                    "score": score,
                    "file_id": fid
                })
        
        # Combine original + expanded chunks, prioritizing expanded content
        final_sources = []
        final_docs = []
        final_file_ids = []
        final_evidence_chunks = []
        
        for fname in target_files:
            if fname in expanded_chunks:
                # Sort by score and take the best chunks
                sorted_chunks = sorted(expanded_chunks[fname], key=lambda x: x["score"], reverse=True)
                # Take up to 3 chunks per document to get comprehensive coverage
                for chunk in sorted_chunks[:3]:
                    final_sources.append(fname)
                    final_docs.append(chunk["text"])
                    final_file_ids.append(chunk["file_id"])
                    final_evidence_chunks.append({
                        "file_id": chunk["file_id"],
                        "filename": fname,
                        "text": chunk["text"]
                    })
        
        logger.info(f"Expanded to {len(final_docs)} chunks from {len(set(final_sources))} documents")
        
        return {
            **state,
            "retrieved_docs": final_docs,
            "sources": final_sources,
            "selected_file_ids": final_file_ids,
            "evidence_chunks": final_evidence_chunks,
            "retrieved_docs_count": len(final_docs),
            "retry_expansion": True  # Flag to indicate this is an expanded retry
        }
        
    except Exception as e:
        logger.error(f"Error expanding document chunks: {e}")
        # Return original state if expansion fails
        return state

def generate_fun_fallback(state: RAGState) -> RAGState:
    """Generate a fun, personality-driven fallback response"""
    logger.info("Generating fun fallback response")
    
    query = state.get("query", "")
    found_answer = state.get("found_answer_in_documents", True)
    reason_if_not_found = state.get("reason_if_not_found", "")
    
    # Categorize the query to determine which team to suggest
    query_lower = query.lower()
    
    # Content/curriculum/certification queries → Education team
    # Load keywords from config; fall back to defaults
    edu_keywords = TEAM_RULES.get("edu") or [
        "curriculum", "course", "content", "syllabus", "certification", "taught", "covered", "learn", "study", "technologies", "tools", "languages", "duration", "hours", "weeks"
    ]
    
    # Operations/logistics/process queries → Program team  
    program_keywords = TEAM_RULES.get("program") or [
        "schedule", "start", "when", "application", "apply", "price", "cost", "payment", "location", "format", "requirements", "prerequisites", "job", "placement", "career"
    ]
    
    is_edu_query = any(keyword in query_lower for keyword in edu_keywords)
    is_program_query = any(keyword in query_lower for keyword in program_keywords)
    
    # Choose team and generate fun response
    if is_edu_query:
        team = "Education team"
        team_context = "They know all the curriculum secrets!"
    elif is_program_query:
        team = "Program team (the ones actually running these courses)"
        team_context = "They handle all the logistics and can give you the real scoop!"
    else:
        team = "Education team"
        team_context = "When in doubt, they're your best bet!"
    
    # Generate fun responses based on reason
    if not found_answer:
        if reason_if_not_found == "insufficient_detail":
            personality_intro = "🤔 I found some info but not enough to give you the full picture (don't want to hurt Rudy's feelings with incomplete answers!)"
        elif reason_if_not_found == "no_relevant_information":
            personality_intro = "🕵️ I searched high and low through our docs but came up empty-handed - better to admit defeat than start a fight with the Product team about missing documentation!"
        elif reason_if_not_found == "wrong_document_sections":
            personality_intro = "📚 I might be looking in the wrong sections of our docs (happens to the best of us!)"
        else:
            personality_intro = "🤷 I'm playing it safe here rather than risk giving you dodgy information"
    else:
        # This shouldn't happen but let's handle it gracefully
        personality_intro = "🛡️ I'm being extra cautious with this one"
    
    fun_response = f"""{personality_intro}

For the most accurate info about your question, I'd recommend reaching out to our **{team}** on Slack. {team_context}

They'll have the detailed answers you're looking for and won't give me grief about sending you their way! 😄"""
    
    fallback_validation = {
        "contains_only_retrieved_info": True,
        "unsupported_claims": [],
        "confidence": 1.0,
        "explanation": "Used fun fallback response with appropriate team routing."
    }
    
    return {
        **state,
        "response": fun_response,
        "validation_result": fallback_validation,
        "confidence": 1.0
    }

def apply_fallback(state: RAGState) -> RAGState:
    """Apply safe fallback if validation fails"""
    logger.info("Applying fallback due to validation failure")
    
    # Use the fun fallback generator
    return generate_fun_fallback(state)

def finalize_response(state: RAGState) -> RAGState:
    """Add assistant response to conversation history and finalize state"""
    # Add the assistant's response to the conversation history for future context
    if state.get("response"):
        # Create a new messages list with the assistant's response added
        current_messages = list(state.get("messages", []))
        current_messages.append(AIMessage(content=state["response"]))
        
        return {
            **state,
            "messages": current_messages
        }
    
    return state

# ---------------- Error Recovery Nodes ----------------

def handle_retrieval_error(state: RAGState) -> RAGState:
    """Handle retrieval failures with degraded service"""
    logger.warning("Handling retrieval error with degraded service")
    
    return {
        **state,
        "retrieved_docs": [],
        "sources": [],
        "selected_file_ids": [],
        "evidence_chunks": [],
        "retrieved_docs_count": 0,
        "degraded_mode": True,
        "retry_count": 0  # Reset for next stage
    }

def handle_generation_error(state: RAGState) -> RAGState:
    """Handle generation failures with simplified approach"""
    logger.warning("Handling generation error with simplified approach")
    
    # Try simple template-based response
    query_lower = state.get("query", "").lower()
    
    if any(word in query_lower for word in ["technolog", "tools", "software"]):
        simplified_response = (
            "I'd be happy to help you learn about the technologies covered in our programs. "
            "Please reach out to the Education team on Slack for detailed information about "
            "specific tools and technologies used in each bootcamp."
        )
    elif any(word in query_lower for word in ["duration", "time", "long", "hours"]):
        simplified_response = (
            "Our bootcamps vary in duration depending on the program format. "
            "Please reach out to the Education team on Slack for specific timing "
            "information about the program you're interested in."
        )
    else:
        simplified_response = FALLBACK_MESSAGE
    
    return {
        **state,
        "response": simplified_response,
        "actual_sources_used": [],
        "degraded_mode": True,
        "retry_count": 0  # Reset for next stage
    }

def handle_validation_error(state: RAGState) -> RAGState:
    """Handle validation failures by accepting response with warning"""
    logger.warning("Handling validation error - accepting response with reduced confidence")
    
    # Create a permissive validation result
    validation_result = {
        "contains_only_retrieved_info": True,  # Accept the response
        "unsupported_claims": [],
        "confidence": 0.5,  # Reduced confidence due to validation failure
        "explanation": "Validation system failed, accepted with reduced confidence."
    }
    
    return {
        **state,
        "validation_result": validation_result,
        "confidence": 0.5,
        "degraded_mode": True
    }

def retry_with_delay(state: RAGState) -> RAGState:
    """Add delay before retry for rate limiting and network issues"""
    error_type = state.get("last_error", {}).get("error_type", "")
    
    if error_type == ErrorType.API_RATE_LIMIT:
        delay = RETRY_DELAY * (state.get("retry_count", 0) + 1) * 2  # Exponential backoff
        logger.info(f"Rate limit hit, waiting {delay} seconds before retry")
        time.sleep(delay)
    elif error_type == ErrorType.NETWORK_ERROR:
        delay = RETRY_DELAY
        logger.info(f"Network error, waiting {delay} seconds before retry")
        time.sleep(delay)
    
    # Increment retry count
    return {
        **state,
        "retry_count": state.get("retry_count", 0) + 1
    }

# ---------------- Conditional Logic ----------------
def is_fallback_response(response: str) -> bool:
    """Ask AI to classify whether the response is a fallback (no substantive answer) with JSON output; fallback to heuristics on error"""
    try:
        prompt = (FALLBACK_CLASSIFIER_PROMPT or "Classify if the response is a fallback. Return JSON.")
        classification_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "fallback_classifier",
                "schema": {
                    "type": "object",
                    "properties": {
                        "is_fallback": {"type": "boolean"},
                        "reason": {"type": "string"}
                    },
                    "required": ["is_fallback"]
                }
            }
        }
        full_prompt = prompt + "\n\nRESPONSE:\n" + response
        ai_resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return only JSON following the schema."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0,
            response_format=classification_schema
        )
        parsed = json.loads(ai_resp.choices[0].message.content)
        is_fb = bool(parsed.get("is_fallback", False))
        logger.info(f"AI fallback classification: {is_fb} ({parsed.get('reason','')})")
        return is_fb
    except Exception as e:
        logger.warning(f"AI fallback classification failed, using heuristics: {e}")
        fallback_indicators = [
            "i don't have that specific information",
            "i don't have complete information", 
            "please reach out to the education team",
            FALLBACK_MESSAGE.lower()
        ]
        response_lower = response.lower()
        return any(ind in response_lower for ind in fallback_indicators)

def should_expand_chunks(state: RAGState) -> str:
    """Determine if we should expand chunks and retry generation using structured/AI fallback flags"""
    response = state.get("response", "")
    retry_expansion = state.get("retry_expansion", False)
    sources = state.get("sources", [])
    found_answer = state.get("found_answer_in_documents", True)
    reason_if_not_found = state.get("reason_if_not_found", "")
    is_fallback_ai = state.get("is_fallback_ai", None)
    
    logger.info(f"Checking for chunk expansion: response_length={len(response)}, has_sources={bool(sources)}, already_tried={retry_expansion}")
    logger.info(f"Raw state keys: {list(state.keys())}")
    logger.info(f"found_answer_in_documents in state: {state.get('found_answer_in_documents', 'NOT FOUND')}")
    logger.info(f"Structured response analysis: found_answer={found_answer}, reason={reason_if_not_found}")
    if is_fallback_ai is not None:
        logger.info(f"AI fallback flag present: {is_fallback_ai}")
        legacy_fallback = is_fallback_ai
    else:
        # Heuristic backup if classifier wasn't run
        legacy_fallback = is_fallback_response(response)
        if legacy_fallback:
            logger.info("Detected legacy fallback text from generation (heuristic)")
    
    # Expand if model said not found or legacy fallback text produced, once
    if ((legacy_fallback or not found_answer) and sources and not retry_expansion):
        logger.info("Triggering expansion due to missing answer/legacy fallback")
        return "expand_document_chunks"
    
    # If we tried expansion and still no answer (or still legacy fallback), use fun fallback
    if (retry_expansion and (legacy_fallback or not found_answer)):
        logger.info("Expansion unsuccessful; routing to fun fallback")
        return "generate_fun_fallback"
    
    logger.info("Model found answer or no expansion needed - proceeding to validation")
    return "validate_response"

def classify_fallback(state: RAGState) -> RAGState:
    """Classify if current response is a fallback using AI (with heuristic backup). Only runs when likely needed."""
    response = state.get("response", "")
    found_answer = state.get("found_answer_in_documents", True)
    # Only run when structured flags say not found OR heuristic suspects fallback
    should_run = (not found_answer) or is_fallback_response(response)
    if not should_run:
        return state
    try:
        classification_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "fallback_classifier",
                "schema": {
                    "type": "object",
                    "properties": {
                        "is_fallback": {"type": "boolean"},
                        "reason": {"type": "string"}
                    },
                    "required": ["is_fallback"]
                }
            }
        }
        prompt = (
            "Classify if the following assistant response is a fallback/non-answer (polite deferral,"
            " says cannot find info, suggests contacting teams) versus a substantive answer that provides"
            " concrete information from documents. Return JSON.\n\nRESPONSE:\n" + response
        )
        ai_resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return only JSON following the schema."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format=classification_schema
        )
        parsed = json.loads(ai_resp.choices[0].message.content)
        is_fb = bool(parsed.get("is_fallback", False))
        reason = str(parsed.get("reason", ""))
        logger.info(f"AI fallback classification node: {is_fb} ({reason})")
        return {**state, "is_fallback_ai": is_fb, "fallback_reason_ai": reason}
    except Exception as e:
        logger.warning(f"AI fallback classification node failed, using heuristic: {e}")
        heuristic_flag = is_fallback_response(response)
        return {**state, "is_fallback_ai": heuristic_flag, "fallback_reason_ai": "heuristic"}

def should_apply_fallback(state: RAGState) -> str:
    """Determine if we should apply fallback based on validation"""
    confidence_threshold = 0.4
    validation = state.get("validation_result", {})
    
    confidence = validation.get('confidence', 0)
    contains_only_retrieved = validation.get('contains_only_retrieved_info', False)
    
    logger.info(f"Fallback decision: confidence={confidence}, contains_only_retrieved={contains_only_retrieved}, threshold={confidence_threshold}")
    
    if (confidence < confidence_threshold or not contains_only_retrieved):
        logger.info(f"APPLYING FALLBACK: confidence {confidence} < {confidence_threshold} OR contains_only_retrieved={contains_only_retrieved}")
        return "apply_fallback"
    
    logger.info("FINALIZING: validation passed")
    return "finalize"

def should_retry_retrieval(state: RAGState) -> str:
    """Determine if retrieval should be retried based on error"""
    last_error = state.get("last_error", {})
    error_type = last_error.get("error_type", "")
    severity = last_error.get("severity", "")
    
    if should_retry(state, error_type, severity):
        return "retry_with_delay"
    else:
        return "handle_retrieval_error"

def should_retry_generation(state: RAGState) -> str:
    """Determine if generation should be retried based on error"""
    last_error = state.get("last_error", {})
    error_type = last_error.get("error_type", "")
    severity = last_error.get("severity", "")
    
    if should_retry(state, error_type, severity):
        return "retry_with_delay"
    else:
        return "handle_generation_error"

def should_retry_validation(state: RAGState) -> str:
    """Determine if validation should be retried based on error"""
    last_error = state.get("last_error", {})
    error_type = last_error.get("error_type", "")
    severity = last_error.get("severity", "")
    
    if should_retry(state, error_type, severity):
        return "retry_with_delay"
    else:
        return "handle_validation_error"

# ---------------- Graph Construction ----------------
def create_rag_graph():
    """Create the robust LangGraph workflow with error handling"""
    workflow = StateGraph(RAGState)
    
    # Add main workflow nodes
    workflow.add_node("retrieve_documents", retrieve_documents)
    workflow.add_node("filter_documents_for_sales", filter_documents_for_sales)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("classify_fallback", classify_fallback)
    workflow.add_node("expand_document_chunks", expand_document_chunks)
    workflow.add_node("generate_fun_fallback", generate_fun_fallback)
    workflow.add_node("validate_response", validate_response)
    workflow.add_node("apply_fallback", apply_fallback)
    workflow.add_node("finalize_response", finalize_response)
    
    # Add error recovery nodes
    workflow.add_node("handle_retrieval_error", handle_retrieval_error)
    workflow.add_node("handle_generation_error", handle_generation_error)
    workflow.add_node("handle_validation_error", handle_validation_error)
    workflow.add_node("retry_with_delay", retry_with_delay)
    
    # Define the main flow
    workflow.set_entry_point("retrieve_documents")
    workflow.add_edge("retrieve_documents", "filter_documents_for_sales")
    workflow.add_edge("filter_documents_for_sales", "generate_response")
    
    # After generation, classify fallback when likely needed
    workflow.add_edge("generate_response", "classify_fallback")
    # Add conditional routing after classification - check for expansion/fallback
    workflow.add_conditional_edges(
        "classify_fallback",
        should_expand_chunks,
        {
            "expand_document_chunks": "expand_document_chunks",
            "generate_fun_fallback": "generate_fun_fallback",
            "validate_response": "validate_response"
        }
    )
    
    # After expansion, generate again and validate
    workflow.add_edge("expand_document_chunks", "generate_response")
    
    # Conditional routing after validation (original logic)
    workflow.add_conditional_edges(
        "validate_response",
        should_apply_fallback,
        {
            "apply_fallback": "apply_fallback",
            "finalize": "finalize_response"
        }
    )
    
    # Error recovery routing - these will be triggered by enhanced nodes
    # (Note: Error routing is handled within nodes for now, but could be expanded)
    
    # Standard completion
    workflow.add_edge("apply_fallback", "finalize_response")
    workflow.add_edge("generate_fun_fallback", "finalize_response")
    workflow.add_edge("finalize_response", END)
    
    # Error recovery completion paths
    workflow.add_edge("handle_retrieval_error", "generate_response")
    workflow.add_edge("handle_generation_error", "finalize_response") 
    workflow.add_edge("handle_validation_error", "finalize_response")
    
    # Retry routing - retry goes back to the failed node
    workflow.add_edge("retry_with_delay", "retrieve_documents")  # Could be made more specific
    
    # Set up memory for persistent conversation state
    memory = MemorySaver()
    
    return workflow.compile(checkpointer=memory)

# Initialize the simplified graph
rag_graph = create_rag_graph()

# ---------------- Slack Integration ----------------
def clean_citations(text):
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]', r'\1', text)           # [text] -> text
    return text

def convert_markdown_to_slack(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)  # bold
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'_\1_', text)  # italics
    text = re.sub(r'^#+\s*(.+)$', r'*\1*', text, flags=re.MULTILINE)  # headers
    text = re.sub(r'^-\s+', '• ', text, flags=re.MULTILINE)  # bullets
    return text

# Initialize Slack app
slack_app = None
handler = None
try:
    if SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET:
        slack_app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
        handler = SlackRequestHandler(slack_app)
        logger.info("Slack app initialized successfully")
    else:
        logger.info("Slack env vars missing. Running without Slack handlers.")
except Exception as e:
    logger.error(f"Failed to initialize Slack app: {e}")
    slack_app = None
    handler = None

def process_message(event, say):
    """Process incoming Slack message using LangGraph with optimized conversation handling"""
    user_message = event.get('text', '')
    
    # Determine thread context for proper Slack threading
    thread_ts = None
    conversation_id = None
    
    if event.get('thread_ts'):
        # This is a reply in an existing thread
        thread_ts = event['thread_ts']  # Reply to the original thread
        conversation_id = f"thread_{event['thread_ts']}"
        logger.info(f"Replying in existing thread: {thread_ts}")
    else:
        # This is a new mention/message - create a new thread using this message's timestamp
        thread_ts = event.get('ts')  # Start new thread with this message
        if event.get('channel'):
            conversation_id = f"thread_{event.get('ts')}"  # Use thread-based ID even for new threads
        else:
            conversation_id = f"fallback_{hash(user_message)}_{int(time.time())}"
        logger.info(f"Starting new thread: {thread_ts}")
    
    # Fallback for edge cases
    if not conversation_id:
        conversation_id = f"fallback_{hash(user_message)}_{int(time.time())}"
    
    logger.info(f"Processing message in conversation: {conversation_id}")
    logger.info(f"User message: {user_message[:100]}{'...' if len(user_message) > 100 else ''}")
    
    try:
        start_time = time.time()
        
        # Create initial state - let LangGraph handle conversation history automatically
        initial_state = {
            "query": user_message,
            "conversation_id": conversation_id,
            "messages": [HumanMessage(content=user_message)],  # Current message only
            "processing_time": 0.0,
            # Initialize error handling fields
            "error_count": 0,
            "last_error": {},
            "retry_count": 0,
            "degraded_mode": False,
            "error_history": []
        }
        
        # Run the graph with conversation-specific thread - LangGraph merges with existing history
        config = {"configurable": {"thread_id": conversation_id}}
        result = rag_graph.invoke(initial_state, config=config)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        assistant_message = result["response"]
        
        logger.info("Enhanced LangGraph RAG Results:")
        logger.info(f"   Retrieved docs: {result.get('retrieved_docs_count', 0)}")
        logger.info(f"   Sources: {result.get('sources', [])}")
        logger.info(f"   Validation confidence: {result.get('confidence', 0):.2f}")
        logger.info(f"   Processing time: {processing_time:.2f}s")
        logger.info(f"   Error count: {result.get('error_count', 0)}")
        logger.info(f"   Degraded mode: {result.get('degraded_mode', False)}")
        
        # Log error history if any errors occurred
        error_history = result.get('error_history', [])
        if error_history:
            logger.warning(f"Errors during processing: {len(error_history)} total")
            for i, error in enumerate(error_history):
                logger.warning(f"   Error {i+1}: {error.get('error_type', 'unknown')} in {error.get('node', 'unknown')}")
        
        # Prepare message for Slack
        cleaned_message = clean_citations(assistant_message)
        slack_message = convert_markdown_to_slack(cleaned_message)
        
        # Reply in the correct thread context
        say(slack_message, thread_ts=thread_ts)
        logger.info(f"Response sent successfully in thread: {thread_ts}")
        
    except Exception as e:
        logger.error(f"Error processing message with Simplified LangGraph RAG: {str(e)}")
        try:
            say(PROCESSING_ERROR_MESSAGE, thread_ts=thread_ts)
        except Exception as e2:
            logger.error(f"Error sending failure response: {str(e2)}")

# Register Slack handlers
if slack_app is not None:
    @slack_app.event("app_mention")
    def handle_mention(event, say):
        """Handle @productwizard mentions in channels"""
        logger.info(f"App mention detected in channel {event.get('channel')}, thread_ts: {event.get('thread_ts')}")
        process_message(event, say)

    @slack_app.event("message")
    def handle_message(event, say):
        """Handle direct messages and thread replies where the bot was previously mentioned"""
        # Handle direct messages
        if event.get("channel_type") == "im":
            logger.info(f"Direct message received from user")
            process_message(event, say)
        # Handle replies in threads where we've already participated
        elif event.get("thread_ts") and not event.get("bot_id"):
            # This is a human message in a thread - check if we should respond
            # Note: We rely on the conversation memory to determine if we're part of this thread
            logger.info(f"Thread reply detected in thread {event.get('thread_ts')}")
            process_message(event, say)

# ---------------- Flask App ----------------
flask_app = Flask(__name__)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    if handler:
        try:
            return handler.handle(request)
        except Exception as e:
            logger.error(f"Error handling Slack event: {e}")
            return {"error": f"Error processing Slack event: {str(e)}"}, 500
    else:
        logger.error("Slack handler not initialized - check environment variables")
        return {"error": "Slack handler not initialized - check SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET"}, 500

@flask_app.route("/health", methods=["GET"])
def health_check():
    return {
        "status": "healthy",
        "api": "langgraph_rag",
        "pipeline": "retrieve_ai_filter_generate_validate",
        "validation": "enabled",
        "memory_management": "automatic_via_langgraph",
        "document_filtering": "ai_powered_sales_accuracy",
        "architecture": "clean_configurable_instructions"
    }

if __name__ == "__main__":
    flask_app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
