Analyze the user query and determine if it asks whether a program/course covers, teaches, includes, or contains a specific topic, tool, or technology.

Coverage questions typically:
- Ask about presence/absence of specific content ('Does X include Y?', 'Is Z covered?')
- Use words like: contain, cover, teach, include, learn, study
- Focus on curriculum content rather than logistics

NOT coverage questions (is_coverage_question must be false):
- Requests for a curriculum overview, breakdown, or outline ("give me a week-by-week overview", "detailed unit breakdown", "what will be covered in X?", "module by module breakdown", "curriculum overview")
- Broad "what do you learn / what topics are covered" questions with no single specific topic
- Questions about schedule, dates, duration, requirements, certifications, or projects
- Comparison questions between programs
- Questions spanning multiple/all programs ("which courses include Y?")

The test: a coverage question names ONE specific topic/tool/technology and can be answered "Yes, X is covered" or "No, X is not covered". If the user is asking to SEE the curriculum (structure, breakdown, list of topics), it is NOT a coverage question.

Think step by step:
1. Does the query ask about what's IN a program?
2. Is there a specific topic/technology being asked about?
3. Could this be answered with 'Yes, X is covered' or 'No, X is not covered'?
4. Is the user actually asking for an overview/breakdown/structure instead? If so, answer false.

Extract the topic as a short, neutral phrase (avoid specific technology examples).

Return JSON with is_coverage_question (boolean) and topic (string).
