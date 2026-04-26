Milestone 2 - Workflow Modeling Core
Summary
Goal: build the central structured workflow model for DentCare-MDE, starting with Post-Extraction Follow-Up.

This milestone creates the data model, admin/API surface, and minimal admin frontend needed to define workflow structures. It does not validate, activate, assign, execute, or evaluate workflows yet.

Current repo state:

Milestone 1 auth foundation is implemented.
accounts has UserRole and IsAdminRole.
Backend has no workflows app yet.
Frontend has protected role routes and an admin dashboard placeholder.
Django migrations are current and manage.py check passes.
In Scope
Create a new workflows Django app.
Add structured workflow models:
TreatmentWorkflow
CareStage
SymptomDefinition
SymptomRule
AIAdviceBoundary
EscalationRule
Store rule conditions as JSON structured data, never executable strings.
Add Django admin registration for workflow models.
Add admin-protected DRF APIs for CRUD operations.
Add frontend admin workflow management pages:
workflow list
workflow create/edit
workflow detail with simple forms for stages, symptoms, rules, AI boundaries, and escalation rules
Allow creating the Post-Extraction Follow-Up workflow structure as DRAFT.
Out of scope:

Workflow validation and activation enforcement.
Patient profiles, follow-up cases, symptom reports, decision engine, advice generation, escalation cases, appointments, audit logging.
Dynamic patient report forms.
Graphical workflow editor.
LLM/image diagnosis/cloud work.
Backend Plan
Implement workflows and add it to INSTALLED_APPS.

Models:

TreatmentWorkflow

name, treatment_type, status, description, created_by, timestamps
status choices: DRAFT, VALIDATED, ACTIVE, ARCHIVED
first treatment choice: POST_EXTRACTION
default status: DRAFT
CareStage

workflow, name, start_day, end_day, description, sort_order
examples: Day 0-1, Day 2-3, Day 4-7
SymptomDefinition

workflow, key, label, data_type, allowed_values, min_value, max_value, description, is_required
data types: INTEGER, BOOLEAN, CHOICE, TEXT
intended Post-Extraction keys: pain_level, swelling, bleeding, fever, bad_smell
SymptomRule

stage, name, condition, risk_level, recommended_action, appointment_priority, explanation
risk choices: LOW, WARNING, HIGH, URGENT
action choices: SHOW_ADVICE, CONTINUE_MONITORING, RECOMMEND_CONTACT, ESCALATE_TO_DENTIST, PRIORITIZE_APPOINTMENT
priority choices: NONE, LOW, NORMAL, HIGH, URGENT
condition supports all / any groups and operators =, !=, >, >=, <, <=, in
AIAdviceBoundary

workflow, optional stage, allowed_topics, forbidden_topics, required_disclaimer
must support boundaries against diagnosis and prescription, but does not generate advice yet
EscalationRule

linked symptom_rule, target_role, urgency, appointment_priority, message
target role should use existing roles, with DENTIST as the staff target for v1
APIs:

Use DRF serializers and viewsets.
Register routes under /api/workflows/.
Require IsAdminRole for create/update/delete.
Keep read access admin-only in this milestone.
Use simple flat endpoints for each model; nesting can be added later only if needed.
Backend tests:

admin can create a workflow
non-admin cannot create workflow data
workflow related objects can be created
structured rule condition JSON is accepted
invalid obvious condition shape is rejected only at a basic structural level, without implementing full workflow validation
Frontend Plan
Extend the existing admin area only.

Add workflow API helper methods.
Add admin route for workflow management.
Update Admin Dashboard to link to workflow management.
Add workflow list page.
Add create/edit workflow form.
Add workflow detail page with simple sections/forms for:
care stages
symptom definitions
symptom rules
AI advice boundaries
escalation rules
Keep UI form-based, compact, and functional.
Do not expose workflow management to patient or dentist dashboards.
File/Module Impact
Expected backend changes:

new backend/workflows/ app
backend/core/settings.py
backend/core/urls.py
workflow migration files
possible reuse of backend/accounts/permissions.py
Expected frontend changes:

frontend/src/App.jsx
frontend/src/pages/
frontend/src/api/
possibly shared form/style additions in existing CSS
Dependencies:

No new backend package expected.
No new frontend package expected.
Use existing Django, DRF, SimpleJWT, React, and React Router.
Migrations:

Yes. New workflow models require migrations.
Run makemigrations, migrate, then python manage.py check.
Completion Condition
Milestone 2 is complete when:

workflows app exists and is registered.
Workflow models are migrated and visible in Django admin.
Admin-protected workflow APIs exist.
Admin can create a TreatmentWorkflow.
Admin can add care stages, symptom definitions, symptom rules, AI advice boundaries, and escalation rules.
Non-admin users cannot create or modify workflow data through the API.
Admin frontend can create/view the core Post-Extraction Follow-Up workflow structure.
python manage.py check passes.
Focused workflow API/model permission tests pass.
Cautions
Do not implement workflow validation lifecycle behavior in this milestone.
Do not activate or assign workflows yet.
Do not implement report submission or decision evaluation.
Do not hardcode Post-Extraction behavior only in backend logic; store it as workflow data.
Do not store rule conditions as raw strings.
Do not add LLM or patient-facing advice behavior.
Keep active workflow immutability concerns for later lifecycle work.
Keep this milestone narrow: model structure, admin CRUD, minimal admin UI.