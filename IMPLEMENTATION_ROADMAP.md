# IMPLEMENTATION_ROADMAP.MD

Below is the final updated Coding RoadMap for DentCare-MDE.

This is the implementation reference we should follow. It is structured as milestones, because the system must be built in dependency order: each milestone prepares the next one.

Core principle:

DentCare-MDE is not a generic dental chatbot.
It is a model-driven dental follow-up system where structured workflow models control patient guidance, risk decisions, escalation, and appointment priority.
0. Current status

Already completed:

Python installed and verified
Node.js / npm installed and verified
project-level virtual environment created
backend dependencies installed:
Django
Django REST Framework
django-cors-headers
requirements.txt created
root .gitignore created
monorepo-style structure created:
backend/
frontend/
Django project created:
backend/core
Django development server runs
SQLite used for early local development
Django settings updated with:
rest_framework
corsheaders
accounts
CORS configured for:
http://localhost:5173
React + Vite frontend created
Vite development server runs
accounts Django app created
custom user model created
roles added:
PATIENT
DENTIST
ADMIN
AUTH_USER_MODEL = "accounts.User" configured
custom user registered in Django admin

So the project is currently at:

environment setup + framework initialization + custom user/role foundation

Business logic has not started yet.

1. Final target of version 1

The first complete version should implement one full working loop:

Create workflow
Validate workflow
Activate workflow
Assign workflow to patient
Patient submits symptoms
Decision engine evaluates rules
System produces risk assessment + trace
Patient receives bounded advice or case is escalated
Staff reviews case
Appointment priority is handled
Audit log records important actions

The first workflow is:

Post-Extraction Follow-Up

Do not start with many dental treatments. One complete and well-designed workflow is better than several shallow workflows.

2. Non-negotiable design rules

These rules protect the project from becoming a normal CRUD web app.

Rule 1 — Workflow model is central

The system behavior must come from workflow data:

treatment stages
symptom definitions
symptom rules
risk levels
AI advice boundaries
escalation rules
appointment priority rules

Not from hardcoded backend conditions only.

The backend can evaluate rules, but the rules themselves must be stored as structured workflow data.

Rule 2 — Rules must be structured data

Do not store rule logic as raw executable strings such as:

pain_level >= 8 AND bad_smell = true

Use structured data, conceptually like:

{
  "all": [
    {"field": "pain_level", "operator": ">=", "value": 8},
    {"field": "bad_smell", "operator": "=", "value": true},
    {"field": "day_after_treatment", "operator": ">=", "value": 3}
  ]
}

This is safer, easier to validate, easier to test, and more aligned with model-driven thinking.

Rule 3 — AI does not decide risk

Correct runtime flow:

Patient report → workflow rule evaluation → risk decision → advice/escalation

Not:

Patient report → AI decides what to do

The AI/advice module only explains the decision within safe boundaries.

Rule 4 — Validation before activation

A workflow cannot become active unless it passes validation.

Invalid workflows must not be assigned to patients.

Rule 5 — Active workflow stability

Only ACTIVE workflows can be assigned to patients.

If an active workflow is later changed, do not silently modify the version used by existing patients. Prefer this lifecycle:

DRAFT → VALIDATED → ACTIVE → ARCHIVED

For version 1, versioning can be simple, but the logic should be respected.

Rule 6 — Decision trace is persistent

Every evaluated symptom report must store:

detected care stage
matched rules
risk level
recommended action
appointment priority if any
explanation
timestamp

This supports staff trust, audit, testing, and reporting.

Rule 7 — Image upload is not AI diagnosis

If image upload is included, it is supporting evidence for staff review only.

Not:

image → AI diagnosis
3. Milestone 1 — Foundation completion
Goal

Finish the base platform so users can authenticate and access the correct dashboard by role.

You already started this milestone.

What to build
Backend
login API
register API if needed
logout/token handling depending on chosen auth approach
current authenticated user endpoint
role-based permission helpers
basic protected API structure
Frontend
login page
register page if needed
authentication state handling
protected routes
role-based dashboard routing
Dashboards

Create basic placeholder dashboards:

Patient Dashboard

Shows:

patient area placeholder
no active follow-up case yet
Dentist/Staff Dashboard

Shows:

staff area placeholder
no escalated cases yet
Admin Dashboard

Shows:

workflow management placeholder
Why this milestone comes first

All later features depend on roles.

Example:

only admin can create workflows
only patient can submit reports
only dentist/staff can view escalations

If role control is weak, later modules become insecure and messy.

Completion condition

A user can log in and is routed to the correct dashboard:

patient → Patient Dashboard
dentist → Staff Dashboard
admin → Admin Dashboard
4. Milestone 2 — Workflow Modeling Core
Goal

