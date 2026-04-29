from patients.models import PatientProfile

from .query_router import normalize


DEFAULT_SUGGESTIONS = [
    "How many appointments are scheduled today?",
    "Show unresolved urgent escalations",
    "Show active workflows",
    "Show recent audit events",
    "Show appointment-required cases without scheduled appointment",
]


def suggestions_for(query):
    normalized = normalize(query or "")
    patient = matching_patient(normalized)

    if patient:
        username = patient.user.username
        return [
            f"How many follow-up cases does {username} have?",
            f"Show latest follow-up case for {username}",
            f"Show appointments for {username}",
            f"Show escalations for {username}",
            f"Show reports for {username}'s latest case",
        ]

    if not normalized:
        return DEFAULT_SUGGESTIONS

    if "appoint" in normalized or "schedule" in normalized:
        return [
            "How many appointments are scheduled today?",
            "Show today’s appointments",
            patient_suggestion("Show appointments for {patient}"),
            "Show appointment-required cases without scheduled appointment",
            "Show cancelled appointments",
        ]

    if "urgent" in normalized:
        return [
            "Show unresolved urgent escalations",
            "How many urgent reports this week?",
            "Show appointment-required cases without scheduled appointment",
        ]

    if "escalation" in normalized or "review" in normalized:
        return [
            "Show unresolved escalations",
            "Show unresolved urgent escalations",
            "Which escalations are waiting for patient?",
            patient_suggestion("Show escalations for {patient}"),
        ]

    if "workflow" in normalized:
        return [
            "Which workflows are active?",
            "How many active workflows exist?",
            "Show workflows by status",
            "Which workflow has most escalations?",
            "Show Post-Extraction workflow status",
        ]

    if "audit" in normalized or "trace" in normalized:
        return [
            "Show recent audit events",
            "Show audit trace for case 1",
            "Show appointment updates today",
        ]

    if "risk" in normalized or "report" in normalized:
        return [
            "How many high-risk reports today?",
            "How many urgent reports this week?",
            "Show latest high-risk reports",
            "Which reports produced escalation?",
        ]

    return DEFAULT_SUGGESTIONS


def matching_patient(normalized):
    for profile in PatientProfile.objects.select_related("user"):
        username = normalize(profile.user.username)
        full_name = normalize(profile.user.get_full_name()) if profile.user.get_full_name() else ""
        if username and username in normalized:
            return profile
        if full_name and full_name in normalized:
            return profile
    return None


def patient_suggestion(template):
    profile = PatientProfile.objects.select_related("user").order_by("user__username", "id").first()
    if not profile:
        return template.format(patient="patient1")
    return template.format(patient=profile.user.username)
