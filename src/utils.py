"""
Utility functions for RAG service.
Includes markdown conversion, OpenAI API calls, and conversation formatting.
"""

import json
import logging
import os
import re
from typing import Dict, List, Any, Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from src.config import openai_client

# Configure logging
logger = logging.getLogger(__name__)


def convert_markdown_to_slack(text: str) -> str:
    """
    Convert markdown formatting to Slack-friendly formatting.
    - Headers (##, ###) -> Bold with newlines
    - **bold** -> *bold* (Slack uses single asterisk)
    - Markdown lists -> Slack-friendly lists with bullets
    - Code blocks -> Preserved with backticks
    - Links -> Slack link format
    """
    # Protect code blocks from being modified
    code_blocks = []
    def protect_code(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(code_blocks)-1}__"

    # Protect inline code
    inline_code = []
    def protect_inline_code(match):
        inline_code.append(match.group(0))
        return f"__INLINE_CODE_{len(inline_code)-1}__"

    # Protect code blocks (```code```)
    text = re.sub(r'```[\s\S]*?```', protect_code, text)

    # Protect inline code (`code`)
    text = re.sub(r'`([^`]+)`', protect_inline_code, text)

    # Remove markdown headers and convert to bold
    # Handle both ## and ### headers
    text = re.sub(r'^##+\s+(.+)$', r'*\1*', text, flags=re.MULTILINE)

    # Convert markdown bold (**text**) to Slack bold (*text*)
    # But be careful not to convert single asterisks that are already Slack formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'*\1*', text)

    # Convert markdown links [text](url) to Slack format <url|text>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<\2|\1>', text)

    # Convert markdown lists (- or *) to Slack bullets (•)
    # Handle both - and * list markers, but avoid converting asterisks in bold text
    text = re.sub(r'^[\s]*[-]\s+', '• ', text, flags=re.MULTILINE)
    # For asterisk lists, be more careful - only convert if it's at start of line with spaces
    text = re.sub(r'^[\s]+\*\s+', '• ', text, flags=re.MULTILINE)

    # Convert numbered lists (1. 2. etc.) to Slack format (1. 2. etc. - keep as is)
    # Slack supports numbered lists, so we can keep them

    # Remove excessive blank lines (more than 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Restore inline code
    for i, code in enumerate(inline_code):
        text = text.replace(f"__INLINE_CODE_{i}__", code)

    # Restore code blocks
    for i, code in enumerate(code_blocks):
        text = text.replace(f"__CODE_BLOCK_{i}__", code)

    # Clean up any remaining markdown artifacts
    text = text.strip()

    return text


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


def _sampling_kwargs(model: str, temperature: float) -> Dict:
    """
    Sampling params compatible with the given model. Newer reasoning families
    (gpt-5*, o*) only accept the default temperature and reject the param.
    """
    if re.match(r"^(gpt-5|o\d)", model or ""):
        return {}
    return {"temperature": temperature}


def call_openai_json(
    system_prompt: str,
    user_prompt: str,
    model: str = None,
    timeout: int = 30,
    schema: Dict = None,
    schema_name: str = "response",
) -> Dict:
    """Call OpenAI API and parse JSON response.

    Args:
        system_prompt: System prompt for the API call
        user_prompt: User prompt for the API call
        model: Model to use (default: MODEL_FAST from config)
        timeout: Request timeout in seconds
        schema: Optional JSON Schema; when given, uses strict structured outputs
                so the shape is enforced by the API instead of hoped for
        schema_name: Name for the structured output schema
    """
    from src.config import MODEL_FAST
    model = model or MODEL_FAST
    if schema:
        response_format = {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "strict": True, "schema": schema},
        }
    else:
        response_format = {"type": "json_object"}
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=response_format,
            timeout=timeout,
            **_sampling_kwargs(model, 0.1),
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"OpenAI JSON call failed: {e}")
        return {}


