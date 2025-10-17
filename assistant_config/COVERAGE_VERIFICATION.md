Given the retrieved curriculum excerpts, determine if the queried topic(s) are explicitly listed/mentioned.
Do not infer or assume. Answer strictly based on the text. Return JSON.

INPUTS
- QUERY: {query}
- PROGRAMS: {programs}
- EXCERPTS:
{evidence_text}

DECISION RULES (STRICT, NO KNOWLEDGE BIAS)
1) Explicit-only criterion:
   - Mark a topic as present ONLY if it is explicitly mentioned in the excerpts.
   - Prefer short direct quotes as evidence.

2) Acronyms policy (allow to reduce false negatives):
   - Treat unambiguous acronym ↔ full-term pairs as explicit equivalence.
     Examples (pattern-based, not exhaustive):
       - "MLOps" ≡ "Machine Learning Operations"/"Machine Learning Operationalization"
       - "NLP" ≡ "Natural Language Processing"
       - "CI/CD" ≡ "Continuous Integration and Continuous Delivery/Deployment"
   - If ambiguous, default to not present.

3) Handling broad queries like "what do you learn" (especially for Web Development):
   - If the query is broad/general (e.g., "what do you learn in Web Development?"), DO NOT try to verify a single synthetic topic.
   - Instead, check whether MULTIPLE explicit curriculum topics appear across excerpts.
   - For Web Development, if any two or more of the following are explicitly mentioned across excerpts, set is_present=true and return a concise evidence summary with quotes:
     { "JavaScript", "React", "Node.js", "Express", "MongoDB", "HTML", "CSS", "REST APIs", "Git" }
   - If fewer than two of these are explicitly present, return is_present=false.
   - Never infer topics; require exact matches in text.

4) Coverage-like interpretation for general queries:
   - Treat a general "what do you learn" query as coverage-like ONLY if explicit topic matching (Rule 3) fails to find 2+ explicit topics.
   - If 2+ explicit topics are present, prefer a positive result with those topics as evidence.

5) Program boundary:
   - Consider only excerpts that clearly match the detected program(s). Ignore mismatched programs.

OUTPUT FORMAT (JSON)
{
  "is_present": true|false,
  "topic": "single explicit topic if the query asks about one; else 'multiple_topics' for broad queries",
  "evidence": [
    { "quote": "short exact quote", "source": "filename_or_id" },
    { "quote": "short exact quote", "source": "filename_or_id" }
  ],
  "matched_topics": ["JavaScript", "React", ...]  // include when query is broad
}

NOTES
- Keep evidence concise (1–2 short quotes). Use multiple quotes if needed to show 2+ topics.
- Do not paraphrase as evidence; use verbatim phrases for quotes.