Build the central model-driven artifact of the system: the dental workflow model.

This is the first real DentCare-MDE business milestone.

Backend concepts to implement
TreatmentWorkflow

Represents a dental follow-up workflow.

Example:

Post-Extraction Follow-Up

Main fields:

name
treatment type
status:
DRAFT
VALIDATED
ACTIVE
ARCHIVED
description
created by
timestamps
CareStage

Represents the recovery period stage.

Examples:

Day 0–1: immediate recovery
Day 2–3: early healing
Day 4–7: complication monitoring

Main fields:

workflow
name
start day
end day
description
SymptomDefinition

Defines symptoms that can be reported/evaluated.

Examples:

pain level: 0–10
swelling: none/mild/severe
bleeding: none/mild/severe
fever: yes/no
bad smell/taste: yes/no

Main fields:

workflow
symptom name
data type
allowed values or scale
description
SymptomRule

Defines condition → risk/action.

Example:

If:

stage = Day 4–7
pain level >= 8
bad smell = true

Then:

risk = HIGH
action = ESCALATE_TO_DENTIST
appointment priority = HIGH

Main fields:

stage
structured condition
risk level
recommended action
explanation
priority
AIAdviceBoundary

Defines what patient-facing support text may or may not say.

Main fields:

workflow or stage
allowed topics
forbidden topics
required disclaimer/template
risk level applicability if needed

Examples of forbidden topics:

diagnosis
prescription
telling patient to ignore urgent symptoms
EscalationRule

Defines what happens when a rule requires staff intervention.

Main fields:

linked symptom rule
target role:
dentist/staff
urgency
appointment priority
escalation message or reason
Frontend pages
Workflow List

Shows:

workflow name
treatment type
status
actions:
edit
validate
activate
archive
Workflow Create/Edit

Admin can define:

workflow basic information
care stages
symptom definitions
symptom rules
AI boundaries
escalation rules

Use forms first. Do not build a graphical workflow editor in version 1.

Completion condition

Admin can create a structured Post-Extraction Follow-Up workflow with:

stages
symptoms
rules
AI boundaries
escalation rules

The workflow may still be draft before validation.

5. Milestone 3 — Workflow Validation and Lifecycle
Goal

Make workflows safe and complete before they are used.

This milestone gives the project its “static semantics” layer.

Validation rules

Implement validation checks such as:

Structure validation
workflow must have at least one care stage
workflow must have at least one symptom definition
workflow must have at least one symptom rule
care stages must have valid day ranges
care stages must not overlap ambiguously
Safety validation
every HIGH risk rule must have escalation
every URGENT rule must have escalation
escalation must target dentist/staff or appointment priority
AI boundaries must forbid diagnosis/prescription
urgent symptoms cannot be handled only by AI advice
Lifecycle validation
invalid workflow cannot become VALIDATED
only VALIDATED workflow can become ACTIVE
only ACTIVE workflow can be assigned to patients
Workflow status transitions

Use this lifecycle:

DRAFT → VALIDATED → ACTIVE → ARCHIVED

Important behavior:

DRAFT can be edited
VALIDATED has passed checks
ACTIVE can be assigned to patients
ARCHIVED is no longer assignable

For version 1, keep versioning simple. Do not overbuild complex workflow version control unless needed.

Frontend behavior

Admin clicks:

Validate Workflow

System returns:

success: workflow is valid
errors: list of precise validation problems

Example error:

Urgent rule “fever = true” must have an escalation rule.

Completion condition

Admin can validate a workflow.
Only valid workflows can become active.
Only active workflows can later be assigned.

6. Milestone 4 — Patient Follow-Up Runtime
Goal

Connect real patients to active workflows.

Now the model starts controlling real patient cases.

Backend concepts to implement
PatientProfile

Minimal patient profile.

Fields:

user
contact information
basic dental notes if needed
allergies if needed
emergency contact if needed

Do not overbuild full medical history.

FollowUpCase

Represents one patient’s active dental recovery/follow-up process.

Fields:

patient
assigned workflow
treatment date
current status
assigned dentist/staff if needed
created date

Possible statuses:

CREATED
ACTIVE
MONITORING
AI_GUIDANCE_PROVIDED
ESCALATED
APPOINTMENT_REQUIRED
RESOLVED
CLOSED
Staff/admin functionality
create patient profile
assign active workflow to patient
create follow-up case
view patient follow-up status
Patient dashboard

Patient sees:

active treatment workflow
treatment date
current day after treatment
current status
button to submit symptom report
previous reports/results if available
Completion condition

A patient can have an active Post-Extraction follow-up case assigned from an active workflow.

