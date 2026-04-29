import re

from django.contrib.auth import get_user_model

from patients.models import PatientProfile
from workflows.models import RiskLevel

from . import query_handlers as handlers


def execute_query(question):
    normalized = normalize(question)

    if asks_for_diagnosis(normalized):
        return handlers.response(
            answer=(
                "I cannot diagnose or infer medical conditions. I can show recorded reports, "
                "risk assessments, escalations, and appointment status."
            ),
            intent="clinical_question_blocked",
            display_type="unsupported",
            suggested_followups=[
                "Show latest high-risk reports",
                "Show unresolved escalations",
                "Show reports for patient1's latest case",
            ],
        )

    patient = find_patient(normalized)
    patient_candidate = extract_patient_candidate(normalized)

    if has_all(normalized, ["appointment", "update", "today"]):
        return handlers.appointment_updates_today()

    if "follow up case" in normalized or "follow-up case" in normalized or "case" in normalized:
        if has_any(normalized, ["how many", "count"]) and "case" in normalized:
            return with_patient(patient, patient_candidate, handlers.count_follow_up_cases_for_patient)
        if has_all(normalized, ["status", "latest", "case"]):
            return with_patient(patient, patient_candidate, handlers.latest_case_status_for_patient)
        if has_all(normalized, ["latest", "case"]) and "report" not in normalized:
            return with_patient(patient, patient_candidate, handlers.latest_follow_up_case_for_patient)
        if has_all(normalized, ["active", "case"]):
            return with_patient(patient, patient_candidate, handlers.active_cases_for_patient)
        if has_all(normalized, ["report", "latest", "case"]):
            return with_patient(patient, patient_candidate, handlers.reports_for_latest_case)

    if is_appointment_question(normalized):
        if has_all(normalized, ["how many", "scheduled", "today"]):
            return handlers.appointments_scheduled_today()
        if has_any(normalized, ["today", "todays", "today's"]) and not has_any(
            normalized, ["completed", "update"]
        ):
            return handlers.todays_appointments()
        if has_all(normalized, ["completed", "today"]):
            return handlers.completed_appointments_today()
        if "cancelled" in normalized or "canceled" in normalized:
            return handlers.cancelled_appointments()
        if has_all(normalized, ["without", "scheduled"]) or "appointment required" in normalized:
            return handlers.appointment_required_without_scheduled()
        if patient or patient_candidate:
            return with_patient(patient, patient_candidate, handlers.appointments_for_patient)

    if is_report_or_risk_question(normalized):
        if has_all(normalized, ["high", "today"]):
            return handlers.risk_reports_today(RiskLevel.HIGH)
        if has_all(normalized, ["urgent", "week"]):
            return handlers.urgent_reports_this_week()
        if has_all(normalized, ["latest", "high"]):
            return handlers.latest_high_risk_reports()
        if has_all(normalized, ["produced", "escalation"]):
            return handlers.reports_produced_escalation()
        if has_all(normalized, ["low", "today"]):
            return handlers.risk_reports_today(RiskLevel.LOW)

    if is_escalation_question(normalized):
        if "waiting for patient" in normalized:
            return handlers.waiting_for_patient_escalations()
        if has_any(normalized, ["last responded", "last response", "responded"]):
            return with_patient(patient, patient_candidate, handlers.last_staff_response_for_patient)
        if patient or patient_candidate:
            return with_patient(patient, patient_candidate, handlers.escalations_for_patient)
        if "urgent" in normalized:
            return handlers.unresolved_escalations(urgent_only=True)
        if "unresolved" in normalized or "open" in normalized:
            return handlers.unresolved_escalations()

    if is_workflow_question(normalized):
        workflow_id = extract_id_after(normalized, "workflow")
        if has_all(normalized, ["who", "activated"]) and workflow_id:
            return handlers.workflow_activation_actor(workflow_id)
        if has_all(normalized, ["how many", "active"]):
            return handlers.active_workflows(count_only=True)
        if "active" in normalized:
            return handlers.active_workflows()
        if "by status" in normalized:
            return handlers.workflows_by_status()
        if has_all(normalized, ["most", "escalation"]):
            return handlers.workflow_with_most_escalations()
        if "post extraction" in normalized or "post-extraction" in normalized:
            return handlers.post_extraction_workflow_status()

    if is_audit_question(normalized):
        case_id = extract_id_after(normalized, "case")
        workflow_id = extract_id_after(normalized, "workflow")
        actor = find_user(normalized)
        if "trace" in normalized and case_id:
            return handlers.audit_trace_for_case(case_id)
        if has_all(normalized, ["who", "activated"]) and workflow_id:
            return handlers.workflow_activation_actor(workflow_id)
        if actor and "today" in normalized:
            return handlers.actions_by_actor_today(actor)
        if has_all(normalized, ["appointment", "update", "today"]):
            return handlers.appointment_updates_today()
        if "recent" in normalized or "audit" in normalized:
            return handlers.recent_audit_events()

    return handlers.unsupported_response()


def normalize(value):
    normalized = value.lower()
    normalized = normalized.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    normalized = normalized.replace("follow-up", "follow up")
    normalized = normalized.replace("post-extraction", "post extraction")
    normalized = re.sub(r"[^a-z0-9_#'\s-]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def asks_for_diagnosis(normalized):
    return has_any(
        normalized,
        [
            "diagnose",
            "diagnosis",
            "infection",
            "prescribe",
            "prescription",
            "medicine",
            "medication",
        ],
    )


def is_appointment_question(normalized):
    return "appoint" in normalized or "scheduled appointment" in normalized


def is_escalation_question(normalized):
    return "escalation" in normalized or "urgent" in normalized or "waiting for patient" in normalized


def is_workflow_question(normalized):
    return "workflow" in normalized or "post extraction" in normalized


def is_report_or_risk_question(normalized):
    return "report" in normalized or "risk" in normalized


def is_audit_question(normalized):
    return "audit" in normalized or "trace" in normalized or "actions did" in normalized or "activated workflow" in normalized


def has_any(normalized, words):
    return any(word in normalized for word in words)


def has_all(normalized, words):
    return all(word in normalized for word in words)


def with_patient(patient, candidate, handler):
    if not patient:
        return handlers.patient_not_found_response(candidate or "the requested patient")
    return handler(patient)


def find_patient(normalized):
    profiles = PatientProfile.objects.select_related("user").all()
    for profile in profiles:
        candidates = patient_name_candidates(profile)
        if any(candidate and candidate in normalized for candidate in candidates):
            return profile
    return None


def patient_name_candidates(profile):
    user = profile.user
    candidates = [
        normalize(user.username),
        normalize(user.get_full_name()) if user.get_full_name() else "",
        normalize(user.first_name) if user.first_name else "",
        normalize(user.last_name) if user.last_name else "",
    ]
    return [candidate for candidate in candidates if candidate]


def extract_patient_candidate(normalized):
    patterns = [
        r"for ([a-z0-9_-]+)",
        r"does ([a-z0-9_-]+) have",
        r"for ([a-z0-9_-]+)'s",
        r"to ([a-z0-9_-]+)",
    ]
    ignored = {
        "patient",
        "patients",
        "case",
        "cases",
        "today",
        "workflow",
        "appointment",
        "appointments",
    }
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            candidate = match.group(1)
            if candidate not in ignored:
                return candidate
    return ""


def extract_id_after(normalized, label):
    match = re.search(rf"{label}\s+#?(\d+)", normalized)
    if not match:
        return None
    return int(match.group(1))


def find_user(normalized):
    User = get_user_model()
    for user in User.objects.all():
        if normalize(user.username) in normalized:
            return user
    return None