def call_openai_text(system_prompt: str, user_prompt: str, model: str = None, timeout: int = 60) -> str:
    """Call OpenAI API and get text response.

    Args:
        system_prompt: System prompt for the API call
        user_prompt: User prompt for the API call
        model: Model to use (default: MODEL_QUALITY from config)
        timeout: Request timeout in seconds
    """
    from src.config import MODEL_QUALITY
    model = model or MODEL_QUALITY
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            timeout=timeout,
            **_sampling_kwargs(model, 0.3),
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI text call failed: {e}")
        return ""


def normalize_source_citation(source: str) -> str:
    """Stable syllabus filename for user-facing citations (e.g. chunk source -> Syllabus.md)."""
    if not source or source == "unknown":
        return source or "unknown"
    s = source.strip().replace("\\", "/").split("/")[-1]
    lower = s.lower()
    if lower.endswith(".txt"):
        s = s[:-4] + ".md"
    elif not lower.endswith(".md") and "." not in s:
        s = s + ".md"
    return s


def strip_doc_version(filename: str) -> str:
    """
    Normalize a syllabus filename to its versionless base for matching.
    'Data_Science_&_Machine_Learning_bootcamp_2026_02.md' -> 'data_science_&_machine_learning_bootcamp'
    Keeps document-filter matching working when a syllabus is re-uploaded with a new date suffix.
    """
    if not filename:
        return ""
    s = filename.strip().replace("\\", "/").split("/")[-1].lower()
    s = re.sub(r"\.(txt|md)$", "", s)
    s = re.sub(r"_20\d{2}_\d{2}$", "", s)
    return s


def program_syllabus_needles(program_ids: List[str], program_synonyms: Dict) -> List[str]:
    """Versionless syllabus filename bases for the given programs (for source matching)."""
    needles = []
    for pid in program_ids:
        info = program_synonyms.get(pid) or {}
        for fn in info.get("filenames", []):
            base = strip_doc_version(fn)
            if base and base not in needles:
                needles.append(base)
    return needles


def program_display_name(prog_id: Optional[str], program_synonyms: Dict) -> str:
    """Human-readable program name for user-facing messages (never a raw code like 'ml')."""
    if not prog_id:
        return "this program"
    info = program_synonyms.get(prog_id) or {}
    if info.get("display_name"):
        return info["display_name"]
    # Fall back to the longest alias (short ones are codes like 'de'), else the id
    aliases = [a for a in info.get("aliases", []) if len(a) > 3]
    if aliases:
        return max(aliases, key=len).title()
    return prog_id.replace("_", " ").title()


_MONTH_DISPLAY = {
    "01": "January", "02": "February", "03": "March", "04": "April",
    "05": "May", "06": "June", "07": "July", "08": "August",
    "09": "September", "10": "October", "11": "November", "12": "December",
}

_UNIVERSAL_DOC_DISPLAY = {
    "certifications": "Certifications guide",
    "computer_specs_min_requirements": "Computer requirements",
    "course_design_overview": "Course design overview",
    "ironhack_portfolio_overview": "Ironhack portfolio overview",
    "mein_now_title_equivalence": "MeinNOW course title mapping",
}


def humanize_source_citation(source: str, program_synonyms: Dict) -> str:
    """
    User-friendly name for a source file, for people who don't care about .md files:
    'Cloud_Engineering_bootcamp_2025_12.md' -> 'Cloud Engineering bootcamp syllabus (December 2025)'
    'Certifications_2025_07.md'             -> 'Certifications guide (July 2025)'
    Unknown names degrade gracefully to de-underscored text.
    """
    if not source:
        return source or ""
    s = source.strip().replace("\\", "/").split("/")[-1]
    s = re.sub(r"\.(txt|md)$", "", s, flags=re.IGNORECASE)

    date_suffix = ""
    m = re.search(r"_(20\d{2})_(\d{2})$", s)
    if m:
        month = _MONTH_DISPLAY.get(m.group(2), "")
        date_suffix = f" ({month} {m.group(1)})" if month else f" ({m.group(1)})"
    base = re.sub(r"_20\d{2}_\d{2}$", "", s)
    base_lower = base.lower()

    pid = program_for_source(source, program_synonyms)
    if pid:
        name = program_display_name(pid, program_synonyms)
        label = f"{name} bootcamp syllabus" if "bootcamp" in base_lower and "bootcamp" not in name.lower() else f"{name} syllabus"
        return label + date_suffix

    for needle, display in _UNIVERSAL_DOC_DISPLAY.items():
        if needle in base_lower:
            return display + date_suffix

    return base.replace("_", " ").strip() + date_suffix


