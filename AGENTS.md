# AGENTS.md

## Project identity

DentCare-MDE is a model-driven dental follow-up system.

It is not a generic dental chatbot, not an autonomous diagnosis system, and not a full clinic-management platform.

The core system behavior is:

workflow model -> workflow validation -> patient follow-up case -> symptom report -> deterministic decision -> bounded advice or escalation -> staff action -> appointment priority -> audit trace

The workflow model is the central artifact of the system.

---

## Files to read first

Before starting non-trivial work, read:

- PROJECT_STATUS.md
- IMPLEMENTATION_ROADMAP.md
- CURRENT_MILESTONE.md

Use these files to understand:

- what is already completed
- what the current milestone is
- what is in scope
- what is out of scope
- what the completion condition is

Do not modify IMPLEMENTATION_ROADMAP.md unless explicitly asked.

---

## Working behavior

Before making significant changes:

1. Inspect the relevant existing files.
2. Understand the current implementation.
3. Propose a short implementation plan.
4. Then make focused changes.

For very small obvious fixes, a short plan is not required.

Work mainly inside the current milestone. Do not implement future milestones unless a small supporting change is necessary for the current milestone to work correctly.

Do not invent new product features, new roles, new modules, or new architecture outside the roadmap.

Small engineering improvements are allowed when they directly support the current milestone, such as:

- fixing a related import or configuration issue
- adding a small helper to avoid duplication
- aligning serializers/admin/URLs after model changes
- improving validation/error handling for the feature being implemented
- adding minimal tests for changed logic
- cleaning clearly broken or inconsistent code touched by the task

Avoid broad refactors, unrelated cleanup, or speculative abstractions.

---

## Engineering standards

Prefer simple, readable, testable code.

Intended module boundaries:

- accounts: users, roles, authentication, permissions
- patients: patient profile and follow-up cases
- workflows: workflow model, stages, symptoms, rules, validation
- reports: symptom reports and report history
- decision_engine: stage detection, rule matching, risk assessment
- ai_support: bounded advice/templates
- escalations: staff review and escalation cases
- appointments: appointment priority and scheduling
- audit: important system events and decision trace

If a model changes, check whether related admin, serializers, views, permissions, URLs, tests, and frontend usage need updates.

Do not add dependencies unless clearly necessary. If a dependency is needed, explain why.

Do not silently assume missing requirements. If something important is unclear, state the assumption and choose the simplest safe option.

---

## Core design rules

These rules must be preserved:

1. Workflow model is central.
2. Workflow rules are structured data, not raw executable strings.
3. AI does not decide risk.
4. Decision Engine decides risk/action deterministically.
5. AI/advice module only explains the decision within safe boundaries.
6. Workflow validation happens before activation.
7. Only ACTIVE workflows can be assigned to patients.
8. Active workflows should not be edited directly in version 1.
9. Every symptom report should produce a persistent RiskAssessment.
10. Decision trace must store detected stage, matched rules, risk level, action, explanation, and timestamp.
11. Image upload is supporting evidence for staff review only, not AI diagnosis.
12. High or urgent reports must create staff escalation.
13. Appointment priority follows workflow/decision risk, not manual guesswork.
14. Important actions should be auditable.

---

## Rule condition format

Do not store rule logic as raw executable strings.

Use structured rule data.

Example:

{
  "all": [
    { "field": "pain_level", "operator": ">=", "value": 8 },
    { "field": "bad_smell", "operator": "=", "value": true },
    { "field": "day_after_treatment", "operator": ">=", "value": 3 }
  ]
}

Version 1 should support only a small controlled operator set:

- =
- !=
- >
- >=
- <
- <=
- in

Logical groups:

- all
- any

Keep rule evaluation safe, explicit, and testable.

---

## Risk and action rules

Risk severity order:

LOW < WARNING < HIGH < URGENT

If multiple rules match, choose the highest severity.

Recommended actions should stay controlled, for example:

- SHOW_ADVICE
- CONTINUE_MONITORING
- RECOMMEND_CONTACT
- ESCALATE_TO_DENTIST
- PRIORITIZE_APPOINTMENT

Do not let patient-facing advice override the selected action.

---

## Version 1 scope

Version 1 focuses on:

Post-Extraction Follow-Up

Keep the first implementation complete and narrow.

Do not implement first:

- full dental clinic management
- many treatment families
- autonomous diagnosis
- prescription recommendation
- AI image diagnosis
- graphical workflow editor
- payment/subscription logic
- sales/marketing modules
- broad hospital system
- LLM integration as a core dependency

These can be future work.

---

## Required checks

After backend code changes, run:

python manage.py check

If models change, run:

python manage.py makemigrations
python manage.py migrate

When logic is added or changed, add or update focused tests where practical.

At minimum, important logic should be tested for:

- permissions
- workflow validation
- decision engine behavior
- state transitions

---
## After finishing each milestone

After a milestone is completed and verified, update PROJECT_STATUS.md.
When moving to the next milestone, update CURRENT_MILESTONE.md.
Do not edit IMPLEMENTATION_ROADMAP.md unless explicitly instructed.
---

## Output expectations

After completing a task, summarize clearly:

- what changed
- which files/modules were affected
- what checks/tests were run
- any assumptions made
- what remains next, if relevant

Do not over-explain obvious code. Keep summaries concise and factual.