7. Milestone 5 — Symptom Reporting
Goal

Allow patients to submit dental follow-up reports.

Backend concept
SymptomReport

Fields:

follow-up case
submitted by patient
day after treatment
pain level
swelling
bleeding
fever
bad smell/taste
notes
optional image
timestamp

For version 1, fields can be aligned with the Post-Extraction workflow.

Later, this can become more dynamic based on SymptomDefinition, but do not overcomplicate the first version.

Frontend
Symptom Report Form

Fields:

pain level: 0–10
swelling: none/mild/severe
bleeding: none/mild/severe
fever: yes/no
bad smell/taste: yes/no
notes
optional image upload
Important rule

Image upload is only supporting evidence for staff.

No automatic diagnosis from image.

Completion condition

Patient can submit a symptom report connected to their active follow-up case.

8. Milestone 6 — Decision Engine and Risk Assessment
Goal

Make the workflow executable.

This is the runtime core of DentCare-MDE.

Backend concepts
RiskAssessment

Stores the decision result for a symptom report.

Fields:

report
detected care stage
matched rules
risk level
recommended action
appointment priority if any
explanation
created timestamp
Decision engine responsibilities
1. Detect current care stage

Use:

treatment date
report day
workflow care stages

Example:

Day 4 → Day 4–7 stage

2. Evaluate structured rules

Use the rules from the active workflow.

Example structured rule:

{
  "all": [
    {"field": "pain_level", "operator": ">=", "value": 8},
    {"field": "bad_smell", "operator": "=", "value": true}
  ]
}
3. Select highest severity result

If multiple rules match:

URGENT beats HIGH
HIGH beats WARNING
WARNING beats LOW
4. Select recommended action

Possible actions:

SHOW_ADVICE
CONTINUE_MONITORING
RECOMMEND_CONTACT
ESCALATE_TO_DENTIST
PRIORITIZE_APPOINTMENT
5. Persist decision trace

Do not just compute and discard.

Store:

stage
matched rule IDs
risk level
explanation
recommended action
Example

Patient report:

Day 4
pain 8
bad smell yes
fever no

Matched rule:

pain >= 8 AND bad_smell = true in Day 4–7

Risk:

HIGH

Action:

ESCALATE_TO_DENTIST

Explanation:

Severe pain with bad smell after day 3 is marked high-risk in the active workflow.
Completion condition

Every symptom report produces a persistent RiskAssessment.

9. Milestone 7 — Bounded Advice Module
Goal

Give safe patient-facing messages based on the decision result.

This module does not decide risk.
It only explains the decision safely.

Initial implementation

Use template-based responses.

Examples:

LOW

Your symptoms appear consistent with the expected recovery stage. Continue monitoring and follow your dentist’s aftercare instructions.

WARNING

Your symptoms should be monitored carefully. If they worsen or continue, contact the clinic.

HIGH

Your report requires dental staff review. Your case has been sent to the clinic.

URGENT

Your symptoms may require urgent attention. The clinic has been notified, and you should follow staff instructions.

Boundaries

The advice module must not:

diagnose definitively
prescribe medication
override escalation
replace dentist/staff decision
tell patient to ignore serious symptoms
Completion condition

After a report is evaluated, patient receives a safe result/advice message consistent with the risk assessment.

10. Milestone 8 — Escalation and Staff Review
Goal

High-risk and urgent cases must reach dental staff.

Backend concept
EscalationCase

Fields:

report
risk assessment
status
urgency
assigned staff
staff response
created timestamp

Statuses:

NEW
IN_REVIEW
WAITING_FOR_PATIENT
APPOINTMENT_REQUIRED
RESOLVED
CLOSED
Automatic behavior

If risk is HIGH or URGENT:

create escalation case
attach report
attach risk assessment
show it in staff dashboard
Staff frontend
Staff Dashboard

Shows:

escalated cases
urgency
patient
treatment workflow
date
status
Escalation Case Detail

Shows:

patient data
report symptoms
optional image
detected care stage
matched rules
risk assessment
explanation
previous reports
response form

Staff can:

respond to patient
request more info
mark appointment required
resolve/close case
Completion condition

High-risk or urgent reports automatically create staff escalation cases that staff can review and act on.

11. Milestone 9 — Appointment Priority
Goal

Connect risk level to appointment handling.

Backend concept
Appointment

Fields:

patient
follow-up case
escalation case if linked
priority
scheduled date/time
status

Statuses:

REQUESTED
PRIORITY_SUGGESTED
SCHEDULED
COMPLETED
CANCELLED
Behavior

If decision result is HIGH:

appointment priority may be HIGH

