DentCare-MDE
============

DentCare-MDE is a clinical workflow system for structured patient follow-up and decision support. It converts care processes into explicit, auditable models that govern monitoring, symptom intake, risk evaluation, and escalation decisions. By combining rule-based reasoning with traceable operational workflows, the system strengthens consistency, accountability, and staff oversight across the care journey.


.. |Python| image:: https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white
   :alt: Python

.. |Django| image:: https://img.shields.io/badge/Django-6.0.4-092E20?logo=django&logoColor=white
   :alt: Django

.. |DRF| image:: https://img.shields.io/badge/Django_REST_Framework-API-A30000
   :alt: Django REST Framework

.. |React| image:: https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black
   :alt: React

.. |Vite| image:: https://img.shields.io/badge/Vite-Frontend-646CFF?logo=vite&logoColor=white
   :alt: Vite


|Python| |Django| |DRF| |React| |Vite|


Core Capabilities
=================

* Model-driven post-extraction follow-up workflows
* Internal workflow DSL with human-readable model previews
* Static workflow validation before activation
* Dynamic patient report forms generated from workflow definitions
* Stage-specific deterministic risk assessment
* Bounded template-based patient guidance
* Automatic escalation of ``HIGH`` and ``URGENT`` reports
* Staff-controlled appointment management
* Global validation of patient-facing recommendation text
* Audit logging and execution traceability
* Read-only Admin Intelligence for operational queries


Domain Model
============

The workflow is the central domain artifact. It defines both the information collected from patients and the rules used to interpret that information.

``TreatmentWorkflow``
   Root follow-up model containing the complete workflow definition.

``CareStage``
   Defines a time range based on the number of days after treatment.

``SymptomDefinition``
   Defines the patient-report fields generated for a workflow.

``SymptomRule``
   Contains deterministic conditions used during risk evaluation.

``AIAdviceBoundary``
   Defines constraints applied to bounded patient-facing guidance.

``EscalationRule``
   Defines conditions and routing behavior for staff review.

At runtime, a ``FollowUpCase`` links a patient and treatment date to an active workflow. Submitted ``SymptomReport`` data is evaluated through that workflow and produces traceable runtime artifacts including risk assessments, guidance, escalations, and appointments.


Model-Driven Execution
======================

The execution pipeline is deterministic and stage-aware:

.. code-block:: text

   TreatmentWorkflow + FollowUpCase + SymptomReport
                  ↓
          Determine CareStage
                  ↓
        Evaluate SymptomRules
                  ↓
        Persist RiskAssessment
                  ↓
     Generate bounded guidance
                  ↓
     Escalate HIGH / URGENT
                  ↓
             Staff review
                  ↓
           Appointment
                  ↓
              AuditLog

The workflow therefore controls both the structure of patient input and the interpretation of that input.


Workflow Validation
===================

Before activation, workflows undergo structural and semantic validation.

Validation includes:

* valid and non-overlapping care-stage ranges;
* unique symptom definitions within a workflow;
* supported rule operators;
* references to known report fields;
* escalation support for high-risk and urgent rules;
* explicit restrictions on unsafe patient-facing topics such as diagnosis and prescription.

This prevents invalid workflow definitions from entering runtime execution.


Decision & Escalation Logic
===========================

Risk Assessment
---------------

For each submitted report, the decision engine:

#. calculates the number of days since treatment;
#. identifies the matching ``CareStage``;
#. evaluates rules applicable to that stage;
#. determines the highest-priority matching risk level;
#. persists the result as a ``RiskAssessment``.


Patient Guidance
----------------

Patient-facing guidance is generated from validated templates and constrained by workflow-defined advice boundaries and global safety policies.


Escalation
----------

``HIGH`` and ``URGENT`` outcomes automatically create escalation cases for staff review.

Appointments are never created autonomously by the decision engine. They are created or updated by staff after reviewing the patient case.


Architecture
============

The backend separates workflow modelling, patient reporting, rule evaluation, escalation handling, auditing, and clinical-safety responsibilities into dedicated application modules.

Repository Structure
--------------------

