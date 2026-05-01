# DentCare-MDE Documentation

DentCare-MDE is a model-driven dental follow-up system. Its purpose is not to act as a generic dental chatbot, autonomous diagnostic assistant, or broad clinic-management platform. Its purpose is to let a clinic define a structured recovery workflow, validate that workflow before use, assign it to a patient, collect follow-up symptom reports, execute deterministic decision rules, produce bounded advice or staff escalation, guide appointment priority, and preserve an audit trace of the resulting clinical support process.

The central artifact is the workflow model. The runtime system behaves according to workflow data: care stages, symptom definitions, structured rules, escalation requirements, advice boundaries, and lifecycle constraints. The system's intelligence comes from transforming validated workflow structure into controlled operational behavior.

## Section 1: The Technical Ecosystem

### Core Stack

DentCare-MDE is implemented as a web-based full-stack application with a Django REST backend and a React frontend.

The backend is built with Python and Django. Django provides the application framework, ORM, model validation, administrative interface, request routing, authentication integration, persistence model, and lifecycle hooks. Django REST Framework exposes the domain as authenticated JSON APIs. JSON Web Tokens provide stateless API authentication, while role-aware permission classes constrain each API surface to the correct actor type: patient, dentist/staff, or administrator.

The persistence layer uses Django's relational ORM over SQLite for local development. The domain is relational because the system depends on durable links between workflow definitions, patient follow-up cases, symptom reports, risk assessments, advice messages, escalation cases, appointments, and audit logs. JSON fields are used where the system needs controlled structured data inside a relational entity, especially for workflow rule conditions and persistent decision traces.

The frontend is built with JavaScript, React, Vite, and React Router. React renders the role-specific user experience, Vite provides development and production bundling, and React Router controls navigation between authenticated work areas. Browser-side API modules communicate with the backend over HTTP using JSON payloads and bearer tokens.

The primary API style is REST. The frontend does not directly access persistence. It sends authenticated requests to the backend, and the backend returns serialized domain state shaped for the current role and workflow stage. CORS allows the local React application to communicate with the local Django API during development.

The system also includes a bounded Admin Intelligence capability. This is not an LLM diagnosis layer. It is a deterministic operational query interface that routes supported administrative questions to known database queries about patients, cases, reports, risk assessments, escalations, appointments, workflows, and audit events. Clinical diagnosis and prescription-like questions are explicitly blocked.

### Infrastructure Logic

The system is organized around a clean separation of responsibilities:

- The browser owns interaction, navigation, form submission, and presentation.
- The REST API owns authentication, authorization, validation, serialization, and state mutation.
- The domain services own business behavior such as workflow validation, rule evaluation, advice creation, escalation creation, appointment priority handling, lifecycle synchronization, and audit recording.
- The database owns durable state and the historical trace of actions.

At runtime, the React frontend authenticates a user and stores access credentials locally in the browser. Every protected request includes the JWT bearer token. Django REST Framework validates that token, resolves the authenticated user, applies role permissions, validates submitted data, performs domain operations, persists results, and returns the resulting state to the frontend.

The backend's infrastructure logic is intentionally synchronous for version 1. A symptom report submission is not placed onto an external queue. Instead, report creation, deterministic assessment, advice generation, escalation creation when required, lifecycle synchronization, and audit logging are performed as a direct downstream chain from the submitted request. This keeps the model-driven execution path inspectable, testable, and aligned with the current scope.

The frontend then refreshes or displays the resulting state: the patient sees the report outcome and bounded advice; staff see escalation and appointment work queues; administrators see workflow lifecycle controls and audit history. The cohesion comes from the persistent data model: every downstream object points back to the originating workflow-controlled patient case and symptom report.

## Section 2: The End-to-End Narrative: The Life of a Request

### Activation Begins With a Model

