from django.core.exceptions import ValidationError
from django.db import transaction

from audit import actions as audit_actions
from audit.services import record_audit
from patients.lifecycle import sync_follow_up_case_from_escalation
from workflows.models import RiskLevel

from .models import EscalationCase, EscalationStatus

ALLOWED_ESCALATION_TRANSITIONS = {
    EscalationStatus.NEW: {
        EscalationStatus.IN_REVIEW,
        EscalationStatus.APPOINTMENT_REQUIRED,
        EscalationStatus.RESOLVED,
    },
    EscalationStatus.IN_REVIEW: {
        EscalationStatus.WAITING_FOR_PATIENT,
        EscalationStatus.APPOINTMENT_REQUIRED,
        EscalationStatus.RESOLVED,
    },
    EscalationStatus.WAITING_FOR_PATIENT: {
        EscalationStatus.IN_REVIEW,
        EscalationStatus.APPOINTMENT_REQUIRED,
        EscalationStatus.RESOLVED,
    },
    EscalationStatus.APPOINTMENT_REQUIRED: {EscalationStatus.RESOLVED},
    EscalationStatus.RESOLVED: {EscalationStatus.CLOSED},
    EscalationStatus.CLOSED: set(),
}


def validate_escalation_transition(current_status, next_status):
    if current_status == next_status:
        return

    allowed_next_statuses = ALLOWED_ESCALATION_TRANSITIONS.get(current_status, set())
    if next_status not in allowed_next_statuses:
        raise ValidationError(
            f"Escalation status cannot transition from {current_status} to {next_status}."
        )


def create_escalation_for_assessment(risk_assessment):
    if risk_assessment.risk_level not in {RiskLevel.HIGH, RiskLevel.URGENT}:
        return None

    try:
        return risk_assessment.escalation_case
    except EscalationCase.DoesNotExist:
        pass

    existing = EscalationCase.objects.filter(risk_assessment=risk_assessment).first()
    if existing:
        return existing

    with transaction.atomic():
        report = risk_assessment.report
        follow_up_case = report.follow_up_case
        escalation = EscalationCase.objects.create(
            risk_assessment=risk_assessment,
            report=report,
            follow_up_case=follow_up_case,
            patient=follow_up_case.patient,
            urgency=risk_assessment.risk_level,
            assigned_staff=follow_up_case.assigned_staff,
        )
        sync_follow_up_case_from_escalation(escalation)
        record_audit(
            None,
            audit_actions.ESCALATION_CREATED,
            escalation,
            {
                "risk_assessment_id": escalation.risk_assessment_id,
                "report_id": escalation.report_id,
                "follow_up_case_id": escalation.follow_up_case_id,
                "patient_id": escalation.patient_id,
                "urgency": escalation.urgency,
                "assigned_staff_id": escalation.assigned_staff_id,
            },
        )
    return escalation


def update_escalation_status(escalation, status):
    previous_status = escalation.status
    validate_escalation_transition(escalation.status, status)
    with transaction.atomic():
        escalation.status = status
        escalation.mark_resolved_timestamp()
        escalation.save(update_fields=["status", "resolved_at", "updated_at"])
        sync_follow_up_case_from_escalation(escalation)
        if previous_status != status:
            record_audit(
                None,
                audit_actions.ESCALATION_UPDATED,
                escalation,
                {
                    "previous_status": previous_status,
                    "new_status": status,
                    "urgency": escalation.urgency,
                    "assigned_staff_id": escalation.assigned_staff_id,
                },
            )
    return escalation
