 CURRENT_MILESTONE.md as the concrete working plan for Milestone 12 - Testing and Reliability.

Main adjustments:

Keep the milestone focused on reliability, not new product scope.
Reflect that backend modules and many focused tests already exist.
Prioritize missing cross-module regression coverage over rewriting good app-level tests.
Add environment reliability as a first concern because full backend test execution hit an inconsistent local Python/venv launcher issue.
Keep frontend work limited to lint/build and broken-flow fixes only.
Replacement Structure
CURRENT_MILESTONE.md should contain these sections:

Milestone name: Milestone 12 - Testing and Reliability
Goal: prove the implemented workflow-driven runtime is stable.
Why this matters: Milestones 1-11 built the runtime chain; Milestone 12 protects it before UI polish and report alignment.
In scope:
backend test review
cross-module high-risk Post-Extraction regression
low-risk no-escalation regression
permission coverage
lifecycle/state transition coverage
audit log coverage
downstream idempotency coverage
small reliability fixes only when tests expose real bugs
environment/test command reliability
Out of scope:
new features
model redesign
UI polish
report/diagram work
cloud/Docker work
LLM integration
new dependencies unless clearly required
Backend work:
Normalize/verify Python test environment.
Run existing app tests and record failures.
Preserve existing focused tests in accounts, workflows, patients, reports, decision_engine, ai_support, escalations, appointments, and audit.
Add one cross-module high-risk end-to-end backend test covering workflow activation through report, risk assessment, advice, escalation, appointment, case resolution, and audit logs.
Add one low-risk backend regression proving no escalation or appointment is created.
Fill only concrete gaps in permission, lifecycle, idempotency, workflow validation, rule evaluation, and audit coverage.
Apply small bug fixes only if tests expose real reliability problems.
Frontend work:
Run npm run lint.
Run npm run build.
Fix only broken imports, routes, API wiring, or implemented-flow reliability issues.
Expected file/module impact:
Mostly backend/*/tests.py.
Possible small fixes in serializers/services/views/lifecycle helpers if tests expose bugs.
Possible minimal frontend fixes under frontend/src.
No roadmap edits.
Dependencies/package changes:
None expected.
Migrations:
No migrations expected.
Run python manage.py makemigrations --check --dry-run.
Completion condition:
backend suite passes
Django check passes
migration dry-run passes
frontend lint/build pass
high-risk and low-risk regression tests exist and pass
no new product features added
Cautions:
Do not weaken permissions to pass tests.
Do not bypass workflow validation.
Do not remove audit logging.
Do not treat image upload as AI diagnosis.
Do not broaden beyond Post-Extraction v1 behavior.
Protect existing user changes in CURRENT_MILESTONE.md.
Implementation Plan In Short
Replace CURRENT_MILESTONE.md with a shorter repository-aware plan based on the structure above.
Start Milestone 12 implementation later by fixing the Python/venv test command issue first.
Then run the backend suite, add missing cross-module regression tests, and only fix bugs exposed by those tests.
Finish with Django checks, migration dry-run, frontend lint, and frontend build.
Assumptions And Risks
Existing CURRENT_MILESTONE.md is already directionally correct, so the rewrite should refine and tighten it rather than change the milestone.
No model changes or migrations should be needed.
The main uncovered area appears to be full cross-module regression coverage, not app-level unit coverage.
I observed CURRENT_MILESTONE.md already modified in the working tree; treat that as user-owned content.
Full backend test execution could not be verified because the venv/Python launcher became inconsistent and reported a missing Python 3.12 path. Frontend lint/build passed, and Django check plus migration dry-run initially passed.