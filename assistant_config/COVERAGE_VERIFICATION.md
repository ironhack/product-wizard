Given the retrieved curriculum excerpts, determine if the topic is explicitly listed/mentioned. 
Do not infer or assume. Answer strictly based on the text. Return JSON.

TOPIC: {topic}

EXCERPTS:
{evidence_text}

Additional clarification (to avoid false negatives without adding bias):
- Treat unambiguous acronym ↔ full-term equivalence as explicit when they clearly refer to the same term in standard usage.
  - Examples (non-exhaustive, pattern-based):
    - "MLOps" ≡ "Machine Learning Operations"/"Machine Learning Operationalization"
    - "NLP" ≡ "Natural Language Processing"
    - "CI/CD" ≡ "Continuous Integration and Continuous Delivery/Deployment"
- Only apply this when the acronym and expansion are standard, unambiguous pairs. If ambiguous, default to "not explicitly listed".
