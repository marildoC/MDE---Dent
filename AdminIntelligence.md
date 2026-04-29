The correct Stage A identity is:

Admin Intelligence = admin-only, chat-style, read-only query interface over DentCare-MDE’s existing structured data.

No OpenAI API yet.
No LLM yet.
No raw SQL.
No clinical decision-making.
No record modification.

It should feel intelligent, but internally it should be safe, deterministic, and controlled.

1. What we want to build in Stage A

We replace the raw Audit Logs page with a new page:

Admin Intelligence

At the top:

“Welcome, admin1”
short explanation:
“Ask about patients, follow-up cases, reports, escalations, appointments, workflows, and audit history.”

Then a chat-like interface:

admin types a question
system detects the intended query
backend executes a safe predefined data query
answer appears as a chat response
answer may include:
direct text
table
compact cards
evidence references
suggested follow-up questions

Example:

Admin asks:

How many appointments are scheduled today?

System answers:

There are 3 appointments scheduled today.

Then table:

Time	Patient	Case	Priority	Status
10:30	patient1	Case #4	HIGH	SCHEDULED
15:00	marildo	Case #7	URGENT	SCHEDULED

This is useful and not duplicated from Follow-Up Cases because it gives a system-level answer.

2. Key design principle

The page should not show all data by default.

It should answer questions.

That means the page is not:

a second Follow-Up Cases page
a second Audit Logs list
a full analytics dashboard
a patient medical record page

It is:

a question-answer interface over existing system state.

So the admin asks what they need, and the system retrieves the relevant answer.

3. Best UI design
Page structure
Top section
Page title: Admin Intelligence
Greeting: Welcome, admin1
Subtitle: “Ask operational questions about workflows, patients, reports, escalations, appointments, and audit traces.”
Query box

Large GPT-style input:

placeholder:
“Ask about patients, cases, appointments, escalations, workflows, or audit history…”

Example:

How many follow-up cases does marildo have?
Suggested question chips

Under the input, show smart suggestions.

Default suggestions:

“How many appointments are scheduled today?”
“Show unresolved urgent escalations”
“How many follow-up cases does patient1 have?”
“Show latest follow-up case for marildo”
“Show active workflows”
“Show audit trace for case 4”
Chat history

Question and answer should stay visible during the session.

Important behavior:

if admin asks question 1, then question 2, previous answers remain
refresh should ideally keep the current chat history
logout should clear the local admin intelligence session

Best Stage A approach:

store chat history in localStorage
key it by admin user id
clear it on logout

No need for database-stored chat history yet.

4. Smart suggestion behavior

This is important because it makes the page feel intelligent before using real AI.

When admin starts typing, suggestions should adapt.

Example:

Admin types:

appointement

Even with typo, system should recognize likely meaning: appointment.

Suggestions should become:

“How many appointments are scheduled today?”
“Show today’s appointments”
“Show appointments for patient1”
“Show appointment-required cases without scheduled appointment”
“Show cancelled appointments”

Admin types:

marildo

Suggestions should become:

“How many follow-up cases does marildo have?”
“Show latest follow-up case for marildo”
“Show appointments for marildo”
“Show unresolved escalations for marildo”
“Show audit trace for marildo’s latest case”

Admin types:

urgent

Suggestions:

“Show unresolved urgent escalations”
“How many urgent cases are still open?”
“Show urgent appointments”
“Show urgent cases without scheduled appointment”

This can be implemented without LLM by using:

simple keyword matching
synonym lists
typo normalization
patient-name matching from backend data
5. Backend architecture

Create a new backend app:

backend/admin_intelligence/

Files:

admin_intelligence/
  urls.py
  views.py
  serializers.py
  services.py
  query_router.py
  query_handlers.py
  suggestions.py
  tests.py

Main endpoints:

POST /api/admin-intelligence/query/
GET  /api/admin-intelligence/suggestions/?q=<text>

