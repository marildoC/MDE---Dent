DentCare-MDE
============

DentCare-MDE is a clinical workflow system for structured patient follow-up and decision support. It converts care processes into explicit, auditable models that govern monitoring, symptom intake, risk evaluation, and escalation decisions. By combining rule-based reasoning with traceable operational workflows, the system strengthens consistency, accountability, and staff oversight across the care journey.

---

Highlights
==========

* Internal workflow DSL for post-extraction follow-up models
* Static workflow validation before activation
* Dynamic patient report forms generated from workflow symptom definitions
* Deterministic risk assessment using stage-specific rules
* Bounded template-based patient guidance
* Automatic escalation for high-risk and urgent reports
* Staff-controlled appointment handling
* Global safety policy for patient-facing recommendation text
* Audit logging and model execution traceability
* Read-only Admin Intelligence for operational questions

---

Core Model
==========

The workflow model is the main domain artifact. It defines:

* ``TreatmentWorkflow`` — the root follow-up model
* ``CareStage`` — ranges based on day after treatment
* ``SymptomDefinition`` — entries used to generate patient report fields
* ``SymptomRule`` — conditions used for deterministic risk assessment
* ``AIAdviceBoundary`` — constraints for bounded patient guidance
* ``EscalationRule`` — entries for staff review routing

At runtime, a patient follow-up case connects a patient, a treatment date, and an active workflow. Submitted symptom reports are interpreted through that workflow, producing traceable runtime artifacts.

---

Model-Driven Execution
======================

The system operates through a clear, deterministic evaluation pipeline:

.. code-block:: text

   TreatmentWorkflow + FollowUpCase + SymptomReport
      ↓
      Detect CareStage (based on day after treatment)
      ↓
      Match SymptomRule conditions
      ↓
      Generate RiskAssessment
      ↓
      Create AdviceMessage (if applicable)
      ↓
      Escalate to staff (HIGH or URGENT risk)
      ↓
      Staff creates Appointment (if needed)
      ↓
      Log all actions to AuditLog

This flow makes clinical-support logic explicit and inspectable. The workflow controls both the structure of patient input and the interpretation of that input.

---

User Roles & Responsibilities
=============================

**Administrator**
   Creates and manages workflows, validates and activates models, creates patient profiles, assigns workflows to cases, reviews operational records, and executes admin intelligence queries.

**Dentist / Staff**
   Reviews patient reports, interprets risk assessments, manages escalation cases, provides clinical responses, and schedules appointments.

**Patient**
   Views assigned follow-up cases, submits structured symptom reports, receives guidance, and tracks staff responses, escalation status, and appointment information.

---

Key Capabilities
=================

Workflow Management
~~~~~~~~~~~~~~~~~~~

Administrators define care stages, symptoms, rules, advice boundaries, and escalation rules through an intuitive workflow editor. A generated DSL preview exposes the saved model in human-readable form.

Workflow Validation
~~~~~~~~~~~~~~~~~~~

Before activation, all workflows undergo rigorous structural and semantic validation:

* Care stages must exist with valid, non-overlapping day ranges
* Symptom definitions must be unique within the workflow
* Rule conditions must use supported operators and reference known fields
* High-risk and urgent rules must have corresponding escalation support
* Advice boundaries must explicitly forbid unsafe topics (diagnosis, prescription)

Patient Reporting
~~~~~~~~~~~~~~~~~

Patient report forms are dynamically generated from the assigned workflow's symptom definitions. Reports capture structured symptom values, optional clinical notes, and optional image evidence for staff review.

Decision Engine
~~~~~~~~~~~~~~~

The decision engine computes days since treatment, identifies the matching care stage, evaluates only that stage's applicable rules, and persists the highest-priority risk level as a ``RiskAssessment``.

Advice & Escalation
~~~~~~~~~~~~~~~~~~~

* Patient guidance is generated from validated templates and constrained by workflow advice boundaries
* High-risk and urgent outcomes automatically create staff escalation cases
* Appointments are created or updated by staff after clinical review, never automatically by the system

Traceability
~~~~~~~~~~~~

Comprehensive audit logging connects workflow definitions, patient reports, rule evaluations, risk assessments, advice messages, escalations, appointments, and staff actions into a complete decision trail.

---

Safety & Design Philosophy
===========================

**What This System Is**

DentCare-MDE is a clinical-support workflow system built on explicit, rule-based logic. It provides structured monitoring, data-driven escalation, and operational accountability.

**What This System Is Not**

This is not a diagnosis or prescription system. Dental professionals retain full clinical responsibility for patient care decisions.

**Core Constraints**