The system begins before any patient submits symptoms. An administrator defines a treatment workflow for a focused clinical follow-up scenario, currently Post-Extraction Follow-Up. The workflow expresses the expected recovery period as care stages, defines the symptoms that patients can report, describes structured rule conditions, attaches risk levels and recommended actions to those rules, defines escalation behavior for high-risk outcomes, and sets safety boundaries for patient-facing advice.

This model is not merely descriptive. It is the source of runtime behavior. A care stage determines which rules are eligible on a given recovery day. Symptom definitions constrain the fields a rule may reference. Structured conditions determine whether a report matches a clinical support pattern. Risk levels determine severity ordering. Recommended actions determine whether the patient continues monitoring, receives contact guidance, or moves into staff review. Appointment priority is inherited from the decision context rather than guessed manually. Advice boundaries prevent the patient-facing layer from becoming a diagnosis or prescription mechanism.

Before the workflow can affect patients, the system validates it. Validation acts as the static semantics of the model-driven system. It checks that the workflow has usable stages, symptoms, and rules; that care stages have valid non-overlapping day ranges; that rule conditions use the allowed JSON shape; that rule fields refer to known symptom or report fields; that high and urgent rules have escalation support; that serious rules cannot be handled only through patient advice; that advice boundaries forbid diagnosis and prescription; and that escalation behavior includes appointment priority.

Only after validation can the workflow become active. This lifecycle matters because active workflows are assignable to patients and therefore become part of real follow-up execution. Draft workflows can be shaped, validated workflows have passed static checks, active workflows drive patient care support, and archived workflows are no longer assignable.

### Patient Assignment Converts the Model Into a Runtime Case

Once a workflow is active, staff or administrators can assign it to a patient by creating a follow-up case. This is the point where the abstract workflow becomes a concrete recovery process. The follow-up case binds together a patient, an active workflow, a treatment date, assigned staff context, and a lifecycle status.

The treatment date is important because the system uses it to derive the current day after treatment. That day places the patient inside the workflow's staged recovery model. A report on day 1 and a report on day 5 may contain the same symptom values, but the active care stage can make those values mean different things operationally because different rules may apply.

The case also becomes the state container for the patient's follow-up lifecycle. It starts in an actionable state, can move through monitoring or advice-provided states, can become escalated when the decision engine detects high risk, can become appointment-required when staff or appointment handling requires it, and can later resolve or close. Terminal cases block further symptom reporting so the system does not continue generating decisions against a completed process.

### Data Entry: The Symptom Report

The main runtime request begins when a patient submits a symptom report. The patient reports controlled symptom values such as pain level, swelling, bleeding, fever, bad smell or taste, notes, and optional supporting image evidence. The image is evidence for staff review only; it is not used for AI diagnosis or autonomous clinical interpretation.

When the request reaches the backend, the system first verifies identity and ownership. Only a patient can submit a report, and the report must belong to that patient's own follow-up case. The case must be in a reportable lifecycle state. The submitted values are validated, the report is saved, and the day after treatment is derived from the case's treatment date rather than trusted as arbitrary user input.

At this moment the system has received new data, but it has not yet produced clinical support behavior. The saved report is the input to the decision engine.

### Transformation: Deterministic Decision Engine Execution

The decision engine performs the execution semantics of the workflow model. It transforms a symptom report into a persistent risk assessment by following an explicit sequence.

First, it loads the report with its follow-up case and assigned workflow. It detects the current care stage by comparing the report's day after treatment against the workflow's staged day ranges. If no care stage matches, the system takes a conservative path: it produces a warning-level assessment that recommends contacting the clinic because the model cannot confidently place the report inside a defined recovery stage.

If a care stage is found, the engine selects the rules attached to that stage. Each rule contains structured condition data rather than executable code. The engine validates the condition shape, then evaluates logical groups such as `all` and `any`. Each condition leaf compares a controlled report field against a value using a small allowed operator set: equality, inequality, greater-than, greater-than-or-equal, less-than, less-than-or-equal, and membership.

The engine never evaluates raw code and never asks an AI model to decide risk. It compares saved report values to workflow-defined rule data. Unknown fields, invalid condition shapes, and type mismatches fail safely rather than becoming executable behavior.