def program_for_source(source: str, program_synonyms: Dict) -> Optional[str]:
    """Map a chunk source filename to its program id, version-tolerant. None if no match."""
    src_base = strip_doc_version(source or "")
    if not src_base:
        return None
    for pid, info in (program_synonyms or {}).items():
        for fn in (info or {}).get("filenames", []):
            base = strip_doc_version(fn)
            if base and base in src_base:
                return pid
    return None


_BREAKDOWN_PATTERNS = re.compile(
    r"week[\s-]*by[\s-]*week|module[\s-]*by[\s-]*module|unit[\s-]*by[\s-]*unit|day[\s-]*by[\s-]*day"
    r"|weekly (detail|overview|breakdown|schedule)"
    r"|(detailed|full|complete|comprehensive) (unit |module |week |curriculum |course )?(breakdown|overview|outline|structure)"
    r"|curriculum (overview|breakdown|outline|structure)"
    r"|(overview|breakdown|outline) of (the )?(topics|curriculum|units|modules|weeks|what)"
    r"|what (will|is going to) be covered",
    re.IGNORECASE,
)


def is_breakdown_request(text: str) -> bool:
    """True if the user asks for a curriculum overview/breakdown rather than a yes/no coverage check."""
    return bool(text and _BREAKDOWN_PATTERNS.search(text))


_PORTFOLIO_WIDE_PATTERNS = re.compile(
    r"which (of (our|the) )?(courses?|programs?|bootcamps?|verticals?)"
    r"|what (courses?|programs?|bootcamps?|verticals?) (has|have|include|includes|cover|covers|teach|teaches|contain|contains|use|uses)"
    r"|(any|all) (of (our|the) )?(courses?|programs?|bootcamps?) (that|with|covering|teaching|including)"
    r"|across (all )?(our )?(courses?|programs?|bootcamps?)"
    r"|in (any|which) (course|program|bootcamp)",
    re.IGNORECASE,
)


def is_portfolio_wide_query(text: str) -> bool:
    """True if the question spans the whole portfolio ('which courses have Linux?') instead of one program."""
    return bool(text and _PORTFOLIO_WIDE_PATTERNS.search(text))


def is_valid_coverage_topic(topic: str) -> bool:
    """True if a coverage-verification topic is a real topic we can honestly say 'not mentioned' about."""
    if not topic or not topic.strip():
        return False
    t = topic.strip().lower()
    if len(topic) > 100:
        return False
    invalid_indicators = (
        "the requested topic",
        "multiple_topics",
        "multiple topics",
        "single explicit topic",
        "if the query asks",
        "broad queries",
        "else",
    )
    return not any(ind in t for ind in invalid_indicators)


def load_full_syllabus_docs(program_ids: List[str], program_synonyms: Dict) -> List[Dict[str, Any]]:
    """
    Load complete syllabus documents for the given programs from the local knowledge base.
    Used for breakdown/overview questions where top-k chunk retrieval only surfaces
    fragments of the curriculum. Returns docs in the same shape as retrieved chunks,
    flagged with full_syllabus=True so filtering nodes keep them intact.
    """
    kb_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "knowledge_base",
        "database",
    )
    docs = []
    try:
        available = sorted(os.listdir(kb_dir))
    except OSError as e:
        logger.warning(f"Knowledge base directory unavailable for full-syllabus load: {e}")
        return docs

    for pid in program_ids:
        needles = program_syllabus_needles([pid], program_synonyms)
        # Latest version wins when several files share the same versionless base
        matches = [f for f in available if any(n in strip_doc_version(f) for n in needles)]
        if not matches:
            logger.warning(f"No local syllabus file found for program '{pid}'")
            continue
        filename = sorted(matches)[-1]
        try:
            with open(os.path.join(kb_dir, filename), "r", encoding="utf-8") as f:
                content = f.read().strip()
        except OSError as e:
            logger.warning(f"Could not read syllabus file {filename}: {e}")
            continue
        if content:
            docs.append({
                "content": content,
                "source": filename,
                "quote": content[:200],
                "score": 1.0,
                "full_syllabus": True,
            })
            logger.info(f"Loaded full syllabus for '{pid}': {filename} ({len(content)} chars)")
    return docs


