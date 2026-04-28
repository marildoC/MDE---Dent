# PROJECT_STATUS.md

## Project
DentCare-MDE

## Current high-level identity
DentCare-MDE is a web-based, model-driven dental follow-up system where dental clinics define treatment-specific recovery workflows, validate them, assign them to patients, and use them to drive patient support, bounded AI advice, escalation, and appointment priority.

The system is not a generic dental chatbot.
The system is workflow-driven dental follow-up.

## Current setup completed
- Python installed and verified
- Node.js / npm installed and verified
- project-level virtual environment created
- backend dependencies installed:
  - Django
  - Django REST Framework
  - django-cors-headers
- requirements.txt created
- root .gitignore created
- monorepo structure created:
  - backend/
  - frontend/
- Django project created:
  - backend/core
- Django development server runs
- SQLite used for early local development
- React + Vite frontend created
- Vite development server runs
- accounts Django app created
- custom user model created
- roles added:
  - PATIENT
  - DENTIST
  - ADMIN
- AUTH_USER_MODEL configured
- custom user registered in Django admin
- JWT authentication API added
- current authenticated user API added
- role permission helpers added
- frontend login flow added
- protected frontend routes added
- role-based dashboard routing added
- placeholder dashboards added:
  - Patient Dashboard
  - Dentist/Staff Dashboard
  - Admin Dashboard
- workflows Django app created
- structured workflow models added:
  - TreatmentWorkflow
  - CareStage
  - SymptomDefinition
  - SymptomRule
  - AIAdviceBoundary
  - EscalationRule
- workflow models registered in Django admin
- admin-protected workflow APIs added
- workflow model migrations created and applied
- frontend admin workflow management pages added
- workflow validation service added
- workflow lifecycle API actions added:
  - validate
  - activate
  - archive
- invalid workflows are blocked from becoming validated or active
- active workflow structures are protected from direct API edits
- frontend admin validation/lifecycle controls added
- patients Django app created
- minimal patient profiles added
- follow-up cases added
- active workflow assignment enforcement added
- patient/staff follow-up access control added
- patient dashboard active-case display added
- staff/admin follow-up case management UI added
- reports Django app created
- symptom report model/API added
- patient symptom report submission added
- patient report history display added
- staff/admin symptom report visibility added
- decision_engine Django app created
- deterministic symptom report assessment service added
- persistent risk assessments added
- risk assessment API added
- patient and staff/admin risk assessment display added
- ai_support Django app created
- persistent bounded advice messages added
- deterministic template-based advice generation added
- advice generation API added
- new risk assessments create bounded advice downstream
- patient and staff/admin advice display added
- escalations Django app created
- persistent escalation cases added
- HIGH and URGENT risk assessments create staff escalations automatically
- staff/admin escalation queue and review updates added
- patient escalation status/response display added
- appointments Django app created
- persistent appointment records added
- staff/admin appointment creation and updates added for escalations
- appointment priority defaults from risk assessment/escalation context
- patient appointment status display added
- follow-up case lifecycle rules centralized and enforced
- escalation status transitions enforced
- appointment status transitions enforced
- terminal follow-up cases block new symptom reports
- appointment completion resolves linked follow-up cases
- patient/staff UI guards added for terminal and invalid lifecycle actions
- audit Django app created
- persistent audit log model added and migrated
- stable audit action constants added
- audit recording helper added
- important workflow/runtime actions now create structured audit logs
- admin-only audit log API added
- audit logs registered in Django admin
- minimal admin audit log frontend page added
- testing and reliability milestone completed
- backend regression coverage strengthened with cross-module Post-Extraction flows:
  - high-risk report -> risk assessment -> advice -> escalation -> appointment -> case resolution -> audit trace
  - low-risk report -> risk assessment -> advice without escalation or appointment
- backend app test suite passes
- Django system checks and migration dry-run pass
- frontend lint and build pass

## Current project stage
Testing and Reliability implemented and passing checks.

## Current active milestone
Milestone 12 - Testing and Reliability

## Immediate next objective
Prepare for Milestone 13 - UI Completion and Demo Flow:
- verify the browser demo flow for patient, staff, and admin users
- keep UI work focused on implemented workflows
- avoid new product features while polishing the existing demo path

## Fixed design decisions
- First complete workflow: Post-Extraction Follow-Up
- AI support is bounded and comes after deterministic decision logic
- SQLite is acceptable for early local development
- PostgreSQL will come later
- Workflow rules must be stored as structured data
- Image upload is supporting evidence only

## What is intentionally not implemented yet
- UI completion and demo polish
- report and diagram alignment
- cloud deployment

## Known cautions
- Do not run business-logic implementation before auth foundation is clean
- Do not let workflow behavior become hardcoded-only logic
- Do not add LLM-based AI before deterministic workflow evaluation exists
