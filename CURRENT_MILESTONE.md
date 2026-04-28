Milestone 13 - UI Completion and Demo Flow
Summary
Polish the existing DentCare-MDE UI so the implemented Post-Extraction workflow can be demonstrated clearly across patient, staff/admin, and admin audit views.

The current CURRENT_MILESTONE.md is mostly aligned with the roadmap. Refine it to be more repository-aware, keep it limited to UI/demo polish, and make the implementation order explicit.

Goal
Make the existing browser experience demo-ready for this implemented chain:

workflow setup -> patient follow-up case -> symptom report -> risk assessment -> bounded advice -> escalation -> appointment -> case resolution -> audit trace

This milestone must not add new domain behavior.

Why This Matters
Milestones 1-12 implemented and tested the core workflow-driven system. Milestone 13 should make that real system understandable in the browser without changing deterministic backend rules.

The UI should clearly show:

workflow status and lifecycle
active patient follow-up context
report history and risk assessment
bounded patient advice
staff escalation and appointment handling
admin audit trace
In Scope
Improve existing React pages only:
Dashboards.jsx
WorkflowListPage.jsx
WorkflowDetailPage.jsx
FollowUpManagementPage.jsx
AuditLogPage.jsx
Improve existing navigation between dashboard, workflows, follow-up cases, and audit logs.
Replace remaining placeholder copy with accurate implemented-state copy.
Add readable labels/status badges for workflow, case, report, risk, escalation, appointment, and audit states.
Improve existing form usability, loading states, empty states, success messages, and API error display.
Hide or translate raw internal constants on patient-facing views where practical.
Keep compact technical context visible on staff/admin views where useful.
Ensure terminal/resolved/closed cases are visibly non-actionable.
Fix small backend serializer/view issues only if an existing UI flow is blocked.
Run frontend lint/build and backend checks.
Out Of Scope
New backend business logic.
New models, migrations, workflow rules, report fields, or decision behavior.
New advice, escalation, appointment, or audit semantics.
Notifications, real-time updates, LLM/chat, analytics, exports, full calendar scheduling.
Report/diagram work.
Cloud/Docker work.
UI framework or design-system migration.
Broad redesign beyond demo-flow clarity.
Backend Work
Backend work should be avoided by default.

Allowed only if the UI exposes a real blocker:

expose an already-existing read-only serializer field needed by an existing screen
fix broken response shape, filtering, or permission behavior for the implemented demo path
fix an endpoint issue that prevents existing patient/staff/admin UI flows
Do not change:

workflow validation
risk assessment logic
advice generation
automatic escalation creation
appointment priority/lifecycle rules
audit logging semantics
Documentation cleanup:

update PROJECT_STATUS.md active milestone from Milestone 12 to Milestone 13 when implementation begins or completes, because current docs conflict.
Frontend Work
Work in dependency order:

Navigation and dashboards

Make patient, staff, and admin dashboards show useful implemented entry points.
Ensure admin links to workflow management, follow-up cases, and audit logs are clear.
Ensure staff link to follow-up management is clear.
Patient flow

Show active follow-up case, treatment date, recovery day, and status.
Show symptom report form only when case status allows reports.
Show report history with readable risk/advice/escalation/appointment summaries.
Translate patient-facing constants where practical.
Staff/admin follow-up flow

Improve follow-up case list readability.
Group report, risk, advice, escalation, appointment, and lifecycle information clearly.
Make invalid/terminal actions disabled or visibly unavailable.
Improve staff response and appointment controls without adding scheduling features.
Admin workflow and audit flow

Improve workflow status, validation, activation, and archive visibility.
Keep workflow forms form-based, not graphical.
Improve audit log readability: timestamp, actor, action, target, compact details.
CSS and responsiveness

Keep styling in existing CSS.
Reuse current layout patterns.
Fix mobile/text overflow issues where found.
Avoid introducing new dependencies.
Expected File/Module Impact
Frontend likely:

frontend/src/pages/Dashboards.jsx
frontend/src/pages/FollowUpManagementPage.jsx
frontend/src/pages/WorkflowListPage.jsx
frontend/src/pages/WorkflowDetailPage.jsx
frontend/src/pages/AuditLogPage.jsx
frontend/src/App.css
Backend only if needed:

serializers/views in existing apps, with no model changes expected
Docs:

CURRENT_MILESTONE.md rewrite to this plan
PROJECT_STATUS.md active milestone correction when moving forward
Dependencies And Migrations
No new package dependencies expected.
No migrations expected.
If a model change appears necessary, stop and justify it before implementation.
Completion Condition
Milestone 13 is complete when:

full browser demo can be performed through existing UI routes
patient report/advice/escalation/appointment status is clear
staff/admin escalation and appointment handling is clear
admin workflow and audit navigation is clear
terminal cases are clearly non-actionable
patient-facing views avoid diagnosis/prescription wording and avoid unnecessary raw constants
no new product scope was added
npm.cmd run lint passes
npm.cmd run build passes
python manage.py check passes
python manage.py makemigrations --check --dry-run passes
backend tests pass if backend code changes
Cautions
Preserve the model-driven identity: workflow data controls runtime behavior.
Do not weaken permissions for UI convenience.
Do not change tested Milestone 1-12 backend behavior.
Do not expose audit logs to patients.
Do not treat image upload as diagnosis.
Do not add future milestone features under UI polish.
Keep changes focused on making the real implemented system understandable.