_TOPIC_INDEX_STOPWORDS = {
    "which", "what", "who", "where", "when", "how", "does", "did", "are", "is", "was",
    "course", "courses", "program", "programs", "bootcamp", "bootcamps", "vertical", "verticals",
    "have", "has", "had", "include", "includes", "included", "including",
    "teach", "teaches", "taught", "teaching", "cover", "covers", "covered", "covering",
    "contain", "contains", "use", "uses", "used", "using", "with", "the", "and", "for",
    "any", "all", "our", "your", "them", "they", "that", "this", "these", "those",
    "tools", "tool", "such", "like", "there", "topics", "topic", "learn", "students",
    "ironhack", "part", "full", "time",
}


def local_topic_index(query: str, program_synonyms: Dict) -> List[Dict[str, Any]]:
    """
    Literal, deterministic index of which program syllabi mention the meaningful
    terms of a portfolio-wide query ("which course have linux in?").
    Scans the local knowledge base files and returns one entry per (term, program)
    match with a verbatim evidence line. Ground truth for "which programs mention X".
    """
    terms = [
        t for t in re.findall(r"[a-zA-Z][a-zA-Z+#./-]{2,}", (query or "").lower())
        if t not in _TOPIC_INDEX_STOPWORDS
    ]
    terms = list(dict.fromkeys(terms))  # dedupe, keep order
    if not terms:
        return []

    entries = []
    programs_per_term = {}
    for pid in program_synonyms:
        docs = load_full_syllabus_docs([pid], program_synonyms)
        if not docs:
            continue
        content = docs[0]["content"]
        content_lower = content.lower()
        lines = content.splitlines()
        for term in terms:
            if term not in content_lower:
                continue
            programs_per_term[term] = programs_per_term.get(term, 0) + 1
            evidence = next(
                (ln.strip() for ln in lines if term in ln.lower() and len(ln.strip()) > len(term)),
                "",
            )
            entries.append({
                "term": term,
                "program_id": pid,
                "program_name": program_display_name(pid, program_synonyms),
                "source": docs[0]["source"],
                "evidence": evidence[:200],
            })

    # Drop non-discriminative terms: a word found in more than half the programs
    # (e.g. "certification", "project") identifies nothing and bloats the index
    # into a doc citing every syllabus
    max_programs = max(1, len(program_synonyms) // 2)
    entries = [e for e in entries if programs_per_term.get(e["term"], 0) <= max_programs]
    return entries


def docs_for_program_syllabi(
    filtered_docs: List[Dict[str, Any]], program_ids: List[str], program_synonyms: Dict
) -> List[Dict[str, Any]]:
    """
    Chunks whose source belongs to the given programs' syllabus files only.
    Used so coverage verification searches the same curriculum the user asked about.
    Version-tolerant: matches on the versionless filename base, so a re-uploaded
    syllabus with a new date suffix still matches its program.
    """
    if not program_ids:
        return list(filtered_docs)
    needles = program_syllabus_needles(program_ids, program_synonyms)
    out = []
    for doc in filtered_docs:
        src = strip_doc_version(doc.get("source") or "")
        if any(n in src for n in needles):
            out.append(doc)
    return out


def unique_citations_from_docs(docs: List[Dict[str, Any]]) -> List[str]:
    """Ordered unique normalized citation filenames for docs we actually read."""
    seen = set()
    out = []
    for doc in docs:
        raw = doc.get("source") or ""
        c = normalize_source_citation(raw)
        if c and c != "unknown" and c not in seen:
            seen.add(c)
            out.append(c)
    return out
