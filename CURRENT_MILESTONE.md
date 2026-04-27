# CURRENT_MILESTONE.md

## Milestone Name
Milestone 11 - Audit and Decision Logging

## Goal
Add persistent audit logging for important DentCare-MDE actions across the existing workflow/runtime chain.

The audit trail should record:
- who acted
- what action occurred
- what object was affected
- when it happened
- safe structured metadata about the event

This milestone must not change workflow validation, risk decisions, advice generation, escalation behavior, appointment behavior, or case lifecycle rules.

## Why This Milestone Matters
DentCare-MDE is a model-driven dental follow-up system. Workflow models drive patient reports, deterministic decisions, advice, escalations, staff actions, appointment priority, and case lifecycle changes.

Audit logging makes that chain traceable:

workflow model -> validation -> follow-up case -> symptom report -> deterministic decision -> bounded advice/escalation -> staff action -> appointment priority -> audit trace

This supports debugging, staff trust, testing, and the SWE/MDD report.

## In Scope
- Create a new backend `audit` app.
- Add persistent `AuditLog` model.
- Add stable audit action constants.
- Add a reusable audit recording helper/service.
- Register audit logs in Django admin.
- Add a read-only audit API for admin users.
- Record audit events going forward from existing stable backend points.
- Add focused backend tests for audit creation, permissions, and sensitive-detail avoidance.
- Add a simple admin-only frontend audit log page if backend work is complete and the UI change remains small.
- Update `PROJECT_STATUS.md` after implementation.

## Out of Scope
- Changing business logic from Milestones 1-10.
- Changing workflow validation rules.
- Changing decision-engine risk evaluation.
- Changing bounded advice templates.
- Changing escalation creation rules.
- Changing appointment lifecycle behavior.
- Notifications.
- Real-time event streaming.
- Analytics dashboards.
- Export/reporting tools.
- External immutable log storage.
- Backfilling audit logs for existing database records.
- Patient-facing audit timeline.
- Complex dentist-specific audit filtering.

## Backend Work

### 1. Create Audit App
Create a new Django app:

- `backend/audit/`

Register it in:

- `backend/core/settings.py`
- `backend/core/urls.py`

API path:

- `/api/audit/logs/`

### 2. Add AuditLog Model
Add `AuditLog` with:

- `actor`: nullable FK to user
- `action`: stable string action
- `target_type`: string
- `target_id`: string
- `target_repr`: short readable label
- `details`: JSON field, default dict
- `created_at`: timestamp

Ordering:

- newest first

Create and apply migration.

### 3. Add Action Constants
Create stable constants, likely in `backend/audit/actions.py`.

Required actions:

- `WORKFLOW_VALIDATED`
- `WORKFLOW_ACTIVATED`
- `WORKFLOW_ARCHIVED`
- `FOLLOW_UP_CASE_CREATED`
- `FOLLOW_UP_CASE_STATUS_CHANGED`
- `SYMPTOM_REPORT_SUBMITTED`
- `RISK_ASSESSMENT_CREATED`
- `ADVICE_CREATED`
- `ESCALATION_CREATED`
- `ESCALATION_UPDATED`
- `APPOINTMENT_CREATED`
- `APPOINTMENT_UPDATED`

Use constants, not scattered raw strings.

### 4. Add Audit Service
Create `record_audit(actor, action, target, details=None)`.

Behavior:
- Accept `actor=None` for system-generated events.
- Derive `target_type`, `target_id`, and `target_repr` from the target object.
- Store `details` as safe structured metadata.
- Do not swallow programming errors with broad silent exception handling.
- Do not add an event bus or signal-heavy architecture.

### 5. Integrate Audit Calls
Add audit calls at stable points:

- Workflow lifecycle actions in `workflows.views`
  - validate
  - activate
  - archive

- Follow-up case creation/status change in `patients`
  - serializer/view update path
  - lifecycle helper/service where status transitions are applied

- Symptom report submission in `reports.serializers`
  - after report is created

- Risk assessment creation in `decision_engine.services`
  - after `RiskAssessment.objects.create`

