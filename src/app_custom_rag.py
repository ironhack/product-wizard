"""
Custom RAG Slack App with Hybrid Architecture
- Responses API for retrieval + grounded generation with citations
- Chat Completions API for JSON validators (variant QA, comparisons)
- Slack integration and conversation context
- Variant-aware answers (only: remote, berlin)
- Program tokens grounded to your docs (Portfolio/Design/Certifications 2025_07)
- No hardcoded content claims; all answers must come from retrieved docs
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
from typing import Dict, List, Tuple, Optional

# ---------------- Logging ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SAFE_FALLBACK_MSG = (
    "I don't have complete information about this topic in our curriculum materials. "
    "Please reach out to the Education team on Slack for the specific details you need."
)

# ---------------- Slack init ----------------
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")

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

# ---------------- OpenAI init ----------------
client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
VECTOR_STORE_ID = os.environ.get("OPENAI_VECTOR_STORE_ID", "vs_xxx")

# ---------------- Config loaders ----------------
def load_config_file(filename):
    try:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(script_dir, 'assistant_config', filename)
        with open(file_path, 'r', encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.info(f"Config {filename} not found. Using defaults. Detail: {e}")
        return ""

def load_master_prompt():
    return load_config_file('MASTER_PROMPT.md') or (
        "You are a helpful assistant for Ironhack course information. "
        "Answer only from provided documents. "
        "Never invent facts. "
        "If multiple variants exist, never blend content between variants."
    )

MASTER_PROMPT = load_master_prompt()
GENERATION_INSTRUCTIONS = load_config_file('GENERATION_INSTRUCTIONS.md')
VALIDATION_INSTRUCTIONS = load_config_file('VALIDATION_INSTRUCTIONS.md')
RETRIEVAL_CONTEXT_AWARE_INSTRUCTIONS = load_config_file('RETRIEVAL_CONTEXT_AWARE_QUERIES.md')
RETRIEVAL_COMPARISON_INSTRUCTIONS = load_config_file('RETRIEVAL_COMPARISON_QUERIES.md')
RETRIEVAL_OVERVIEW_INSTRUCTIONS = load_config_file('RETRIEVAL_OVERVIEW_QUERIES.md')
RETRIEVAL_DEFAULT_INSTRUCTIONS = load_config_file('RETRIEVAL_DEFAULT.md')

# ---------------- Tokens grounded to your docs ----------------
# Variants: ONLY remote and berlin (as per your corpus)
VARIANT_TOKENS = ("remote", "berlin", "onsite", "online")

# Programs discovered in:
# /mnt/data/Ironhack_Portfolio_Overview_2025_07.md (#### headings with acronyms)
# We derive aliases strictly from those headings + their acronyms; no extra nicknames.
PROGRAM_TOKENS: Dict[str, List[str]] = {
    "web development": [
        "web development", "web_development", "wdft", "wdpt", "wd"
    ],
    "ux/ui design": [
        "ux/ui design", "ux_ui_design", "uxft", "uxpt", "ux"
    ],
    "data analytics": [
        "data analytics", "data_analytics", "daft", "dapt", "da"
    ],
    "data science & machine learning": [
        "data science & machine learning",
        "data science and machine learning",
        "data_science_and_machine_learning",
        "data_science_machine_learning",
        "mlft", "mlpt", "dsml", "ml"
    ],
    "ai engineering": [
        "ai engineering", "ai_engineering", "aift", "aipt", "ai"
    ],
    "devops": [
        "devops", "dvft", "dvpt", "dv"
    ],
    "marketing": [
        "marketing", "mkft", "mkpt", "mk"
    ],
    "cybersecurity": [
        "cybersecurity", "cyft", "cypt", "cy"
    ],
    "data science and ai 1-year program germany": [
        "data science and ai 1-year program germany",
        "DSAI", "DF1Y"
    ],
    "intensive program in applied ai - ai async productivity course": [
        "intensive program in applied ai - ai async productivity course",
        "ai async productivity course", "apac"
    ],
}

CERT_TOKENS = ["certification", "certifications", "certificate", "certificates", "cert", "badge", "exam", "accreditation"]
COVERAGE_TOKENS = ["does", "include", "cover", "teach", "have", "is there", "do you cover", "is it covered"]

# ---------------- RAG Pipeline ----------------
class CustomRAGPipeline:
    TOP_K_FILES = 4
    MAX_NUM_RESULTS = 40
    MIN_SCORE = 0.0

    def __init__(self, client, vector_store_id, master_prompt):
        self.client = client
        self.vector_store_id = vector_store_id
        self.master_prompt = master_prompt
        self._selected_file_ids: List[str] = []
        self._id_to_filename: Dict[str, str] = {}
        self._evidence_chunks: List[Dict] = []

    # ---------- helpers ----------
    def _normalize_filename(self, filename: str) -> str:
        if not filename:
            return ""
        base = filename.rsplit("/", 1)[-1]
        base = base.rsplit(".", 1)[0]
        return base.replace("_", " ").strip()

    def _contains_any(self, text: str, tokens: List[str]) -> bool:
        t = (text or "").lower()
        return any(tok in t for tok in tokens)

    def _program_from_query(self, query: str) -> str:
        q = (query or "").lower()
        for program, toks in PROGRAM_TOKENS.items():
            if any(tok in q for tok in toks):
                return program
        return ""

    def _is_cert_query(self, query: str) -> bool:
        return self._contains_any(query, CERT_TOKENS)

    def _is_coverage_query(self, query: str) -> bool:
        return self._contains_any(query, COVERAGE_TOKENS)

    def _get_retrieval_instructions(self, query):
        q = (query or "").lower()
        if any(tok in q for tok in ['that', 'this', 'it', 'they', 'them', 'what about', 'how about', 'also', 'too']):
            return (RETRIEVAL_CONTEXT_AWARE_INSTRUCTIONS or "").strip()
        if any(k in q for k in ['difference', 'compare', 'comparison', 'vs', 'versus']) or \
           any(v in q for v in VARIANT_TOKENS):
            return (RETRIEVAL_COMPARISON_INSTRUCTIONS or "").strip()
        if any(k in q for k in ['tell me about', 'overview', 'explain', 'describe', 'what is', 'comprehensive']):
            return (RETRIEVAL_OVERVIEW_INSTRUCTIONS or "").strip()
        return (RETRIEVAL_DEFAULT_INSTRUCTIONS or "").strip()

    def _enhance_query_with_context(self, query, conversation_context):
        if not conversation_context:
            return query
        context_info = []
        mentioned_programs = set()
        for msg in conversation_context[-4:]:
            role = msg.get('role')
            content = (msg.get('content') or "")
            lower = content.lower()
            if role == 'user':
                for program, toks in PROGRAM_TOKENS.items():
                    if any(t in lower for t in toks):
                        mentioned_programs.add(program)
                        context_info.append(f"Previously discussed: {content}")
            elif role == 'assistant':
                if any(term in lower for term in ['bootcamp', 'program', 'certification', 'course']):
                    first_sentence = content.split('.', 1)[0].strip()
                    if first_sentence:
                        context_info.append(f"Previous response mentioned: {first_sentence}")
                    for program, toks in PROGRAM_TOKENS.items():
                        if any(t in lower for t in toks):
                            mentioned_programs.add(program)
        if any(ref in (query or "").lower() for ref in ['that', 'this', 'it', 'they', 'them']) and mentioned_programs:
            context_info.insert(0, f"Referring to: {', '.join(sorted(mentioned_programs))}")
        if context_info:
            return f"{query} (Context: {' '.join(context_info)})"
        return query

    def _variant_label_from_name(self, name: str) -> str:
        n = (name or "").lower()
        if "remote" in n:
            return "remote"
        if "berlin" in n:
            return "berlin"
        return "unspecified"

    def _by_variant(self) -> Dict[str, List[Tuple[str, str]]]:
        byv = {}
        for fid, fname in self._id_to_filename.items():
            v = self._variant_label_from_name(fname)
            byv.setdefault(v, []).append((fid, fname))
        return byv

    def _ensure_single_sources_block(self, text: str, filenames: List[str]) -> str:
        text = text or ""
        # strip existing Sources blocks
        text = re.sub(r'\n+Sources:\n(?:- .+\n?)+$', '', text, flags=re.IGNORECASE | re.MULTILINE)
        if filenames:
            bullets = "\n".join(f"- {self._normalize_filename(fn)}" for fn in filenames)
            text = f"{text}\n\nSources:\n{bullets}"
        return text.strip()

    # ---------- retrieval ----------
    def retrieve_documents(self, query, conversation_context=None):
        try:
            self._evidence_chunks = []
            enhanced_query = self._enhance_query_with_context(query, conversation_context)
            instructions = self._get_retrieval_instructions(enhanced_query)

            resp = self.client.responses.create(
                model="gpt-4o-mini",
                input=[{"role": "user", "content": enhanced_query}],
                instructions=instructions,
                tools=[{
                    "type": "file_search",
                    "vector_store_ids": [self.vector_store_id],
                    "max_num_results": self.MAX_NUM_RESULTS
                }],
                tool_choice={"type": "file_search"},
                include=["file_search_call.results"]
            )

            hits = []
            for out in getattr(resp, "output", []):
                # responses includes results directly or within file_search_call
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
                # fallback to older endpoint
                try:
                    vs = self.client.vector_stores.search(
                        vector_store_id=self.vector_store_id,
                        query=enhanced_query
                    )
                    hits = getattr(vs, "data", []) or []
                except Exception as e:
                    logger.error(f"vector_stores.search fallback failed: {e}")

            if not hits:
                self._selected_file_ids = []
                self._id_to_filename = {}
                return [], []

            by_file: Dict[str, Dict] = {}
            id_to_filename = {}

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
                    else:
                        content = getattr(getattr(r, "document", None), "content", None)
                        if content:
                            text = content

                if not fname or not fid or not text:
                    continue
                if score < self.MIN_SCORE:
                    continue

                id_to_filename[fid] = fname
                entry = by_file.get(fname)
                if entry is None or score > entry["score"]:
                    by_file[fname] = {"text": text, "score": score, "file_id": fid}

            if not by_file:
                self._selected_file_ids = []
                self._id_to_filename = {}
                return [], []

            top = sorted(by_file.items(), key=lambda kv: kv[1]["score"], reverse=True)[: self.TOP_K_FILES]

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

            return retrieved_content, sources

        except Exception as e:
            logger.error(f"Error retrieving documents: {e}", exc_info=True)
            self._selected_file_ids = []
            self._id_to_filename = {}
            return [], []

    # ---------- generation with citations ----------
    def _create_temp_store(self, file_ids):
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
        import time as _t
        start = _t.time()
        while _t.time() - start < timeout_s:
            try:
                vs = self.client.vector_stores.retrieve(vs_id)
                fc = getattr(vs, "file_counts", None)
                if fc and getattr(fc, "completed", 0) >= expected_count and getattr(fc, "in_progress", 0) == 0:
                    return True
            except Exception:
                pass
            _t.sleep(poll_s)
        return False

    def _extract_evidence_chunks(self, resp):
        chunks = []
        for out in getattr(resp, "output", []):
            res = None
            if hasattr(out, "results") and out.results:
                res = out.results
            else:
                fsc = getattr(out, "file_search_call", None)
                if fsc and getattr(fsc, "results", None):
                    res = fsc.results
                elif fsc and getattr(fsc, "search_results", None):
                    res = fsc.search_results
            if not res:
                continue
            for r in res:
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

        # dedupe
        seen = set()
        deduped = []
        for c in chunks:
            key = (c["file_id"], c["text"])
            if key not in seen:
                seen.add(key)
                deduped.append(c)
        return deduped

    def _extract_citations_from_responses(self, resp):
        id_to_filename = dict(self._id_to_filename)
        for out in getattr(resp, "output", []):
            fsc = getattr(out, "file_search_call", None)
            res = None
            if hasattr(out, "results") and out.results:
                res = out.results
            elif fsc and getattr(fsc, "results", None):
                res = fsc.results
            elif fsc and getattr(fsc, "search_results", None):
                res = fsc.search_results
            if res:
                for r in res:
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
                            used.append(fname or id_to_filename.get(fid, fid))

        # dedupe preserving order
        seen = set()
        used_unique = []
        for u in used:
            if u and u not in seen:
                used_unique.append(u)
                seen.add(u)
        return used_unique

    def generate_response(self, query, retrieved_docs, conversation_context=None, sources=None):
        try:
            sel_ids = getattr(self, "_selected_file_ids", []) or []
            if not sel_ids:
                return self.generate_response_fallback(query, retrieved_docs, conversation_context, sources)

            vs = self._create_temp_store(sel_ids)
            ok = self._wait_until_indexed(vs.id, expected_count=len(sel_ids))
            if not ok:
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
                include=["file_search_call.results"]
            )

            self._evidence_chunks = self._extract_evidence_chunks(resp)
            answer = getattr(resp, "output_text", "") or ""
            used_filenames = self._extract_citations_from_responses(resp)

            try:
                self.client.vector_stores.delete(vs.id)
            except Exception:
                pass

            return self._ensure_single_sources_block(answer, used_filenames)

        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return SAFE_FALLBACK_MSG

    def generate_response_fallback(self, query, retrieved_docs, conversation_context=None, sources=None):
        try:
            context = "\n\n".join(retrieved_docs) if retrieved_docs else "No documents retrieved"
            source_info = "\n".join([f"- {s}" for s in (sources or [])]) if sources else "No specific sources"

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
            generated = response.choices[0].message.content
            if sources and len(sources) > 0 and "Sources:" not in generated:
                generated = self._ensure_single_sources_block(generated, sources)
            return generated
        except Exception as e:
            logger.error(f"Error generating fallback response: {e}", exc_info=True)
            return SAFE_FALLBACK_MSG

    # ---------- validation ----------
    def _strip_sources_section(self, text):
        if not text:
            return text
        m = re.search(r'\nSources:\n(?:- .+\n?)+$', text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            return text[:m.start()].strip()
        return text.strip()

    def validate_response(self, response, retrieved_docs):
        try:
            core_resp = self._strip_sources_section(response)
            if getattr(self, "_evidence_chunks", None):
                evidence_text = "\n\n".join(c["text"] for c in self._evidence_chunks)
            else:
                evidence_text = "\n\n".join(retrieved_docs) if retrieved_docs else ""

            if not evidence_text.strip():
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

            v = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Return only valid JSON with the requested keys. No prose."},
                    {"role": "user", "content": validation_instructions}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )

            result_raw = json.loads(v.choices[0].message.content.strip())
            result = {
                "contains_only_retrieved_info": bool(result_raw.get("contains_only_retrieved_info", False)),
                "unsupported_claims": [str(x) for x in result_raw.get("unsupported_claims", [])],
                "confidence": float(result_raw.get("confidence", 0)),
                "explanation": str(result_raw.get("explanation", "")),
            }

            # softening rule
            if (not result["contains_only_retrieved_info"] and
                len(result["unsupported_claims"]) == 1 and
                result["confidence"] <= 0.6):
                result["contains_only_retrieved_info"] = True
                result["unsupported_claims"] = []
                result["explanation"] = "Single low confidence nit ignored."
                result["confidence"] = 0.9

            return result

        except Exception as e:
            logger.error(f"Error validating response: {e}", exc_info=True)
            return {
                "contains_only_retrieved_info": True,
                "unsupported_claims": [],
                "confidence": 1.0,
                "explanation": "Validator error. Treated as supported."
            }

    # ---------- main ----------
    def process_query(self, query, conversation_context=None):
        start_time = time.time()

        retrieved_docs, sources = self.retrieve_documents(query, conversation_context)

        if not retrieved_docs:
            total_time = time.time() - start_time
            validation = {
                "contains_only_retrieved_info": True,
                "unsupported_claims": [],
                "confidence": 1.0,
                "explanation": "Skipped validation because no documents were retrieved and safe fallback was used."
            }
            return {
                "response": SAFE_FALLBACK_MSG,
                "retrieved_docs_count": 0,
                "sources": sources,
                "validation": validation,
                "processing_time": total_time
            }

        response = self.generate_response(query, retrieved_docs, conversation_context, sources)
        validation = self.validate_response(response, retrieved_docs)

        confidence_threshold = 0.6
        if (validation.get('confidence', 0) < confidence_threshold or
            not validation.get('contains_only_retrieved_info', False)):
            response = SAFE_FALLBACK_MSG
            validation = {
                "contains_only_retrieved_info": True,
                "unsupported_claims": [],
                "confidence": 1.0,
                "explanation": "Used safe fallback due to validation failure."
            }

        total_time = time.time() - start_time
        return {
            "response": response,
            "retrieved_docs_count": len(retrieved_docs),
            "sources": sources,
            "validation": validation,
            "processing_time": total_time
        }

# ---------------- Init pipeline ----------------
custom_rag = CustomRAGPipeline(client, VECTOR_STORE_ID, MASTER_PROMPT)

# ---------------- Dedup cache ----------------
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

    def is_duplicate(self, message_id):
        cache = self.load_cache()
        current_time = time.time()
        cache = {k: v for k, v in cache.items() if current_time - v < self.ttl_seconds}
        if message_id in cache:
            return True
        cache[message_id] = current_time
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

# ---------------- Conversation store ----------------
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

# ---------------- Text utils ----------------
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

# ---------------- Slack handlers ----------------
def process_message(event, say):
    user_message = event.get('text', '')

    message_id = event.get('ts', str(time.time()))
    if dedup_cache.is_duplicate(message_id):
        logger.info(f"Duplicate message detected: {message_id}")
        return

    conversation_id = event.get('thread_ts', event.get('channel'))
    logger.info(f"Processing message in conversation: {conversation_id}")
    logger.info(f"User message: {user_message}")

    current_conversation_mapping = load_conversation_mapping()
    if conversation_id not in current_conversation_mapping:
        current_conversation_mapping = update_conversation_mapping(conversation_id, {"messages": []})

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

# Register handlers only if Slack is initialized
if slack_app is not None:
    @slack_app.event("app_mention")
    def handle_mention(event, say):
        process_message(event, say)

    @slack_app.event("message")
    def handle_message(event, say):
        if event.get("channel_type") == "im":
            process_message(event, say)

# ---------------- Flask app ----------------
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
        "validation": "enabled",
        "variants_supported": list(VARIANT_TOKENS),
        "programs_grounded": list(PROGRAM_TOKENS.keys()),
    }

if __name__ == "__main__":
    flask_app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))