from django.core.exceptions import ValidationError
from django.db import transaction

from audit import actions as audit_actions
from audit.services import record_audit
from escalations.models import EscalationStatus
from escalations.services import update_escalation_status
from patients.lifecycle import sync_follow_up_case_from_appointment
from workflows.models import AppointmentPriority, RiskLevel

from .models import Appointment, AppointmentStatus

ALLOWED_APPOINTMENT_TRANSITIONS = {
    AppointmentStatus.REQUESTED: {
        AppointmentStatus.SCHEDULED,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.PRIORITY_SUGGESTED: {
        AppointmentStatus.SCHEDULED,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.SCHEDULED: {
        AppointmentStatus.COMPLETED,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.COMPLETED: set(),
    AppointmentStatus.CANCELLED: set(),
}


def validate_appointment_transition(current_status, next_status):
    if current_status == next_status:
        return

    allowed_next_statuses = ALLOWED_APPOINTMENT_TRANSITIONS.get(current_status, set())
    if next_status not in allowed_next_statuses:
        raise ValidationError(
            f"Appointment status cannot transition from {current_status} to {next_status}."
        )


def default_priority_for_escalation(escalation_case):
    priority = escalation_case.risk_assessment.appointment_priority
    if priority and priority != AppointmentPriority.NONE:
        return priority
    if escalation_case.urgency == RiskLevel.URGENT:
        return AppointmentPriority.URGENT
    return AppointmentPriority.HIGH


def create_appointment_for_escalation(
    *,
    escalation_case,
    created_by,
    priority=None,
    scheduled_at=None,
    notes="",
):
    if hasattr(escalation_case, "appointment"):
        raise ValidationError("Appointment already exists for this escalation case.")

    with transaction.atomic():
        appointment = Appointment.objects.create(
            patient=escalation_case.patient,
            follow_up_case=escalation_case.follow_up_case,
            escalation_case=escalation_case,
            risk_assessment=escalation_case.risk_assessment,
            priority=priority or default_priority_for_escalation(escalation_case),
            status=AppointmentStatus.PRIORITY_SUGGESTED,
            scheduled_at=scheduled_at,
            notes=notes,
            created_by=created_by,
        )
        sync_case_status_for_appointment(appointment)
        record_audit(
            created_by,
            audit_actions.APPOINTMENT_CREATED,
            appointment,
            {
                "patient_id": appointment.patient_id,
                "follow_up_case_id": appointment.follow_up_case_id,
                "escalation_case_id": appointment.escalation_case_id,
                "risk_assessment_id": appointment.risk_assessment_id,
                "priority": appointment.priority,
                "status": appointment.status,
                "scheduled_at": appointment.scheduled_at.isoformat()
                if appointment.scheduled_at
                else None,
            },
        )
    return appointment


def sync_case_status_for_appointment(appointment):
    update_escalation_status(appointment.escalation_case, EscalationStatus.APPOINTMENT_REQUIRED)
    sync_follow_up_case_from_appointment(appointment)
    return appointment