If decision result is URGENT:

appointment priority may be URGENT

Staff confirms the real appointment time.

Patient can view appointment status.

Completion condition

Escalated cases can lead to prioritized appointments, and patients can see appointment updates.

12. Milestone 10 — Case Lifecycle and State Rules
Goal

Ensure follow-up cases progress consistently.

FollowUpCase state transitions

Example:

CREATED → ACTIVE
ACTIVE → MONITORING
MONITORING → AI_GUIDANCE_PROVIDED
MONITORING → ESCALATED
ESCALATED → APPOINTMENT_REQUIRED
APPOINTMENT_REQUIRED → RESOLVED
RESOLVED → CLOSED
Rules to enforce

Examples:

closed case cannot receive reports unless reopened
invalid workflow cannot be used
draft workflow cannot be assigned
escalated case should not be closed without staff action
appointment required state should have appointment record
Completion condition

Case state changes are controlled and consistent.

13. Milestone 11 — Audit and Decision Logging
Goal

Make system behavior traceable.

Backend concept
AuditLog

Fields:

actor
action
target type
target ID
timestamp
details
Events to log
workflow created
workflow validated
workflow activated
workflow assigned
symptom report submitted
risk assessment created
escalation created
staff response sent
appointment scheduled
case resolved/closed
Why this matters

It supports:

debugging
report quality
staff trust
cloud metrics later
security reasoning
Completion condition

Important system actions are recorded and inspectable.

14. Milestone 12 — Testing and Reliability
Goal

Prove the system logic works.

Testing should be added progressively, but this milestone completes the suite.

Workflow validation tests

Test:

workflow without stages is invalid
overlapping stages are invalid
urgent rule without escalation is invalid
AI boundary allowing prescription is invalid
draft workflow cannot be assigned
active workflow can be assigned
Decision engine tests

Test:

mild pain day 2 → LOW
fever → URGENT
severe bleeding → URGENT
pain >= 8 + bad smell day 4 → HIGH
LOW does not create escalation
HIGH creates escalation
Permission tests

Test:

patient cannot access another patient case
patient cannot create workflow
dentist can view escalations
admin can activate workflow
State tests

Test:

active case can receive report
high risk moves case toward escalation
escalated case can become appointment required
resolved case can close
closed case rejects new report unless reopened
Completion condition

Core workflow, decision, permission, and state logic are covered by tests.

15. Milestone 13 — UI Completion and Demo Flow
Goal

Make the system usable and presentable.

Patient UI polish

Ensure clear flow:

dashboard
active case
report symptoms
see result/advice
see escalation status
see appointment status
Staff UI polish

Ensure clear flow:

staff dashboard
escalated cases
case details
decision trace
response
appointment action
Admin UI polish

Ensure clear flow:

workflow list
create workflow
add stages/rules
validate
activate
assign to patient
Completion condition

A full demo can be performed without manual backend/admin intervention.

16. Milestone 14 — Report and Diagram Alignment
Goal

Make the implementation match the SWE report.

Diagrams to derive from the real system
Use Case Diagram
Class Diagram / domain model
Activity Diagram for symptom reporting and evaluation
Sequence Diagram for report → decision → advice/escalation
State Diagram for FollowUpCase lifecycle
Component Diagram
Deployment Diagram
Advanced SWE/MDD explanation

Explain:

workflow model as central artifact
workflow validation as static semantics
decision engine as execution semantics
model-to-behavior mapping
bounded AI boundary
constraints
possible future graphical/DSL editor
Completion condition

Report reflects the real implemented system, not imaginary features.

17. Milestone 15 — Optional Cloud Preparation
Goal

Prepare for later Cloud Computing reuse without distracting from SWE implementation.

Prepare
Docker configuration
environment variables
database externalization
clear API endpoints for load testing
simple logs/metrics endpoints if needed
Future cloud tests

Can test:

many symptom reports
many decision evaluations
response time
throughput
scaling behavior
Completion condition

Project is structurally ready for deployment/cloud adaptation later.

Final implementation order

Use this order:

Finish authentication and role dashboards
Build workflow model
Build workflow validation/lifecycle
Build patient profile and follow-up case
Build symptom reporting
Build decision engine and risk assessment
Build bounded advice module
Build escalation/staff review
Build appointment priority
Build case lifecycle rules
Build audit logging
Add tests progressively and complete test suite
Polish UI
Align report/diagrams
Prepare optional cloud deployment

The most important dependency chain is:

workflow model → validation → active workflow → follow-up case → symptom report → decision engine → advice/escalation

If we keep this chain clean, DentCare-MDE remains a robust, model-driven Advanced Software Engineering project rather than a simple dental web app.