Only admin users should access this.

Patients must not access it.
Dentists can be excluded for Stage A unless you later want a staff-intelligence version.

6. Query pipeline

Correct flow:

admin question
→ normalize text
→ detect supported intent
→ extract parameters
→ execute safe Django ORM query
→ return structured result
→ frontend renders answer

Example:

Question:

How many follow-up cases does marildo have?

Router detects:

{
  "intent": "count_follow_up_cases_for_patient",
  "parameters": {
    "patient_name": "marildo"
  }
}

Backend handler executes:

PatientProfile + FollowUpCase query

Response:

{
  "answer": "Marildo has 2 follow-up cases.",
  "intent": "count_follow_up_cases_for_patient",
  "display_type": "summary",
  "data": {
    "patient": "marildo",
    "count": 2
  },
  "evidence": [
    {"type": "PatientProfile", "id": 3}
  ]
}

The AI-like behavior comes from smart routing and clear answer formatting, not from unsafe free reasoning.

7. Supported V1 question types

Stage A should support a strong but controlled set.

Patient / follow-up case questions

Support:

“How many follow-up cases does [patient] have?”
“Show latest follow-up case for [patient].”
“Which cases are active for [patient]?”
“What is the status of [patient]’s latest case?”
“Show reports for [patient]’s latest case.”

Returned data should include:

patient username/name
case id
workflow name
treatment date
case status
number of reports
latest risk if available
Appointment questions

Support:

“How many appointments are scheduled today?”
“Show today’s appointments.”
“Show appointments for [patient].”
“Show appointment-required cases without scheduled appointment.”
“Show cancelled appointments.”
“Show completed appointments today.”

Returned table should include:

scheduled time
patient
follow-up case id
priority
appointment status
workflow/treatment if available

This is very useful.

Escalation questions

Support:

“Show unresolved escalations.”
“Show urgent unresolved escalations.”
“Show escalations for [patient].”
“Which escalations are waiting for patient?”
“Which staff/admin last responded to [patient]?”

Returned data should include:

patient
urgency
escalation status
risk level
latest staff response status
last updated time
actor if audit can determine it

Important: if actor is not directly stored in escalation model, use audit logs to infer latest update actor. If not available, answer honestly:

The latest staff response exists, but the responding actor is not stored directly. No matching audit update was found.

That is robust.

Workflow questions

Support:

“Which workflows are active?”
“How many active workflows exist?”
“Show workflows by status.”
“Which workflow has most escalations?”
“Show Post-Extraction workflow status.”

Returned data:

workflow name
treatment type
status
number of cases
number of reports/escalations if easy
Risk / report questions

Support:

“How many high-risk reports today?”
“How many urgent reports this week?”
“Show latest high-risk reports.”
“Which reports produced escalation?”
“Show low-risk reports today.”

Returned data:

report id
patient
case id
risk level
action
appointment priority
created time

Do not show full clinical notes by default.

Audit/history questions

Support:

“Show audit trace for case [id].”
“Who activated workflow [id]?”
“What actions did admin1 perform today?”
“Show recent audit events.”
“Show appointment updates today.”

Returned data:

timestamp
actor
action
target
compact details

This replaces the old raw audit page with a query-based audit view.

8. Response display types

The backend should return a display_type.

Examples:

summary
table
cards
timeline
unsupported

Frontend renders accordingly.

Summary response

For simple answers.

Example:

Marildo has 2 follow-up cases.

Table response

For appointments, reports, escalations.

Example:

Time	Patient	Priority	Status
Cards response

For follow-up cases.

Example:

Case #4
Workflow: Post-Extraction
Status: ACTIVE
Treatment date: 2026-04-24
Timeline response

For audit trace.

Example:

10:20 — Symptom Report Submitted
10:20 — Risk Assessment Created
10:20 — Advice Created
10:21 — Escalation Created
10:25 — Appointment Created

