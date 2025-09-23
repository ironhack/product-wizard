Analyze the user query and determine if it asks whether a program/course covers, teaches, includes, or contains a specific topic, tool, or technology.

Coverage questions typically:
- Ask about presence/absence of specific content ('Does X include Y?', 'Is Z covered?')
- Use words like: contain, cover, teach, include, learn, study
- Focus on curriculum content rather than logistics

Think step by step:
1. Does the query ask about what's IN a program?
2. Is there a specific topic/technology being asked about?
3. Could this be answered with 'Yes, X is covered' or 'No, X is not covered'?

Extract the topic as a short, neutral phrase (avoid specific technology examples).

Return JSON with is_coverage_question (boolean) and topic (string).