After evaluating all eligible rules, the engine chooses the highest severity match according to the configured order: LOW, WARNING, HIGH, URGENT. If no rule matches, the report becomes a low-risk monitoring outcome. If multiple rules match, the highest-risk rule controls the selected risk level, recommended action, and appointment priority, while the assessment trace still records the matched rules.

The result is persisted as a risk assessment. This assessment stores the detected stage, matched rule trace, risk level, recommended action, appointment priority, explanation, and timestamp. That persistence is essential: staff can inspect why the system acted, tests can verify the decision, audit tools can reconstruct the flow, and reporting can explain the model-to-behavior mapping.

### Output Branching: Advice, Escalation, Appointment, and Audit

Once a risk assessment exists, downstream outputs are created from it.

The advice module generates a patient-facing message from deterministic templates keyed by risk level. The advice explains what the decision means in safe language. It does not diagnose. It does not prescribe. It does not override the selected action. If the workflow includes an applicable advice boundary with a safe required disclaimer, the system appends that disclaimer. If a disclaimer contains unsafe terms such as diagnosis or prescription language, it is suppressed.

For low or warning outcomes, the system can stop at monitoring or contact guidance. The patient receives bounded advice and the case remains in a non-terminal follow-up state unless other lifecycle rules act on it.

For high or urgent outcomes, the escalation service creates a staff escalation case. The escalation links back to the report, risk assessment, follow-up case, and patient. Its urgency comes from the risk assessment. Its staff assignment follows the follow-up case context. Creating the escalation also synchronizes the follow-up case state so the patient case reflects that it now requires staff attention.

Staff can then review the escalation, inspect the report, inspect the detected stage, read the matched rule trace and assessment explanation, respond to the patient, request more information, mark appointment required, resolve the escalation, or close it through controlled state transitions.

When appointment handling is needed, an appointment record can be created from the escalation context. The appointment priority defaults from the risk assessment's appointment priority, falling back to urgent priority for urgent escalations or high priority for high-risk cases. The appointment does not replace staff judgment on scheduling time, but it prevents appointment urgency from being disconnected from workflow risk. Appointment status changes also synchronize the follow-up case lifecycle: non-cancelled appointment handling pushes the case toward appointment-required, and completed appointments resolve the linked follow-up case.

Every important step emits an audit record. Audit logging captures workflow activation, assignment, symptom reporting, risk assessment creation, advice creation, escalation creation or updates, appointment creation or updates, follow-up case state changes, and related operational events. Sensitive free-text fields are sanitized from audit details so the trace remains useful without unnecessarily exposing patient notes, images, advice text, or staff responses.

### System State and Internal Lifecycle

DentCare-MDE manages state through explicit persisted lifecycles rather than hidden implicit behavior.

Workflow state controls assignability. A workflow must move from draft to validated to active before it can be used in patient follow-up. Archived workflows are removed from assignment flow. Active workflow structures are protected from direct edits in the current implementation scope so runtime behavior remains stable.

Follow-up case state controls whether patients can continue reporting and how staff actions affect the case. Reportable states include active monitoring and escalation-related states. Resolved and closed cases are terminal for reporting. State transitions are validated so a case cannot jump arbitrarily from one lifecycle point to another.

Escalation state controls staff review. Escalations progress through new, in-review, waiting-for-patient, appointment-required, resolved, and closed states using allowed transitions. These changes feed back into the follow-up case, keeping the patient-level lifecycle aligned with staff workflow.

Appointment state controls scheduling progression. Appointments move through requested or priority-suggested states into scheduled, completed, or cancelled states. Completion resolves the follow-up case; cancellation does not falsely resolve the clinical follow-up.

Background-style processing is currently implemented as synchronous downstream processing inside the request lifecycle. A submitted symptom report immediately causes assessment, advice creation, escalation creation when required, case synchronization, and audit recording. This design avoids external worker infrastructure in version 1 while still preserving a clean internal pipeline. The system can later move selected downstream steps to background workers if deployment scale requires it, but the present behavior is direct, deterministic, and testable.