.. code-block:: text

   MDE---Dent/
   ├── backend/
   │   ├── accounts/             Authentication, roles and permissions
   │   ├── workflows/            Workflow DSL, validation and lifecycle
   │   ├── patients/             Patient profiles and follow-up cases
   │   ├── reports/              Structured symptom-report capture
   │   ├── decision_engine/      Rule evaluation and risk assessment
   │   ├── ai_support/           Bounded patient-guidance generation
   │   ├── escalations/          Staff escalation handling
   │   ├── appointments/         Appointment coordination
   │   ├── audit/                Action logging and traceability
   │   ├── admin_intelligence/   Read-only operational queries
   │   └── clinical_safety/      Recommendation-safety policies
   │
   ├── frontend/
   │   └── src/
   │       ├── pages/            Role-based application views
   │       ├── components/       Reusable UI components
   │       ├── api/              API client modules
   │       ├── auth/             Authentication context and hooks
   │       └── utils/            Formatting and data utilities
   │
   └── requirements.txt


Technology Stack
================

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Layer
     - Technology
   * - Backend
     - Python 3.x, Django 6.0.4, Django REST Framework
   * - Authentication
     - Simple JWT
   * - Database
     - SQLite for development, accessed through Django ORM
   * - Frontend
     - React 19, Vite, React Router
   * - Decision Logic
     - JSON-based rule conditions with expression validation


User Roles
==========

Administrator
-------------

Administrators create and manage workflows, validate and activate models, create patient profiles, assign workflows to follow-up cases, review operational records, and execute read-only Admin Intelligence queries.


Dentist / Staff
---------------

Clinical staff review patient reports and risk assessments, handle escalation cases, provide clinical responses, and manage appointments.


Patient
-------

Patients access assigned follow-up cases, submit structured symptom reports, receive bounded guidance, and track staff responses, escalation state, and appointment information.


Safety & Human Oversight
========================

DentCare-MDE is designed as a clinical-support workflow system rather than an autonomous diagnosis or prescription system.

Its automated behavior is deliberately constrained:

* risk assessment is deterministic and rule-based;
* patient guidance is template-based rather than open-ended;
* workflow boundaries restrict unsafe clinical language;
* patient-facing recommendations are subject to global safety-policy validation;
* ``HIGH`` and ``URGENT`` cases are routed to staff;
* appointment decisions remain staff-controlled;
* uploaded images are supporting evidence for staff review and are not autonomously interpreted;
* dental professionals retain responsibility for clinical decisions.

The architecture favors explicit, inspectable logic over opaque decision-making.


Traceability
============

Workflow definitions, submitted reports, rule evaluations, risk assessments, guidance, escalations, appointments, and staff actions remain connected through the runtime and audit model.

This makes decision paths inspectable and allows an outcome to be traced back to the workflow state and patient data that produced it.


Getting Started
===============

Prerequisites
-------------

.. code-block:: console

   Python 3.10+
   Node.js 16+
   npm
   Git


Clone the Repository
--------------------

.. code-block:: console

   $ git clone https://github.com/marildoC/MDE---Dent.git
   $ cd MDE---Dent


Backend
-------

Create a virtual environment:

.. code-block:: console

   $ python -m venv venv

Activate it on Linux or macOS:

.. code-block:: console

   $ source venv/bin/activate

On Windows:

.. code-block:: console

   > venv\Scripts\activate

Install the backend dependencies:

.. code-block:: console

   $ pip install -r requirements.txt

Apply database migrations:

.. code-block:: console

   $ cd backend
   $ python manage.py migrate

Start the Django development server:

.. code-block:: console

   $ python manage.py runserver


Frontend
--------

From a second terminal:

.. code-block:: console

   $ cd frontend
   $ npm install
   $ npm run dev


API Configuration
-----------------

By default, the frontend communicates with the Django API at:

.. code-block:: text

   http://localhost:8000/api

A different API endpoint can be configured through:

.. code-block:: console

   $ export VITE_API_BASE_URL=https://your-api-url.com/api


Development Checks
==================

Backend
-------

Check the Django configuration:

.. code-block:: console

   $ cd backend
   $ python manage.py check

Run backend tests:

.. code-block:: console

   $ python manage.py test


Frontend
--------

Run the linter:

.. code-block:: console

   $ cd frontend
   $ npm run lint

Create a production build:

.. code-block:: console

   $ npm run build
