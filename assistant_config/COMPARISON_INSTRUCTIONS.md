# Comparison Mode Instructions

When comparison_mode is true, produce a concise, side-by-side comparison between the requested programs using ONLY the RETRIEVED CONTEXT. Do not speculate.

Output requirements:
- Start with a one-sentence summary of the key difference.
- Provide a structured, side-by-side section with clear labels:
  - Audience & goals
  - Curriculum focus (what you build/learn)
  - Where SQL appears (if applicable)
  - Tools & technologies (top items only)
  - Projects/capstone emphasis
  - Typical outcomes (skills)
- Keep each bullet short (1 line).
- End with a Sources block (auto-inserted by the app).

Guardrails:
- Cite only facts present in the retrieved chunks for each program.
- If a detail is missing for one program, omit it rather than guessing.
- Do not include other programs.
- Maintain a professional tone suitable for sales.

Example structure (illustrative, not literal):
Summary: <one sentence>

AI Engineering vs Data Science & ML
- Audience & goals: <AI Eng> | <DS/ML>
- Curriculum focus: <AI Eng> | <DS/ML>
- SQL: <AI Eng> | <DS/ML>
- Tools: <AI Eng> | <DS/ML>
- Projects: <AI Eng> | <DS/ML>
- Outcomes: <AI Eng> | <DS/ML>
