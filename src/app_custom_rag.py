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

SAFE_FALLBACK_MSG = (
    "I don't have complete information about this topic in our curriculum materials. "
    "Please reach out to the Education team on Slack for the specific details you need."
)

# Initialize Slack app for both direct execution and Heroku deployment
try:
    slack_app = App(
        token=os.environ["SLACK_BOT_TOKEN"],
        signing_secret=os.environ["SLACK_SIGNING_SECRET"]
    )
    handler = SlackRequestHandler(slack_app)
    logger.info("Slack app initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Slack app: {e}")
    slack_app = None
    handler = None

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Vector Store ID for file search
VECTOR_STORE_ID = os.environ.get("OPENAI_VECTOR_STORE_ID", "vs_68c14625e8d88191a27acb8a3845a706")

# Load configuration files
def load_config_file(filename):
    try:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(script_dir, 'assistant_config', filename)
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading {filename}: {e}")
        return ""

def load_master_prompt():
    return load_config_file('MASTER_PROMPT.md') or "You are a helpful assistant for Ironhack course information."

def load_generation_instructions():
    return load_config_file('GENERATION_INSTRUCTIONS.md')

def load_validation_instructions():
    return load_config_file('VALIDATION_INSTRUCTIONS.md')

def load_retrieval_instructions():
    return load_config_file('RETRIEVAL_INSTRUCTIONS.md')

MASTER_PROMPT = load_master_prompt()
GENERATION_INSTRUCTIONS = load_generation_instructions()
VALIDATION_INSTRUCTIONS = load_validation_instructions()
RETRIEVAL_INSTRUCTIONS = load_retrieval_instructions()

# --------------- Custom RAG Pipeline ---------------

