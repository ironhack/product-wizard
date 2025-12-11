Given the retrieved curriculum excerpts, determine if the queried topic(s) are explicitly listed/mentioned.
Do not infer or assume. Answer strictly based on the text. Return JSON.

INPUTS
- QUERY: {query}
- PROGRAMS: {programs}
- EXCERPTS:
{evidence_text}

DECISION RULES (STRICT, NO KNOWLEDGE BIAS)
1) Explicit-only criterion:
   - Mark a topic as present ONLY if it is explicitly mentioned in the retrieved excerpts.
   - Prefer short direct quotes as evidence.
   - Search the excerpts carefully for exact matches or clear mentions.
   - DO NOT infer or assume topics based on related concepts or synonyms unless explicitly stated.

2) Acronyms policy (allow to reduce false negatives):
   - Treat unambiguous acronym ↔ full-term pairs as explicit equivalence when both forms appear in the excerpts.
   - Only accept equivalence if the relationship is clear from the retrieved text context.
   - If ambiguous or not clearly established in excerpts, default to not present.

3) Handling broad queries like "what do you learn":
   - If the query is broad/general (e.g., "what do you learn in [Program]?"), DO NOT try to verify a single synthetic topic.
   - Instead, search the retrieved excerpts for MULTIPLE explicit curriculum topics, technologies, or concepts.
   - Identify topics that are explicitly mentioned in the excerpts - do not assume what topics should be present.
   - If two or more distinct topics/technologies/concepts are explicitly mentioned across excerpts, set is_present=true and return evidence with quotes.
   - If fewer than two explicit topics are found in the retrieved excerpts, return is_present=false.
   - Never infer topics; require exact matches or clear mentions in the retrieved text.

4) Coverage-like interpretation for general queries:
   - Treat a general "what do you learn" query as coverage-like ONLY if explicit topic matching (Rule 3) fails to find 2+ explicit topics in retrieved excerpts.
   - If 2+ explicit topics are present in retrieved excerpts, prefer a positive result with those topics as evidence.
   - Base all decisions on what is actually retrieved, not on assumptions about what programs typically contain.

5) Program boundary:
   - Consider only excerpts that clearly match the detected program(s) from the retrieved documents.
   - Ignore excerpts from mismatched programs.
   - Verify program matches by checking document sources and content alignment.

OUTPUT FORMAT (JSON)
{
  "is_present": true|false,
  "topic": "EXTRACT THE ACTUAL TOPIC NAME FROM THE QUERY - e.g., if query is 'Does X teach Python?', topic should be 'Python'. If query is 'Does Y include React?', topic should be 'React'. For broad queries asking 'what do you learn', use 'multiple_topics'.",
  "evidence": [
    { "quote": "short exact quote", "source": "filename_or_id" },
    { "quote": "short exact quote", "source": "filename_or_id" }
  ],
  "matched_topics": ["topic1", "topic2", ...]  // include when query is broad - list only topics explicitly found in retrieved excerpts
}

IMPORTANT: When verifying coverage for a topic found in a unit or section:
- Include evidence quotes for BOTH the unit/section title AND specific subtopics covered in that unit/section
- If the retrieved excerpts contain a unit title (e.g., "Unit 1: Introduction to X") AND a list of subtopics/key topics for that unit, include multiple evidence quotes showing both
- This provides comprehensive evidence that enables detailed answers about what is covered

CRITICAL: The "topic" field MUST contain the actual topic name extracted from the query, NOT the instruction text.
Examples:
- Query: "Does Data Analytics teach Python?" → topic: "Python"
- Query: "Does Web Development include React?" → topic: "React"
- Query: "Does Data Science cover machine learning?" → topic: "machine learning"
- Query: "What do you learn in Web Development?" → topic: "multiple_topics"

NOTES
- Keep evidence concise (1–2 short quotes). Use multiple quotes if needed to show 2+ topics.
- Do not paraphrase as evidence; use verbatim phrases for quotes.
- All topics in "matched_topics" must be explicitly found in the retrieved excerpts - never assume or infer.
- CRITICAL: The "topic" field must be the actual topic name from the query, NOT the instruction text. Extract the specific topic being asked about.
- IMPORTANT: When a topic is found in a unit or section, include evidence quotes that show both the unit/section title AND specific subtopics covered in that unit/section if they are mentioned in the retrieved excerpts. This provides comprehensive evidence for generation.