- Advice creation in `ai_support.services`
  - after `AdviceMessage.objects.create`

- Escalation creation/update in `escalations.services` and/or serializer update path

- Appointment creation/update in `appointments.services` and serializer update path

Avoid duplicate audit rows when a service is idempotent and returns an existing object.

### 6. Sensitive Data Rules
Do not store full free-text clinical content in audit details.

Avoid:
- full symptom report notes
- full dental notes
- full staff response
- full advice message
- image file contents or paths

Prefer:
- object IDs
- old/new status
- risk level
- recommended action
- appointment priority
- matched rule IDs
- workflow ID
- follow-up case ID
- patient profile ID
- assigned staff ID

### 7. Audit API
Add read-only DRF serializer/viewset.

Access:
- Admin users can list/retrieve audit logs.
- Dentist/staff access is out of scope for this milestone unless a simple safe filter is already obvious.
- Patients cannot access audit logs.
- Unauthenticated users cannot access audit logs.

Optional simple filters:
- `action`
- `target_type`
- `target_id`
- `actor`

Do not add search, export, analytics, or complex reporting.

### 8. Django Admin
Register `AuditLog`.

Useful list fields:
- `created_at`
- `action`
- `actor`
- `target_type`
- `target_id`
- `target_repr`

## Frontend Work
Add a minimal admin-only audit page only after backend audit API is working.

Expected frontend impact:
- `frontend/src/api/audit.js`
- a simple `AuditLogPage.jsx`
- admin dashboard link
- protected route for `ADMIN`

Display:
- timestamp
- action
- actor
- target type
- target label/id
- compact details

Do not expose audit logs to patients.
Do not build charts, exports, advanced filters, or patient timelines.

If backend audit work takes longer than expected, frontend audit UI may be deferred, but the backend API and Django admin visibility must be completed.

## Expected File/Module Impact
Backend:
- `backend/audit/models.py`
- `backend/audit/actions.py`
- `backend/audit/services.py`
- `backend/audit/serializers.py`
- `backend/audit/views.py`
- `backend/audit/urls.py`
- `backend/audit/admin.py`
- `backend/audit/tests.py`
- `backend/core/settings.py`
- `backend/core/urls.py`
- focused audit calls in:
  - `workflows.views`
  - `patients.serializers` or `patients.lifecycle`
  - `reports.serializers`
  - `decision_engine.services`
  - `ai_support.services`
  - `escalations.services` / `escalations.serializers`
  - `appointments.services` / `appointments.serializers`

Frontend, if included:
- `frontend/src/api/audit.js`
- `frontend/src/pages/AuditLogPage.jsx`
- `frontend/src/App.jsx`
- `frontend/src/pages/Dashboards.jsx`
- `frontend/src/App.css` only for minimal styling

## Dependencies or Package Changes
No new package dependencies are expected.

## Migrations
A migration is expected because this milestone adds the `AuditLog` model.

Run:
- `python manage.py makemigrations audit`
- `python manage.py migrate`

## Completion Condition
Milestone 11 is complete when:
- `audit` app exists and is registered.
- `AuditLog` model exists and is migrated.
- Stable audit action constants exist.
- `record_audit` helper exists.
- Key runtime actions create audit entries going forward.
- Audit details avoid unnecessary sensitive free text.
- Admin can view audit logs through API and Django admin.
- Patients cannot access audit logs.
- Existing Milestone 1-10 behavior remains unchanged.
- Focused audit tests pass.
- Full Django app tests pass.
- `python manage.py check` passes.
- Frontend build passes if frontend files are changed.

## Cautions
- Do not change deterministic risk logic.
- Do not change workflow validation behavior.
- Do not change advice generation behavior.
- Do not change escalation or appointment business rules.
- Do not expose audit logs to patients.
- Do not backfill old records.
- Do not store full clinical notes, staff responses, advice text, or image content in audit details.
- Avoid circular imports when adding audit calls.
- Prefer explicit service calls over broad Django signals for this milestone.
- Keep audit logging simple and testable.