class CustomRAGPipeline:
    def __init__(self, client, vector_store_id, master_prompt):
        self.client = client
        self.vector_store_id = vector_store_id
        self.master_prompt = master_prompt
        self._selected_file_ids = []
        self._id_to_filename = {}
        self._evidence_chunks = []  # captured chunks used during generation

    def _get_retrieval_instructions(self, query):
        """Generate enhanced retrieval instructions based on query type."""
        query_lower = query.lower()

        # Check for context-aware queries (pronouns, references)
        context_indicators = ['that', 'this', 'it', 'they', 'them', 'what about', 'how about', 'also', 'too']
        has_context_reference = any(indicator in query_lower for indicator in context_indicators)
        
        if has_context_reference:
            # Extract context-aware instructions from the loaded file
            lines = RETRIEVAL_INSTRUCTIONS.split('\n')
            for i, line in enumerate(lines):
                if 'For Context-Aware Queries' in line:
                    return '\n'.join(lines[i+1:]).strip()

        comparison_keywords = ['difference', 'compare', 'comparison', 'vs', 'versus', 'remote vs', 'onsite vs', 'berlin vs']
        program_variants = ['remote', 'berlin', 'onsite', 'online']
        is_comparison = any(k in query_lower for k in comparison_keywords)
        has_variants = any(v in query_lower for v in program_variants)

        if is_comparison or has_variants:
            # Extract comparison instructions from the loaded file
            lines = RETRIEVAL_INSTRUCTIONS.split('\n')
            for i, line in enumerate(lines):
                if 'For Comparison Queries' in line:
                    return '\n'.join(lines[i+1:]).strip()

        overview_keywords = ['tell me about', 'overview', 'explain', 'describe', 'what is', 'comprehensive']
        is_overview = any(k in query_lower for k in overview_keywords)
        if is_overview:
            # Extract overview instructions from the loaded file
            lines = RETRIEVAL_INSTRUCTIONS.split('\n')
            for i, line in enumerate(lines):
                if 'For Overview Queries' in line:
                    # Find the next section or end of file
                    next_section = len(lines)
                    for j in range(i+1, len(lines)):
                        if lines[j].startswith('###') or lines[j].startswith('##'):
                            next_section = j
                            break
                    return '\n'.join(lines[i+1:next_section]).strip()

        # Extract default instructions from the loaded file
        lines = RETRIEVAL_INSTRUCTIONS.split('\n')
        for i, line in enumerate(lines):
            if 'Default Instructions' in line:
                return '\n'.join(lines[i+1:]).strip()
        
        return "Search for relevant documents and return the most accurate and complete information found."

    def _enhance_query_with_context(self, query, conversation_context):
        """Enhance the query with relevant information from conversation context."""
        if not conversation_context or len(conversation_context) == 0:
            return query
        
        # Extract key information from recent conversation context
        context_info = []
        mentioned_programs = set()
        
        for msg in conversation_context[-4:]:  # Last 4 messages (2 exchanges)
            if msg.get('role') == 'user':
                # Extract program names, technologies, and key terms from user messages
                content = msg.get('content', '').lower()
                if any(term in content for term in ['data analytics', 'data science', 'web development', 'devops', 'cybersecurity', 'ux/ui', 'marketing']):
                    context_info.append(f"Previously discussed: {msg.get('content', '')}")
                    # Track mentioned programs
                    if 'web development' in content:
                        mentioned_programs.add('web development')
                    elif 'data analytics' in content:
                        mentioned_programs.add('data analytics')
                    elif 'data science' in content:
                        mentioned_programs.add('data science')
            elif msg.get('role') == 'assistant':
                # Extract program names and technologies from assistant responses
                content = msg.get('content', '').lower()
                if any(term in content for term in ['bootcamp', 'program', 'certification', 'course']):
                    # Extract the first sentence or key phrases
                    sentences = msg.get('content', '').split('.')
                    if sentences:
                        context_info.append(f"Previous response mentioned: {sentences[0].strip()}")
                    # Track mentioned programs from responses
                    if 'web development' in content:
                        mentioned_programs.add('web development')
                    elif 'data analytics' in content:
                        mentioned_programs.add('data analytics')
                    elif 'data science' in content:
                        mentioned_programs.add('data science')
        
        # For context reference queries, add specific program context
        if any(ref in query.lower() for ref in ['that', 'this', 'it', 'they', 'them']):
            if mentioned_programs:
                program_context = f"Referring to: {', '.join(mentioned_programs)}"
                context_info.insert(0, program_context)
        
        if context_info:
            context_summary = " ".join(context_info)
            enhanced_query = f"{query} (Context: {context_summary})"
            logger.info(f"Enhanced query with context: {enhanced_query}")
            return enhanced_query
        
        return query

    def retrieve_documents(self, query, conversation_context=None):
        """Retrieve multi-file context from the main vector store and prepare meta for citations."""
        try:
            logger.info(f"Retrieving documents from vector store for: {query}")

            # reset evidence on each retrieval to avoid cross-talk between queries
            self._evidence_chunks = []

            # Enhance query with conversation context
            enhanced_query = self._enhance_query_with_context(query, conversation_context)
            logger.info(f"Enhanced query for retrieval: {enhanced_query}")

            enhanced_instructions = self._get_retrieval_instructions(enhanced_query)
            MAX_NUM_RESULTS = 20
            TOP_K_FILES = 3
            MIN_SCORE = 0.5

            resp = self.client.responses.create(
                model="gpt-4o-mini",
                input=[{"role": "user", "content": query}],
                instructions=enhanced_instructions,
                tools=[{
                    "type": "file_search",
                    "vector_store_ids": [self.vector_store_id],
                    "max_num_results": MAX_NUM_RESULTS
                }],
                tool_choice={"type": "file_search"},
                include=["file_search_call.results"]
            )

            hits = []
            for out in getattr(resp, "output", []):
                fsc = getattr(out, "file_search_call", None)
                if hasattr(out, "results") and out.results:
                    hits = out.results
                    break
                if fsc:
                    if getattr(fsc, "results", None):
                        hits = fsc.results
                        break
                    if getattr(fsc, "search_results", None):
                        hits = fsc.search_results
                        break

            if not hits:
                logger.warning("No file_search results; trying vector_stores.search fallback")
                try:
                    vs = self.client.vector_stores.search(
                        vector_store_id=self.vector_store_id,
                        query=query
                    )
                    hits = getattr(vs, "data", []) or []
                except Exception as e:
                    logger.error(f"vector_stores.search fallback failed: {e}")

            if not hits:
                logger.warning("No hits from file search")
                self._selected_file_ids = []
                self._id_to_filename = {}
                return [], []

            # Group by filename, keep best chunk per file
            by_file = {}
            id_to_filename = {}
            for r in hits:
                fname = getattr(r, "filename", None)
                fid = getattr(r, "file_id", None)
                score = float(getattr(r, "score", 0.0) or 0.0)

                text = ""
                if hasattr(r, "text") and r.text:
                    text = r.text
                else:
                    parts = getattr(r, "content", []) or []
                    if parts and hasattr(parts[0], "text"):
                        text = parts[0].text

                if not fname or not fid or not text:
                    continue
                if score < MIN_SCORE:
                    continue

                id_to_filename[fid] = fname
                if fname not in by_file or score > by_file[fname]["score"]:
                    by_file[fname] = {"text": text, "score": score, "file_id": fid}

            if not by_file:
                logger.warning("Hits found but none passed filters")
                self._selected_file_ids = []
                self._id_to_filename = {}
                return [], []

            top = sorted(by_file.items(), key=lambda kv: kv[1]["score"], reverse=True)[:TOP_K_FILES]

            sources = []
            retrieved_content = []
            selected_file_ids = []
            for fname, entry in top:
                sources.append(fname)
                retrieved_content.append(entry["text"])
                selected_file_ids.append(entry["file_id"])

            self._selected_file_ids = selected_file_ids
            id_map = {entry["file_id"]: fname for fname, entry in top}
            id_map.update(id_to_filename)
            self._id_to_filename = id_map

            logger.info(f"File search: {len(retrieved_content)} chunks from {len(sources)} files -> {sources}")
            return retrieved_content, sources

        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            self._selected_file_ids = []
            self._id_to_filename = {}
            return [], []

    def _create_temp_store(self, file_ids):
        """Create an ephemeral vector store with only the selected files."""
        vs = self.client.vector_stores.create(
            name="tmp_rag_run",
            expires_after={"anchor": "last_active_at", "days": 1}
        )
        for fid in file_ids:
            try:
                self.client.vector_stores.files.create(vector_store_id=vs.id, file_id=fid)
            except Exception as e:
                logger.error(f"Error attaching file {fid} to temp store: {e}")
        return vs

    def _wait_until_indexed(self, vs_id, expected_count, timeout_s=30, poll_s=0.5):
        """Wait for files to be indexed in the vector store."""
        start = time.time()
        while time.time() - start < timeout_s:
            try:
                vs = self.client.vector_stores.retrieve(vs_id)
                fc = getattr(vs, "file_counts", None)
                if fc and getattr(fc, "completed", 0) >= expected_count and getattr(fc, "in_progress", 0) == 0:
                    return True
            except Exception as e:
                logger.error(f"Retrieve temp store failed: {e}")
            time.sleep(poll_s)
        return False

    def _extract_evidence_chunks(self, resp):
        """Collect the actual search results the model saw during generation."""
        chunks = []
        for out in getattr(resp, "output", []):
            fsc = getattr(out, "file_search_call", None)
            results = None
            if hasattr(out, "results") and out.results:
                results = out.results
            elif fsc and getattr(fsc, "results", None):
                results = fsc.results
            elif fsc and getattr(fsc, "search_results", None):
                results = fsc.search_results
            if not results:
                continue

            for r in results:
                fname = getattr(r, "filename", None)
                fid = getattr(r, "file_id", None)
                text = ""
                if hasattr(r, "text") and r.text:
                    text = r.text
                else:
                    parts = getattr(r, "content", []) or []
                    if parts and hasattr(parts[0], "text"):
                        text = parts[0].text
                if fname and fid and text:
                    chunks.append({"file_id": fid, "filename": fname, "text": text})

        # Deduplicate by (file_id, text)
        seen = set()
        deduped = []
        for c in chunks:
            key = (c["file_id"], c["text"])
            if key not in seen:
                seen.add(key)
                deduped.append(c)
        return deduped

    def _extract_citations_from_responses(self, resp):
        """Return ordered, deduped list of filenames cited."""
        id_to_filename = dict(self._id_to_filename) if hasattr(self, "_id_to_filename") else {}

        for out in getattr(resp, "output", []):
            fsc = getattr(out, "file_search_call", None)
            results = None
            if hasattr(out, "results") and out.results:
                results = out.results
            elif fsc and getattr(fsc, "results", None):
                results = fsc.results
            elif fsc and getattr(fsc, "search_results", None):
                results = fsc.search_results
            if results:
                for r in results:
                    fid = getattr(r, "file_id", None)
                    fname = getattr(r, "filename", None)
                    if fid and fname:
                        id_to_filename[fid] = fname

        used = []
        for out in getattr(resp, "output", []):
            for part in getattr(out, "content", []):
                annotations = getattr(part, "annotations", []) or []
                for ann in annotations:
                    if getattr(ann, "type", "") == "file_citation":
                        fid = getattr(ann, "file_id", None)
                        fname = getattr(ann, "filename", None)
                        if fid:
                            filename = fname if fname else id_to_filename.get(fid, fid)
                            used.append(filename)

        seen = set()
        used_unique = []
        for u in used:
            if u not in seen:
                used_unique.append(u)
                seen.add(u)
        return used_unique

    def generate_response(self, query, retrieved_docs, conversation_context=None, sources=None):
        """Generate with Responses + file_search on ephemeral store to get integrated citations."""
        try:
            sel_ids = getattr(self, "_selected_file_ids", []) or []
            if not sel_ids:
                logger.warning("No selected_file_ids; using fallback generation.")
                return self.generate_response_fallback(query, retrieved_docs, conversation_context, sources)

            vs = self._create_temp_store(sel_ids)
            ok = self._wait_until_indexed(vs.id, expected_count=len(sel_ids))
            if not ok:
                logger.warning("Temp vector store not indexed in time; using fallback.")
                return self.generate_response_fallback(query, retrieved_docs, conversation_context, sources)

            msgs = [{"role": "system", "content": self.master_prompt}]
            if conversation_context:
                for m in conversation_context[-6:]:
                    role = "user" if m["role"] == "user" else "assistant"
                    content = m["content"][:800] if len(m["content"]) > 800 else m["content"]
                    msgs.append({"role": role, "content": content})
            msgs.append({"role": "user", "content": query})

            resp = self.client.responses.create(
                model="gpt-4o",
                input=msgs,
                tools=[{"type": "file_search", "vector_store_ids": [vs.id], "max_num_results": 20}],
                tool_choice={"type": "file_search"},
                include=["output[*].file_search_call.search_results"]
            )

            # Capture evidence actually seen during generation
            self._evidence_chunks = self._extract_evidence_chunks(resp)

            answer = getattr(resp, "output_text", "") or ""
            used_filenames = self._extract_citations_from_responses(resp)

            if used_filenames:
                bullets = "\n".join([f"- {fn}" for fn in used_filenames])
                answer = f"{answer}\n\nSources:\n{bullets}"
                logger.info(f"Added sources to response: {used_filenames}")
            else:
                logger.warning("No citations found in response")

            try:
                self.client.vector_stores.delete(vs.id)
            except Exception as e:
                logger.warning(f"Temp store delete failed: {e}")

            logger.info(f"Generated with Responses. Citations: {used_filenames}")
            return answer

        except Exception as e:
            logger.error(f"Error generating response with citations: {e}")
            return "I'm having trouble accessing our curriculum materials right now. Please reach out to the Education team on Slack for the specific course details you need."

    def generate_response_fallback(self, query, retrieved_docs, conversation_context=None, sources=None):
        """Fallback generation using Chat Completions API."""
        try:
            context = "\n\n".join(retrieved_docs) if retrieved_docs else "No documents retrieved"
            source_info = "\n".join([f"- {source}" for source in sources]) if sources else "No specific sources"

            system_prompt = f"""{self.master_prompt}

RETRIEVED CONTEXT:
{context}

SOURCE INFORMATION:
{source_info}

{GENERATION_INSTRUCTIONS}
"""

            messages = [{"role": "system", "content": system_prompt}]
            if conversation_context:
                for msg in conversation_context[-6:]:
                    role = "user" if msg["role"] == "user" else "assistant"
                    content = msg["content"]
                    if len(content) > 800:
                        content = content[:800] + "..."
                    messages.append({"role": role, "content": content})
            messages.append({"role": "user", "content": query})

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.3
            )

            generated_response = response.choices[0].message.content
            logger.info(f"Generated fallback response ({len(generated_response)} chars)")

            if sources and len(sources) > 0 and "Source:" not in generated_response and "Sources:" not in generated_response:
                if len(sources) == 1:
                    generated_response += f"\n\nSource: {sources[0]}"
                else:
                    sources_list = ", ".join(sources)
                    generated_response += f"\n\nSources: {sources_list}"

            return generated_response

        except Exception as e:
            logger.error(f"Error generating fallback response: {e}")
            return "I'm having trouble accessing our curriculum materials right now. Please reach out to the Education team on Slack for the specific course details you need."

    def _strip_sources_section(self, text):
        """Remove trailing Sources section for validation."""
        if not text:
            return text
        marker = "\nSources:\n"
        idx = text.rfind(marker)
        if idx != -1:
            return text[:idx].strip()
        return text.strip()

    def validate_response(self, response, retrieved_docs):
        """Validate response against the exact evidence from generation. Paraphrase tolerant."""
        try:
            logger.info("Validating response against used evidence...")
            core_resp = self._strip_sources_section(response)

            # Prefer evidence captured during generation
            if getattr(self, "_evidence_chunks", None):
                evidence_text = "\n\n".join(c["text"] for c in self._evidence_chunks)
            else:
                evidence_text = "\n\n".join(retrieved_docs) if retrieved_docs else ""

            if not evidence_text.strip():
                # No evidence means we cannot validate. Fail open to avoid false positives.
                return {
                    "contains_only_retrieved_info": True,
                    "unsupported_claims": [],
                    "confidence": 1.0,
                    "explanation": "No evidence available. Treated as safe."
                }

            validation_instructions = f"""{VALIDATION_INSTRUCTIONS}

EVIDENCE TEXT:
{evidence_text}

RESPONSE TO VALIDATE:
{core_resp}
"""

            # Use Chat Completions JSON mode
            v = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Return only valid JSON with the requested keys. No prose."},
                    {"role": "user", "content": validation_instructions}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )

            validation_text = v.choices[0].message.content.strip()

            # Defensive parsing (strip accidental fences)
            if validation_text.startswith("```"):
                validation_text = validation_text.strip("`")
                if validation_text.lower().startswith("json"):
                    validation_text = validation_text[4:].strip()

            result_raw = json.loads(validation_text)

            result = {
                "contains_only_retrieved_info": bool(result_raw.get("contains_only_retrieved_info", False)),
                "unsupported_claims": [str(x) for x in result_raw.get("unsupported_claims", [])],
                "confidence": float(result_raw.get("confidence", 0)),
                "explanation": str(result_raw.get("explanation", "")),
            }

            # Optional softening: ignore one low confidence nit
            if (
                not result["contains_only_retrieved_info"]
                and len(result["unsupported_claims"]) == 1
                and result["confidence"] <= 0.6
            ):
                result["contains_only_retrieved_info"] = True
                result["unsupported_claims"] = []
                result["explanation"] = "Single low confidence nit ignored."
                result["confidence"] = 0.9

            logger.info(f"Validation result: {result}")
            return result

        except Exception as e:
            logger.error(f"Error validating response: {e}", exc_info=True)
            # Fail open to reduce false positives
            return {
                "contains_only_retrieved_info": True,
                "unsupported_claims": [],
                "confidence": 1.0,
                "explanation": "Validator error. Treated as supported."
            }

    def process_query(self, query, conversation_context=None):
        """Main RAG pipeline: retrieve -> generate -> validate."""
        start_time = time.time()

        # Step 1: Retrieve documents with conversation context
        retrieved_docs, sources = self.retrieve_documents(query, conversation_context)

        # If nothing was retrieved, reply with safe fallback and SKIP validation
        if not retrieved_docs:
            response = SAFE_FALLBACK_MSG
            total_time = time.time() - start_time
            validation = {
                "contains_only_retrieved_info": True,
                "unsupported_claims": [],
                "confidence": 1.0,
                "explanation": "Skipped validation because no documents were retrieved and safe fallback was used."
            }
            logger.info("No documents retrieved. Returned safe fallback without running validation.")
            logger.info(f"Custom RAG pipeline completed in {total_time:.2f}s")
            return {
                "response": response,
                "retrieved_docs_count": 0,
                "sources": sources,
                "validation": validation,
                "processing_time": total_time
            }

        # Step 2: Generate response
        response = self.generate_response(query, retrieved_docs, conversation_context, sources)

        # Step 3: Validate response
        validation = self.validate_response(response, retrieved_docs)

        # Step 4: Threshold handling
        confidence_threshold = 0.6
        if (validation.get('confidence', 0) < confidence_threshold or
            not validation.get('contains_only_retrieved_info', False)):
            logger.warning(
                f"Validation failed - confidence: {validation.get('confidence', 0):.2f}, "
                f"contains_only_retrieved_info: {validation.get('contains_only_retrieved_info', False)}"
            )
            logger.warning(f"Unsupported claims: {validation.get('unsupported_claims', [])}")

            response = SAFE_FALLBACK_MSG
            validation = {
                "contains_only_retrieved_info": True,
                "unsupported_claims": [],
                "confidence": 1.0,
                "explanation": "Used safe fallback due to validation failure."
            }

        total_time = time.time() - start_time
        logger.info(f"Custom RAG pipeline completed in {total_time:.2f}s")
        logger.info(f"Validation confidence: {validation.get('confidence', 0):.2f}")

        return {
            "response": response,
            "retrieved_docs_count": len(retrieved_docs),
            "sources": sources,
            "validation": validation,
            "processing_time": total_time
        }

