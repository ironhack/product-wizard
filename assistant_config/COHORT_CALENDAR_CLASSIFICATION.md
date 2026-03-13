Analyze the user query and determine if it asks about cohort/calendar information from the RMT Bootcamps Tracker (who teaches a cohort, whether a cohort exists, who is the PM for a cohort).

Cohort/calendar questions typically:
- Ask who is teaching a specific cohort (e.g. "Who is teaching the May AI PT course?", "Who teaches the June ML FT?")
- Ask whether a specific cohort exists or starts in a given month (e.g. "Do we have a DV FT course starting in November?", "Is there an AI PT in March?")
- Ask who is the PM (Program Manager) for a specific cohort (e.g. "Who is the PM for the June ML FT course?")

They refer to concrete cohorts by track (WD, DA, UX, ML, AI, DV, CY, MK, etc.), type (FT/PT), language (EN/ES), and month or start time—not about curriculum content or program structure in general.

Think step by step:
1. Does the query ask about a specific cohort (by track, type, month)?
2. Is it asking about staff (teacher, PM) or existence/schedule of that cohort?
3. Would the answer come from a calendar/tracker sheet (cohorts, start dates, teachers, PMs) rather than from course syllabi or program docs?

Return JSON with is_cohort_calendar_question (boolean) and optionally reason (string, brief explanation).
