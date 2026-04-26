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

## Current project stage
Workflow Modeling Core implemented and passing checks.
Runtime business logic has not started yet.

## Current active milestone
Milestone 2 - Workflow Modeling Core

## Immediate next objective
Manually verify admin workflow creation in the browser.
After that, refine the plan for Milestone 3 - Workflow Validation and Lifecycle.

## Fixed design decisions
- First complete workflow: Post-Extraction Follow-Up
- AI support is bounded and comes after deterministic decision logic
- SQLite is acceptable for early local development
- PostgreSQL will come later
- Workflow rules must be stored as structured data
- Image upload is supporting evidence only

## What is intentionally not implemented yet
- workflow validation
- patient follow-up cases
- symptom reports
- decision engine
- bounded advice module
- escalation logic
- appointment priority
- audit log
- cloud deployment

## Known cautions
- Do not run business-logic implementation before auth foundation is clean
- Do not let workflow behavior become hardcoded-only logic
- Do not add LLM-based AI before deterministic workflow evaluation exists
