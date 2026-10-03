from patients.models import PatientProfile

from .text import normalize


DEFAULT_SUGGESTIONS = [
    "How many follow-up cases does patient1 have?",
    "Show appointments for patient1",
    "Show unresolved escalations",
    "Show active workflows",
    "Show recent audit events",
]

PATIENT_SUGGESTIONS = [
    "How many follow-up cases does {patient} have?",
    "Show latest follow-up case for {patient}",
    "Show appointments for {patient}",
    "Show escalations for {patient}",
]

APPOINTMENT_SUGGESTIONS = [
    "How many appointments are scheduled today?",
    "Show appointments for {patient}",
    "Show appointment-required cases without scheduled appointment",
    "Show completed appointments today",
    "Show cancelled appointments",
]

ESCALATION_SUGGESTIONS = [
    "Show unresolved urgent escalations",
    "Show unresolved escalations",
    "Show waiting-for-patient escalations",
    "Show escalations for {patient}",
]

WORKFLOW_SUGGESTIONS = [
    "Show active workflows",
    "How many active workflows are there?",
    "Show workflow status counts",
    "Show Post-Extraction workflow status",
]

AUDIT_SUGGESTIONS = [
    "Show recent audit events",
    "Show appointment updates today",
    "Who activated workflow 1?",
    "Show actions admin1 performed today",
]

REPORT_SUGGESTIONS = [
    "Show high-risk reports today",
    "Show latest high-risk reports",
    "Show reports that produced escalation",
    "Show low-risk reports today",
]


def suggestions_for(query):
    normalized = normalize(query or "")
    patient = matching_patient(normalized)
    patient_name = patient.user.username if patient else default_patient_name()

    if patient:
        return render_suggestions(PATIENT_SUGGESTIONS, patient_name)

    if not normalized:
        return render_suggestions(DEFAULT_SUGGESTIONS, patient_name)

    suggestions = []

    if has_any(normalized, ["patient", "patients", "profile", "profiles"]):
        suggestions.extend(PATIENT_SUGGESTIONS)
    if has_any(normalized, ["appoint", "schedule", "scheduled", "today"]):
        suggestions.extend(APPOINTMENT_SUGGESTIONS)
    if has_any(normalized, ["escalation", "urgent", "staff", "review"]):
        suggestions.extend(ESCALATION_SUGGESTIONS)
    if has_any(normalized, ["workflow", "active workflow", "post extraction"]):
        suggestions.extend(WORKFLOW_SUGGESTIONS)
    if has_any(normalized, ["audit", "history", "event", "events", "actor", "admin"]):
        suggestions.extend(AUDIT_SUGGESTIONS)
    if has_any(normalized, ["risk", "high risk", "urgent", "report", "reports"]):
        suggestions.extend(REPORT_SUGGESTIONS)

    if not suggestions:
        suggestions = DEFAULT_SUGGESTIONS

    return render_suggestions(suggestions, patient_name)


def render_suggestions(templates, patient_name):
    rendered = []
    seen = set()
    for template in templates:
        item = template.format(patient=patient_name)
        if item not in seen:
            rendered.append(item)
            seen.add(item)
        if len(rendered) >= 6:
            break
    return rendered


def matching_patient(normalized):
    for profile in PatientProfile.objects.select_related("user"):
        username = normalize(profile.user.username)
        full_name = normalize(profile.user.get_full_name()) if profile.user.get_full_name() else ""
        if username and username in normalized:
            return profile
        if full_name and full_name in normalized:
            return profile
    return None


def default_patient_name():
    profile = PatientProfile.objects.select_related("user").order_by("user__username", "id").first()
    if not profile:
        return "patient1"
    return profile.user.username


def has_any(normalized, words):
    return any(word in normalized for word in words)