The Admin Intelligence layer has its own controlled lifecycle. It receives an administrative natural-language question, normalizes it, routes it to a supported operational query when possible, returns structured results such as summaries, cards, tables, timelines, evidence references, and suggested follow-ups, and refuses diagnosis or prescription questions. This gives administrators a higher-level operational lens over the same persisted system state without introducing autonomous clinical reasoning.

## Section 3: The Functional Philosophy

DentCare-MDE behaves like a workflow execution environment for dental follow-up, not like a free-form chatbot or conventional CRUD dashboard.

From above, the system begins with a clinic encoding a recovery process into a structured model. That model defines what a valid follow-up process looks like before it touches a patient. The clinic does not merely type guidance text; it defines stages, symptoms, rules, risk outcomes, advice boundaries, and escalation requirements. The system then validates that the model is complete and safe enough to activate. In model-driven terms, this validation layer prevents invalid runtime behavior by rejecting incomplete or unsafe models before they become executable.

Once activated, the workflow becomes the controlling source for patient follow-up. A patient case does not independently decide what symptoms mean. It points to the active workflow. A symptom report does not independently decide risk. It is interpreted in the context of the case, the treatment date, the detected care stage, and the structured rules attached to that stage.

The system's execution flow is intentionally chained. Authentication controls who can act. Role authorization controls what kind of action they can perform. Workflow lifecycle controls whether a model can be assigned. Case lifecycle controls whether a patient can report. Report validation controls whether submitted data is acceptable. Stage detection controls which rules are eligible. Rule evaluation controls the risk outcome. Risk severity ordering controls which matched rule wins. The selected risk controls advice, escalation, and appointment priority. Staff and appointment actions control later case transitions. Audit logging records the trail.

Each feature feeds the next feature. Workflow validation makes assignment trustworthy. Assignment gives reports a workflow context. Reports give the decision engine concrete input. The decision engine produces a persistent assessment. The assessment feeds advice. High and urgent assessments feed escalation. Escalation feeds staff review and appointment handling. Appointment completion feeds case resolution. Audit records connect the entire chain into an inspectable trace.

The patient-facing experience is therefore deliberately bounded. Patients can submit structured reports, view the status of their follow-up case, read safe advice consistent with the risk assessment, see escalation status when staff review is required, and see appointment updates. They are not given autonomous diagnoses. They are not told that an image has been interpreted by AI. They are not allowed to see other patients' cases or administrative audit history.

The staff experience is operational. Staff see escalated cases, urgency, patient context, submitted symptoms, supporting evidence, decision traces, explanations, previous reports, appointment context, and response controls. Their work is not replaced by the decision engine; it is prioritized and contextualized by it. The engine raises the case and explains why, while staff perform review, communication, appointment handling, and closure.

The administrative experience is model-governance oriented. Administrators manage the workflow model, validate and activate it, assign it into patient cases, review audit history, and ask supported operational questions through Admin Intelligence. The administrator's power is constrained by the same safety philosophy: the system can report operational facts and traces, but it does not become an unrestricted clinical reasoning agent.

The most important architectural principle is that risk is computed deterministically from structured workflow data. AI support, where present, is downstream and bounded. Advice is explanatory, not decisive. Escalation is driven by risk, not free text. Appointment priority follows the assessment, not manual guesswork. Audit trace follows important actions, not optional documentation habits.

This makes DentCare-MDE suitable for a narrow but complete version 1: Post-Extraction Follow-Up. The system favors one coherent, end-to-end, validated workflow over many shallow treatment categories. Its value comes from preserving the full loop:

workflow model -> workflow validation -> patient follow-up case -> symptom report -> deterministic decision -> bounded advice or escalation -> staff action -> appointment priority -> audit trace

That loop is the core behavior of the platform. Every subsystem exists to protect, execute, explain, or record that loop.