* Patient guidance is deterministic and template-based—never generative or open-ended
* Workflow advice boundaries restrict unsafe clinical language (diagnosis, prescription, medication)
* High-risk and urgent cases are escalated to staff for human review
* Appointment decisions remain entirely staff-controlled
* Uploaded images are supporting evidence for staff review only—never used for autonomous analysis
* All patient-facing recommendations are subject to global safety policy validation

---

System Architecture
===================

**Backend Stack**

.. code-block:: text

   backend/
   ├── accounts/             User authentication, role management, permissions
   ├── workflows/            Workflow DSL, validation, lifecycle, preview
   ├── patients/             Patient profiles and follow-up case management
   ├── reports/              Symptom report capture and validation
   ├── decision_engine/      Rule evaluation and risk assessment
   ├── ai_support/           Bounded advice generation
   ├── escalations/          Staff escalation case handling
   ├── appointments/         Appointment coordination and scheduling
   ├── audit/                Action logging and audit trail
   ├── admin_intelligence/   Read-only operational query interface
   └── clinical_safety/      Global recommendation safety policies

**Frontend Stack**

.. code-block:: text

   frontend/
   ├── src/
   │   ├── pages/            Role-based dashboards (patient, staff, admin)
   │   ├── components/       Reusable UI components
   │   ├── api/              API client modules for each service
   │   ├── auth/             Authentication context and hooks
   │   └── utils/            Display formatting and data utilities
   └── ...

**Technology Stack**

* **Backend:** Python 3.x, Django 6.0.4, Django REST Framework, Simple JWT
* **Database:** SQLite (development), supports production databases via Django ORM
* **Frontend:** React 19, Vite, React Router
* **Logic:** JSON-based rule conditions with full expression validation

---

Getting Started
===============

Prerequisites
~~~~~~~~~~~~~

* Python 3.10+
* Node.js 16+ (with npm)
* Git

Backend Setup
~~~~~~~~~~~~~

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/marildoC/MDE---Dent.git
   cd MDE---Dent

   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate          # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt

   # Run migrations
   cd backend
   python manage.py migrate

   # Start development server
   python manage.py runserver

Frontend Setup
~~~~~~~~~~~~~~

.. code-block:: bash

   # In a new terminal, from the project root
   cd frontend

   # Install dependencies
   npm install

   # Start development server (Vite)
   npm run dev

**API Configuration**

The frontend is configured to communicate with the Django API at ``http://localhost:8000/api``.

To use a different API URL, set the environment variable:

.. code-block:: bash

   export VITE_API_BASE_URL=https://your-api-url.com/api

---

Quality Assurance
=================

**Backend Checks**

.. code-block:: bash

   cd backend

   # Verify Django configuration
   python manage.py check

   # Run unit tests
   python manage.py test

**Frontend Checks**

.. code-block:: bash

   cd frontend

   # Lint code
   npm run lint

   # Build production bundle
   npm run build

---

Design Principles
=================

**Explicit Over Implicit**

DentCare-MDE treats clinical workflows as first-class domain objects. Care logic is always visible, defined, and subject to validation—never hidden or inferred.

**Auditable Over Opaque**

Every decision is logged with full context: which rule was matched, what data drove the assessment, who took action, and when. This creates a defensible audit trail for every patient interaction.

**Safe Over Autonomous**

The system deliberately constrains automated decision-making. Risk assessments are deterministic and rule-based; escalations are data-driven; clinical judgment remains the responsibility of qualified professionals. Human oversight is built into the architecture.

**Consistent Over Flexible**

By modeling care as explicit workflows, DentCare-MDE ensures that every patient receives the same quality of monitoring and assessment. Workflows can be refined over time, but once active, they execute consistently and predictably.

**Traceable Over Black-Box**

Every outcome can be explained by reference to defined logic. This enables continuous improvement, regulatory compliance, and clinician confidence in the system's behavior.

---

Philosophy & Intent
====================

DentCare-MDE exists to bring discipline, clarity, and accountability to clinical workflows. By modeling care as explicit, validated logic rather than improvisation or opacity, the system enables teams to:

* **Operate consistently** across all patients and cases
* **Escalate intelligently** based on data-driven criteria
* **Maintain transparency** through comprehensive audit trails
* **Improve over time** by refining validated workflows based on outcomes
* **Comply confidently** with clinical and regulatory standards

The result is safer patient monitoring, better-informed staff coordination, and workflows that teams can trust, understand, and defend.

---

License & Support
==================

This project is provided as-is for educational and clinical workflow management purposes.

For questions, issues, or contributions, please refer to the GitHub repository: `marildoC/MDE---Dent <https://github.com/marildoC/MDE---Dent>`_
