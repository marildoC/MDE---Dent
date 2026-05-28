DentCare-MDE
============

DentCare-MDE is a model-driven dental follow-up platform for structured
post-extraction monitoring. It allows clinics to define validated follow-up
workflows, assign them to patient cases, collect workflow-driven symptom
reports, evaluate recovery signals through deterministic rules, and escalate
risky outcomes to dental staff.

The system is centered on an executable workflow model. Instead of relying on
static forms or open-ended automated diagnosis, each active workflow defines the
care stages, symptom vocabulary, rule logic, advice boundaries, and escalation
policy used during runtime follow-up.

Highlights
----------

* Internal workflow DSL for post-extraction follow-up models.
* Static workflow validation before activation.
* Dynamic patient report forms generated from workflow symptom definitions.
* Deterministic risk assessment using stage-specific rules.
* Bounded template-based patient guidance.
* Automatic escalation for high-risk and urgent reports.
* Staff-controlled appointment handling.
* Global safety policy for patient-facing recommendation text.
* Audit logging and model execution traceability.
* Read-only Admin Intelligence for operational questions.

Core Model
----------

The workflow model is the main domain artifact. It defines:

* ``TreatmentWorkflow`` as the root follow-up model.
* ``CareStage`` ranges based on day after treatment.
* ``SymptomDefinition`` entries used to generate patient report fields.
* ``SymptomRule`` conditions used for deterministic risk assessment.
* ``AIAdviceBoundary`` constraints for bounded patient guidance.
* ``EscalationRule`` entries for staff review routing.

At runtime, a patient follow-up case connects a patient, a treatment date, and
an active workflow. Submitted symptom reports are interpreted through that
workflow, producing traceable runtime artifacts.

Model-Driven Execution
----------------------

::

   TreatmentWorkflow + FollowUpCase + SymptomReport
      -> detected CareStage
      -> matched SymptomRule
      -> RiskAssessment
      -> AdviceMessage
      -> EscalationCase for HIGH or URGENT risk
      -> staff-created Appointment
      -> AuditLog and model execution trace

This flow makes the clinical-support logic explicit and inspectable. The
workflow controls both the structure of patient input and the interpretation of
that input.

Primary User Roles
------------------

* Administrator: creates workflows, validates and activates models, creates
  patient profiles, assigns workflows, reviews records, and uses Admin
  Intelligence.
* Dentist or staff: reviews patient reports, risk assessments, escalation
  cases, staff responses, and appointments.
* Patient: views assigned follow-up cases, submits workflow-generated symptom
  reports, and sees guidance, staff responses, escalation status, and
  appointment information.

Key Capabilities
----------------

Workflow Management
~~~~~~~~~~~~~~~~~~~

Administrators define care stages, symptoms, rules, advice boundaries, and
escalation rules through the workflow editor. A generated DSL preview exposes
the saved model in a readable form.

Workflow Validation
~~~~~~~~~~~~~~~~~~~

Before activation, workflows are checked for structural and semantic validity:

* care stages must exist and use valid day ranges;
* symptom definitions must exist and use unique keys;
* rule conditions must use supported operators and known fields;
* high-risk and urgent rules must have escalation support;
* advice boundaries must forbid unsafe topics such as diagnosis and
  prescription.

Patient Reporting
~~~~~~~~~~~~~~~~~

Patient report forms are generated from the assigned workflow's symptom
definitions. Reports support structured symptom values, optional notes, and
optional supporting image evidence.

Decision Engine
~~~~~~~~~~~~~~~

The decision engine computes the day after treatment, detects the matching
care stage, evaluates only that stage's rules, and persists the highest
matching risk level as a ``RiskAssessment``.

Advice, Escalation, and Appointment Handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Advice is generated from controlled templates and workflow advice boundaries.
High-risk and urgent outcomes create staff escalation cases. Appointments are
created or updated by staff after review, not automatically by the risk engine.

Traceability
~~~~~~~~~~~~

Audit logs and model execution traces connect workflow definitions, patient
reports, rule evaluation, assessments, advice, escalations, appointments, and
staff actions.

Safety Boundaries
-----------------

DentCare-MDE is a clinical-support workflow system, not a diagnosis or
prescription system. Dental professionals remain responsible for clinical
judgment and patient care decisions.

The system enforces these boundaries:

* Patient guidance is deterministic and template-based.
* Workflow advice boundaries restrict diagnosis and prescription behavior.
* High-risk and urgent reports are escalated to staff.
* Appointment decisions remain staff-controlled.
* Uploaded images are supporting evidence for staff review and are not used for
  automated diagnosis.
* Global recommendation safety rules reject unsafe patient-facing medicine or
  dosage instructions in workflow guidance and staff responses.

Architecture
------------

The repository is organized as a full-stack web application:

::

   backend/
      accounts/             authentication, users, roles
      workflows/            workflow DSL model, validation, lifecycle, preview
      patients/             patient profiles and follow-up cases
      reports/              symptom reports and report validation
      decision_engine/      deterministic workflow interpretation
      ai_support/           bounded advice generation
      escalations/          staff escalation handling
      appointments/         staff-controlled appointments
      audit/                traceability and audit records
      admin_intelligence/   read-only operational querying
      clinical_safety/      global recommendation safety policy

   frontend/
      src/                  React application, pages, API clients, utilities

Technology Stack
----------------

* Python, Django, Django REST Framework
* Django ORM and relational persistence
* Simple JWT authentication
* React, Vite, React Router
* Structured JSON rule conditions

Local Development
-----------------

Backend:

::

   py -3.12 -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   cd backend
   python manage.py migrate
   python manage.py runserver

Frontend:

::

   cd frontend
   npm install
   npm run dev

The frontend uses ``http://localhost:8000/api`` by default. Set
``VITE_API_BASE_URL`` when the API is served from another URL.

Verification
------------

Backend checks:

::

   cd backend
   python manage.py check
   python manage.py test

Frontend checks:

::

   cd frontend
   npm run build

Notes
-----

The project intentionally keeps clinical logic bounded and explainable. The
workflow model defines what can be collected and how reports are assessed, but
the system does not issue diagnoses, prescribe medication, or replace dental
staff review.
