Analyze the user query and determine if it asks about cohort/calendar information from the RMT Bootcamps Tracker (who teaches a cohort, whether a cohort exists, cohort start/end dates, who is the PM for a cohort).

Cohort/calendar questions typically:
- Ask who is teaching a specific cohort (e.g. "Who is teaching the May AI PT course?", "Who teaches the June ML FT?")
- Ask whether a specific cohort exists or starts in a given month (e.g. "Do we have a DV FT course starting in November?", "Is there an AI PT in March?")
- Ask about start dates, end dates, or upcoming intakes (e.g. "When is the next start date for AI Engineering part time?", "When are the next upcoming intakes for the PM bootcamp after April?", "What is the end date of the Data Analytics PT that begins on May 5th?")
- Ask who is the PM (Program Manager) for a specific cohort (e.g. "Who is the PM for the June ML FT course?")

They refer to concrete cohorts by track (WD, DA, UX, ML, AI, DV, CY, MK, etc.), type (FT/PT), language (EN/ES), and month or start time—not about curriculum content or program structure in general.

IMPORTANT: Start-date and intake-date questions are cohort/calendar questions. The tracker sheet is the live source of truth for dates; curriculum documents are not.

Think step by step:
1. Does the query ask about a specific cohort (by track, type, month) or its schedule?
2. Is it asking about staff (teacher, PM), existence, or dates (start/end/next intake) of cohorts?
3. Would the answer come from a calendar/tracker sheet (cohorts, start dates, teachers, PMs) rather than from course syllabi or program docs?

Return JSON with is_cohort_calendar_question (boolean) and optionally reason (string, brief explanation).
