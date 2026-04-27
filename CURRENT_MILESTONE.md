# CURRENT_MILESTONE.md

## Milestone Name

Milestone 5 - Symptom Reporting

## Goal

Allow patients to submit fixed-field Post-Extraction symptom reports connected to their own active follow-up case.

By the end of this milestone:

- a patient with an active follow-up case can submit a symptom report
- the report is persisted in the backend
- the patient can view their own report history
- dentist/admin users can view submitted reports
- no risk decision, advice, escalation, appointment, or audit behavior is created yet

This milestone captures patient recovery data only.

## Why This Milestone Matters

Milestone 4 connected patient users to active workflows through:

`User -> PatientProfile -> FollowUpCase`

Milestone 5 creates the next runtime input:

`FollowUpCase -> SymptomReport`

The decision engine in a later milestone will evaluate these reports against the active workflow rules. This milestone must therefore store clean, permission-safe report data without starting deterministic risk evaluation early.

## Current Repository State

Already implemented:

- `accounts` app with custom user roles: `PATIENT`, `DENTIST`, `ADMIN`
- JWT login and current-user API
- role-protected frontend routing
- `workflows` app with workflow models, validation, lifecycle actions, and admin workflow UI
- `patients` app with `PatientProfile` and `FollowUpCase`
- active workflow assignment enforcement
- patient dashboard active-case display
- staff/admin follow-up case management UI

Not implemented yet:

- no `reports` app exists
- no `SymptomReport` model exists
- no report API exists
- no patient symptom report form exists
- no report history UI exists
- no staff/admin report visibility exists

Current git caution:

- Milestone 4 files are still present as uncommitted/untracked changes.
- Build on the current working tree; do not revert Milestone 4 work.

## In Scope

- Create a new backend `reports` app.
- Add a fixed-field `SymptomReport` model.
- Link each report to `patients.FollowUpCase`.
- Record the authenticated patient user as `submitted_by`.
- Calculate `day_after_treatment` from the follow-up case treatment date on the backend.
- Allow patients to submit reports only for their own active/non-closed follow-up case.
- Allow patients to view only their own report history.
- Allow dentist/admin users to view reports.
- Add optional image upload as supporting evidence only.
- Add Django admin registration for reports.
- Add report API helpers in the frontend.
- Add patient-facing symptom report form.
- Add patient report history display.
- Add staff/admin report visibility in the follow-up case management area.
- Add focused backend tests for permissions, validation, and report creation.

## Out Of Scope

- Decision engine.
- Risk assessment.
- Workflow rule matching.
- Risk level selection.
- Bounded AI/advice responses.
- Automatic escalation.
- Appointment priority.
- Audit logging.
- Dynamic forms generated from `SymptomDefinition`.
- Image diagnosis or AI image interpretation.
- Notifications.
- User registration or demo-data seeding.
- Full clinic-management features.

## Backend Work

Create a new app:

- `backend/reports/`

Register it in:

- `backend/core/settings.py`
- `backend/core/urls.py`

Add model:

- `SymptomReport`

Fields:

- `follow_up_case`: FK to `patients.FollowUpCase`
- `submitted_by`: FK to `accounts.User`
- `day_after_treatment`: non-negative integer
- `pain_level`: integer, 0 to 10
- `swelling`: controlled choices: `NONE`, `MILD`, `SEVERE`
- `bleeding`: controlled choices: `NONE`, `MILD`, `SEVERE`
- `fever`: boolean
- `bad_smell`: boolean
- `notes`: optional text
- `image`: optional image/file upload
- `created_at`
- `updated_at`

Backend rules:

- only authenticated `PATIENT` users can create reports
- report creation must use a follow-up case owned by the authenticated patient
- reports cannot be submitted for another patient’s case
- reports cannot be submitted for `CLOSED` or `RESOLVED` cases
- staff/admin can view reports but cannot submit reports as patients
- backend calculates `day_after_treatment`; frontend must not be trusted for it
- image is stored only as supporting evidence and is not interpreted

API shape:

- `GET /api/reports/symptom-reports/`
  - patient: list own reports
  - dentist/admin: list reports
- `POST /api/reports/symptom-reports/`
  - patient only
- `GET /api/reports/symptom-reports/{id}/`
  - patient can retrieve own report
  - dentist/admin can retrieve reports
- optional query filtering:
  - `?follow_up_case=<id>` for staff/admin and for the owning patient