# Initialize Custom RAG Pipeline
custom_rag = CustomRAGPipeline(client, VECTOR_STORE_ID, MASTER_PROMPT)

# --------------- Message Deduplication Cache ---------------

class MessageDeduplicationCache:
    def __init__(self, max_size=1000, ttl_seconds=300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache_file = os.path.join(tempfile.gettempdir(), 'message_cache_custom_rag.json')

    def load_cache(self):
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    try:
                        return json.load(f)
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Error loading message cache: {str(e)}")
        return {}

    def save_cache(self):
        try:
            with open(self.cache_file, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(self._cache, f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Error saving message cache: {str(e)}")

    @property
    def _cache(self):
        # Keep an in-memory fallback if needed; here we just reload each time for safety
        return self.load_cache()

    def is_duplicate(self, message_id):
        cache = self.load_cache()
        current_time = time.time()

        # Clean expired
        cache = {k: v for k, v in cache.items() if current_time - v < self.ttl_seconds}

        if message_id in cache:
            return True

        cache[message_id] = current_time

        if len(cache) > self.max_size:
            sorted_items = sorted(cache.items(), key=lambda x: x[1])
            cache = dict(sorted_items[-self.max_size:])

        try:
            with open(self.cache_file, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(cache, f)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Error saving message cache: {str(e)}")

        return False

dedup_cache = MessageDeduplicationCache()

# --------------- Conversation Management ---------------

def _mapping_path():
    return os.path.join(tempfile.gettempdir(), 'conversation_mapping_custom_rag.json')

def load_conversation_mapping():
    try:
        mapping_file = _mapping_path()
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
    try:
        mapping_file = _mapping_path()
        with open(mapping_file, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(mapping, f)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        logger.error(f"Error saving conversation mapping: {str(e)}")

def get_conversation_mapping():
    return load_conversation_mapping()

def update_conversation_mapping(conversation_id, conversation_data):
    mapping = load_conversation_mapping()
    mapping[conversation_id] = conversation_data
    save_conversation_mapping(mapping)
    return mapping

def add_message_to_conversation(conversation_id, role, content, timestamp=None):
    if timestamp is None:
        timestamp = time.time()

    mapping = load_conversation_mapping()
    if conversation_id not in mapping:
        mapping[conversation_id] = {"messages": []}

    mapping[conversation_id]["messages"].append({
        "role": role,
        "content": content,
        "timestamp": timestamp
    })

    if len(mapping[conversation_id]["messages"]) > 12:
        mapping[conversation_id]["messages"] = mapping[conversation_id]["messages"][-12:]

    save_conversation_mapping(mapping)
    return mapping

def get_conversation_context(conversation_id):
    mapping = load_conversation_mapping()
    if conversation_id not in mapping or not mapping[conversation_id].get("messages"):
        return []
    messages = mapping[conversation_id]["messages"]
    return messages[-8:] if len(messages) > 8 else messages

# --------------- Text Utilities ---------------

def clean_citations(text):
    """Clean up citations for Slack display."""
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]', r'\1', text)           # [text] -> text
    return text

def convert_markdown_to_slack(text):
    """Convert markdown formatting to Slack formatting."""
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)  # bold
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'_\1_', text)  # italics
    text = re.sub(r'^#+\s*(.+)$', r'*\1*', text, flags=re.MULTILINE)  # headers
    text = re.sub(r'^-\s+', '• ', text, flags=re.MULTILINE)  # bullets
    return text

# --------------- Slack Event Handlers ---------------

def process_message(event, say):
    """Process incoming messages using Custom RAG Pipeline."""
    user_message = event.get('text', '')

    message_id = event.get('ts', str(time.time()))
    if dedup_cache.is_duplicate(message_id):
        logger.info(f"Duplicate message detected: {message_id}")
        return

    conversation_id = event.get('thread_ts', event.get('channel'))
    logger.info(f"Processing message in conversation: {conversation_id}")
    logger.info(f"User message: {user_message}")

    current_conversation_mapping = get_conversation_mapping()
    if conversation_id not in current_conversation_mapping:
        conversation_data = {"messages": []}
        current_conversation_mapping = update_conversation_mapping(conversation_id, conversation_data)

    try:
        conversation_context = get_conversation_context(conversation_id)
        logger.info("Processing with Custom RAG Pipeline...")
        rag_result = custom_rag.process_query(user_message, conversation_context)
        assistant_message = rag_result["response"]

        logger.info("RAG Results:")
        logger.info(f"   Retrieved docs: {rag_result['retrieved_docs_count']}")
        logger.info(f"   Sources: {rag_result['sources']}")
        logger.info(f"   Validation confidence: {rag_result['validation'].get('confidence', 0):.2f}")
        logger.info(f"   Processing time: {rag_result['processing_time']:.2f}s")

        add_message_to_conversation(conversation_id, "user", user_message)
        add_message_to_conversation(conversation_id, "assistant", assistant_message)

        logger.info(f"Assistant response: {assistant_message[:100]}...")
        logger.info(f"Added message exchange to conversation history for: {conversation_id}")

    except Exception as e:
        logger.error(f"Error processing message with Custom RAG: {str(e)}")
        try:
            say("I'm having trouble accessing our course information right now. Please reach out to the Education team on Slack for the details you need.")
        except Exception as e2:
            logger.error(f"Error sending failure response: {str(e2)}")
        return

    cleaned_message = clean_citations(assistant_message)
    slack_message = convert_markdown_to_slack(cleaned_message)

    try:
        say(slack_message, thread_ts=event.get('ts'))
        logger.info("Response sent successfully")
    except Exception as e:
        logger.error(f"Error sending response: {str(e)}")
        try:
            say("I'm having trouble sending my response right now. Please try again, or reach out to the Education team on Slack.")
        except Exception as e2:
            logger.error(f"Error sending backup response: {str(e2)}")

# Register event handlers
@slack_app.event("app_mention")
def handle_mention(event, say):
    process_message(event, say)

@slack_app.event("message")
def handle_message(event, say):
    # Only process if it is a DM
    if event.get("channel_type") == "im":
        process_message(event, say)

# --------------- Flask app for Heroku ---------------

# Create Flask app that can be imported by gunicorn
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
        "api": "custom_rag",
        "pipeline": "responses_retrieval + chat_completions_generation",
        "validation": "enabled"
    }

if __name__ == "__main__":
    # Only run the Flask app when executed directly
    flask_app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))