This is much better than raw log cards.

9. What makes it robust
A. No raw SQL

Never let the admin type arbitrary database queries.

B. No record modification

Stage A is read-only.

No:

create
update
delete
schedule
resolve
close

Only answer questions.

C. Supported-intent only

If question is unsupported, answer:

I can answer questions about patients, follow-up cases, reports, risk assessments, escalations, appointments, workflows, and audit history. This question is outside the currently supported Admin Intelligence scope.

D. Evidence-based answer

Every answer should include evidence references internally or visibly:

patient id
case id
report id
appointment id
audit id

This makes the answer trustworthy.

E. No clinical judgment

If admin asks:

Does marildo have infection?

Answer should not diagnose.

It should say:

I cannot diagnose. I can show recorded reports, risk assessments, escalations, and appointment status for Marildo.

This keeps the system safe.

10. Frontend UI behavior
Chat history

Each message pair:

Admin:

How many appointments are scheduled today?

System:

There are 3 appointments scheduled today.

Then optional table.

History remains until logout.

Suggested implementation:

localStorage
key: dentcare_admin_intelligence_<user_id>
clear on logout
Loading states

When asking:

show “Analyzing system data…”
disable submit button
Error states

If backend error:

show clear error message
do not clear chat
Suggestions

Three types:

Default suggestions

Shown before typing.

Typing suggestions

Based on current input.

Follow-up suggestions

Returned after answer.

Example after asking about patient Marildo:

“Show latest case for marildo”
“Show appointments for marildo”
“Show escalations for marildo”

That makes the interface feel much more intelligent.

11. UI layout

Recommended layout:

Admin Intelligence
Welcome, admin1
Ask operational questions about DentCare-MDE data.

[ input box .................................... Ask ]

Suggested:
[ Today’s appointments ] [ Unresolved escalations ] [ Latest case for patient ]

------------------------------------------------

Chat area:

You:
How many appointments are scheduled today?

Admin Intelligence:
There are 3 appointments scheduled today.

[table]

The page should use full width, not the old audit split layout.

12. What to do with the old audit page

Do not delete audit backend.

But frontend route can change from:

/audit-logs

to:

/admin-intelligence

Or keep the route but change label/page title.

Best:

dashboard button says Admin Intelligence
old audit logs are accessible through query:
“Show recent audit events”
“Show audit trace for case 4”

That is cleaner.

13. Testing plan

Backend tests should cover:

admin can query
patient cannot query
unsupported question returns safe response
count follow-up cases by patient
appointments today
unresolved escalations
active workflows
audit trace for case
patient name not found
typo/synonym handling for appointment
no data modification occurs

Frontend checks:

page loads
suggestions display
ask button works
answers render as summary/table/cards/timeline
chat history persists after refresh
logout clears or invalidates history
lint/build pass
14. What not to implement in Stage A

Do not add:

OpenAI API yet
LLM API key
SQL generation
database write actions
voice input
advanced analytics charts
patient access
dentist access unless explicitly needed
medical diagnosis answers
raw dump of all logs

Stage A must be stable first.

15. Best implementation order
Create admin_intelligence backend app.
Add admin-only query endpoint.
Implement deterministic query router.
Implement safe query handlers.
Add suggestions endpoint.
Build AdminIntelligencePage.jsx.
Replace Audit Logs dashboard link with Admin Intelligence.
Keep audit as queryable data source.
Add localStorage chat history.
Add tests.
Run backend checks and frontend build.
Final design decision

Stage A should be:

A rich admin-only chat-style interface powered by deterministic backend query handlers.

It should feel like AI, but it should be safe and controlled.

The strongest final identity:

Admin Intelligence helps administrators ask natural operational questions about DentCare-MDE data and receive grounded answers from the existing workflow, patient, report, escalation, appointment, and audit records.

This gives you a powerful AI-like feature without weakening the architecture.