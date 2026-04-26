# CURRENT_MILESTONE.md

## 1. Milestone

Milestone 2 — Workflow Modeling Core

---

## 2. Goal

Build the first real DentCare-MDE business/modeling layer: the structured dental workflow model.

By the end of this milestone, an admin should be able to create and view the core data structure for a Post-Extraction Follow-Up workflow, including stages, symptom definitions, symptom rules, AI advice boundaries, and escalation rules.

This milestone does not need full workflow validation yet. It must create the model/API/UI foundation that validation will use in the next milestone.

---

## 3. Why this milestone matters

DentCare-MDE is workflow-driven. All later behavior depends on the workflow model:

workflow model -> validation -> patient report -> deterministic decision -> bounded advice or escalation -> staff action -> appointment priority -> audit trace

Before building patient cases, symptom reports, decisions, advice, escalation, or appointments, the system needs a structured workflow model stored as data.

This milestone creates that central artifact.

---

## 4. In scope

- Create the `workflows` backend app if it does not exist.
- Add workflow-related backend models:
  - TreatmentWorkflow
  - CareStage
  - SymptomDefinition
  - SymptomRule
  - AIAdviceBoundary
  - EscalationRule
- Add controlled enums/choices for:
  - workflow status
  - treatment type
  - symptom data type
  - risk level
  - recommended action
  - appointment priority/urgency where needed
- Store symptom rule conditions as structured JSON, not raw executable strings.
- Add Django admin registration for workflow models.
- Add serializers and API endpoints for admin workflow management.
- Add basic role protection so only admin users can create/update workflow structures in this milestone.
- Add frontend admin workflow pages:
  - workflow list
  - create workflow
  - basic workflow detail/edit view
- Allow admin to define the first workflow structure for Post-Extraction Follow-Up.
- Keep UI form-based and simple.

---

## 5. Out of scope

- Workflow validation logic.
- Workflow activation enforcement beyond basic status field support.
- Patient profile and follow-up case assignment.
- Symptom report submission.
- Decision engine and risk assessment.
- Bounded AI/advice generation.
- Escalation case creation.
- Appointment scheduling.
- Audit logging.
- Dynamic symptom report forms.
- Graphical workflow editor.
- LLM integration.
- Image upload.
- Cloud/Docker work.

---

## 6. Backend work

- Create/configure `workflows` app and add it to installed apps.
- Implement workflow domain models.

Expected model responsibilities:

### TreatmentWorkflow
Represents a dental follow-up workflow.

Fields should support:
- name
- treatment type
- status
- description
- created_by
- timestamps

Initial statuses:
- DRAFT
- VALIDATED
- ACTIVE
- ARCHIVED

For this milestone, new workflows should normally start as `DRAFT`.

### CareStage
Represents a time period in the workflow.

Fields should support:
- workflow
- name
- start_day
- end_day
- description
- ordering if useful

Example:
- Day 0–1
- Day 2–3
- Day 4–7

### SymptomDefinition
Defines what symptoms can be captured/evaluated.

Fields should support:
- workflow
- name/key
- label
- data type
- allowed values or scale metadata if needed
- description

Version 1 symptoms for Post-Extraction should support:
- pain_level
- swelling
- bleeding
- fever
- bad_smell

### SymptomRule
Defines condition -> risk/action.

Fields should support:
- stage
- name
- structured condition JSON
- risk level
- recommended action
- appointment priority if relevant
- explanation

Condition must be stored as structured JSON.

Allowed operator set for version 1:
- =
- !=
- >
- >=
- <
- <=
- in

Allowed logical groups:
- all
- any

Example condition:

```json
{
  "all": [
    {"field": "pain_level", "operator": ">=", "value": 8},
    {"field": "bad_smell", "operator": "=", "value": true},
    {"field": "day_after_treatment", "operator": ">=", "value": 3}
  ]
}
AIAdviceBoundary

Defines allowed and forbidden advice topics.

Fields should support:

workflow or stage association
allowed topics
forbidden topics
required disclaimer/template text if needed

Must support the core boundary that AI/advice cannot diagnose or prescribe.

EscalationRule

Defines what happens when a rule requires staff attention.

Fields should support:

linked symptom rule
target role or target staff type
urgency
appointment priority
reason/message
Add serializers for these models.
Add API views/viewsets for workflow CRUD needed by admin.
Add URL routes under a clean namespace such as /api/workflows/.
Restrict create/update/delete workflow APIs to admin users.
Read access can be admin-only for now unless a simple staff read permission is needed.
Add basic tests where practical:
admin can create workflow
non-admin cannot create workflow
structured condition JSON is accepted
workflow related objects can be created
7. Frontend work
Add admin navigation entry or dashboard action for workflow management.
Create basic workflow list page.
Create basic create workflow form.
Create basic workflow detail/edit area sufficient to add:
care stages
symptom definitions
symptom rules
AI advice boundaries
escalation rules

Keep the frontend simple and functional.

The UI does not need to be polished. It only needs to support creating/viewing the workflow model.

Do not build patient-facing workflow usage yet.

8. Data/model impact

Expected new backend app:

workflows

Expected new entities:

TreatmentWorkflow
CareStage
SymptomDefinition
SymptomRule
AIAdviceBoundary
EscalationRule

Expected settings/API impact:

add workflows to installed apps
add workflow API URLs to root API routing
add migrations for workflow models
update admin registration
possibly add admin-only permission class or reuse existing role helper

Expected frontend impact:

add workflow API client methods
add admin workflow pages/routes
update admin dashboard to link to workflow management

No patient/report/decision/escalation/appointment models should be created in this milestone.

9. Completion condition

This milestone is complete when:

workflows backend app exists and is registered.
Workflow models are implemented and migrated.
Workflow models are visible/manageable in Django admin.
Admin-protected workflow APIs exist.
Admin user can create a TreatmentWorkflow.
Admin user can add stages, symptoms, rules, AI boundaries, and escalation rules.
Non-admin users cannot create or modify workflows through the API.
Frontend admin dashboard links to workflow management.
Admin can use the frontend to create/view the core Post-Extraction Follow-Up workflow structure.
python manage.py check passes.
Migrations are created and applied.
Relevant backend tests pass if added.
10. Cautions
Do not implement workflow validation in this milestone. Only create the model structure that validation will later inspect.
Do not implement patient assignment or symptom report evaluation yet.
Do not hardcode the Post-Extraction logic only in code; store it as workflow data.
Do not store rule conditions as executable strings.
Do not add LLM logic or patient-facing AI advice behavior yet.
Do not overbuild a graphical workflow editor. Use simple forms.
Do not make reports fully dynamic yet. SymptomDefinition exists now, but dynamic patient report forms come later if needed.
Keep permissions backend-enforced, not only hidden in the frontend.
Keep the model minimal but sufficient for Post-Extraction Follow-Up.
If models change, create and apply migrations.
After backend changes, run python manage.py check.