Keep the API simple. Do not add separate `my-reports` endpoint unless it meaningfully simplifies the frontend.

Serializer behavior:

- expose nested basic case details read-only if useful for UI
- keep `submitted_by` and `day_after_treatment` read-only
- validate pain level and choice fields
- validate ownership and case status server-side

Admin:

- register `SymptomReport`
- show patient, follow-up case, day, pain level, fever, bad smell, created date

Backend tests:

- patient can create a report for own active follow-up case
- patient cannot create a report for another patient’s case
- patient cannot submit for `CLOSED` case
- patient cannot submit for `RESOLVED` case
- patient can list/retrieve own reports
- patient cannot list/retrieve another patient’s reports
- dentist/admin can list/retrieve reports
- dentist/admin cannot create patient symptom reports
- invalid pain level is rejected
- invalid swelling/bleeding choices are rejected
- image is optional

## Frontend Work

Add report API helper module:

- `frontend/src/api/reports.js`

Add helpers for:

- list symptom reports
- create symptom report
- optional list by follow-up case

Patient UI:

- extend `PatientDashboard` or add a small patient report section under the active case summary
- show a `Submit symptom report` form only when an active case exists
- form fields:
  - pain level 0-10
  - swelling dropdown
  - bleeding dropdown
  - fever yes/no
  - bad smell/taste yes/no
  - notes
  - optional image upload, if backend upload handling is implemented in this milestone
- after submission:
  - refresh report history
  - show success message
  - do not show risk, advice, escalation, or diagnosis

Patient report history:

- show submitted date
- day after treatment
- pain level
- swelling
- bleeding
- fever
- bad smell
- notes summary if present

Staff/admin UI:

- extend `FollowUpManagementPage`
- show reports associated with follow-up cases
- keep the display simple and read-only
- do not add staff decision actions yet

## Expected File/Module Impact

Backend expected changes:

- new `backend/reports/` app
- `backend/core/settings.py`
- `backend/core/urls.py`
- new reports migration
- possible media settings only if image upload requires local development serving
- read-only integration with `patients.models.FollowUpCase`
- read-only integration with `accounts.models.UserRole`

Frontend expected changes:

- new `frontend/src/api/reports.js`
- `frontend/src/pages/Dashboards.jsx`
- `frontend/src/pages/FollowUpManagementPage.jsx`
- `frontend/src/App.css` only for necessary form/list styling

Do not modify workflow validation/lifecycle logic for this milestone.

## Dependencies Or Package Changes

No new backend package should be added unless image handling requires a clearly justified package.

Prefer Django’s built-in upload handling for the optional image field.

No new frontend package is expected.

If multipart upload is implemented, update frontend request handling carefully because the current shared `request()` helper defaults to JSON `Content-Type`.

## Migrations Expected

Yes.

Expected migration:

- create `reports_symptomreport`

Run:

- `python manage.py makemigrations reports`
- `python manage.py migrate`
- `python manage.py check`

Also run migration dry check after implementation:

- `python manage.py makemigrations --check --dry-run`

## Completion Condition

Milestone 5 is complete when:

- `reports` app exists and is registered
- `SymptomReport` model is implemented and migrated
- `SymptomReport` is registered in Django admin
- patient can submit a report for their own active follow-up case
- patient cannot submit for another patient’s case
- patient cannot submit for closed/resolved cases
- patient can view only their own report history
- dentist/admin can view reports
- patient dashboard exposes a working symptom report form
- patient dashboard shows report history
- staff/admin follow-up UI shows submitted reports
- no risk/advice/escalation/appointment behavior is present
- backend tests for report permissions and validation pass
- `python manage.py check` passes
- migrations are applied
- frontend lint/build pass if frontend files are changed

## Cautions

- Do not implement the decision engine.
- Do not create `RiskAssessment`.
- Do not evaluate workflow rules.
- Do not calculate risk level.
- Do not create AI/advice messages.
- Do not create escalation or appointment records.
- Do not add audit logging.
- Do not diagnose uploaded images.
- Do not build dynamic workflow-driven symptom forms yet.
- Keep fixed fields aligned with Post-Extraction version 1.
- Keep backend permissions authoritative.
- Do not expose reports across patients.
- Do not trust frontend-provided ownership or day-after-treatment.
- Preserve existing Milestone 4 patient/case behavior.
- Build on the current working tree and do not revert uncommitted Milestone 4 files.
