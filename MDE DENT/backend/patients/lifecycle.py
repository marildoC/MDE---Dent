from django.core.exceptions import ValidationError

from .models import FollowUpCaseStatus


TERMINAL_CASE_STATUSES = {
    FollowUpCaseStatus.RESOLVED,
    FollowUpCaseStatus.CLOSED,
}

REPORTABLE_CASE_STATUSES = {
    FollowUpCaseStatus.ACTIVE,
    FollowUpCaseStatus.MONITORING,
    FollowUpCaseStatus.AI_GUIDANCE_PROVIDED,
    FollowUpCaseStatus.ESCALATED,
    FollowUpCaseStatus.APPOINTMENT_REQUIRED,
}

ALLOWED_CASE_TRANSITIONS = {
    FollowUpCaseStatus.CREATED: {FollowUpCaseStatus.ACTIVE},
    FollowUpCaseStatus.ACTIVE: {
        FollowUpCaseStatus.MONITORING,
        FollowUpCaseStatus.ESCALATED,
        FollowUpCaseStatus.RESOLVED,
    },
    FollowUpCaseStatus.MONITORING: {
        FollowUpCaseStatus.AI_GUIDANCE_PROVIDED,
        FollowUpCaseStatus.ESCALATED,
        FollowUpCaseStatus.RESOLVED,
    },
    FollowUpCaseStatus.AI_GUIDANCE_PROVIDED: {
        FollowUpCaseStatus.MONITORING,
        FollowUpCaseStatus.ESCALATED,
        FollowUpCaseStatus.RESOLVED,
    },
    FollowUpCaseStatus.ESCALATED: {
        FollowUpCaseStatus.APPOINTMENT_REQUIRED,
        FollowUpCaseStatus.RESOLVED,
    },
    FollowUpCaseStatus.APPOINTMENT_REQUIRED: {FollowUpCaseStatus.RESOLVED},
    FollowUpCaseStatus.RESOLVED: {FollowUpCaseStatus.CLOSED},
    FollowUpCaseStatus.CLOSED: set(),
}


def can_submit_report(follow_up_case):
    return follow_up_case.status in REPORTABLE_CASE_STATUSES


def validate_reportable_case(follow_up_case):
    if not can_submit_report(follow_up_case):
        raise ValidationError("Reports cannot be submitted for closed or resolved cases.")


def validate_follow_up_case_transition(current_status, next_status):
    if current_status == next_status:
        return

    allowed_next_statuses = ALLOWED_CASE_TRANSITIONS.get(current_status, set())
    if next_status not in allowed_next_statuses:
        raise ValidationError(
            f"Follow-up case status cannot transition from {current_status} to {next_status}."
        )


def transition_follow_up_case(follow_up_case, next_status):
    previous_status = follow_up_case.status
    validate_follow_up_case_transition(follow_up_case.status, next_status)
    if follow_up_case.status != next_status:
        follow_up_case.status = next_status
        follow_up_case.save(update_fields=["status", "updated_at"])
        from audit import actions as audit_actions
        from audit.services import record_audit

        record_audit(
            None,
            audit_actions.FOLLOW_UP_CASE_STATUS_CHANGED,
            follow_up_case,
            {
                "patient_id": follow_up_case.patient_id,
                "workflow_id": follow_up_case.workflow_id,
                "previous_status": previous_status,
                "new_status": next_status,
            },
        )
    return follow_up_case


def sync_follow_up_case_from_escalation(escalation):
    from escalations.models import EscalationStatus

    follow_up_case = escalation.follow_up_case
    next_status = None

    if escalation.status == EscalationStatus.APPOINTMENT_REQUIRED:
        next_status = FollowUpCaseStatus.APPOINTMENT_REQUIRED
    elif escalation.status == EscalationStatus.RESOLVED:
        next_status = FollowUpCaseStatus.RESOLVED
    elif escalation.status == EscalationStatus.CLOSED:
        next_status = FollowUpCaseStatus.CLOSED
    elif follow_up_case.status not in {
        FollowUpCaseStatus.APPOINTMENT_REQUIRED,
        FollowUpCaseStatus.RESOLVED,
        FollowUpCaseStatus.CLOSED,
    }:
        next_status = FollowUpCaseStatus.ESCALATED

    if next_status:
        if next_status == FollowUpCaseStatus.APPOINTMENT_REQUIRED and follow_up_case.status in {
            FollowUpCaseStatus.ACTIVE,
            FollowUpCaseStatus.MONITORING,
            FollowUpCaseStatus.AI_GUIDANCE_PROVIDED,
        }:
            transition_follow_up_case(follow_up_case, FollowUpCaseStatus.ESCALATED)
            follow_up_case.refresh_from_db(fields=["status", "updated_at"])
        transition_follow_up_case(follow_up_case, next_status)

    return follow_up_case


def sync_follow_up_case_from_appointment(appointment):
    from appointments.models import AppointmentStatus

    if appointment.status == AppointmentStatus.COMPLETED:
        return transition_follow_up_case(appointment.follow_up_case, FollowUpCaseStatus.RESOLVED)

    if appointment.status != AppointmentStatus.CANCELLED:
        if appointment.follow_up_case.status in {
            FollowUpCaseStatus.ACTIVE,
            FollowUpCaseStatus.MONITORING,
            FollowUpCaseStatus.AI_GUIDANCE_PROVIDED,
        }:
            transition_follow_up_case(appointment.follow_up_case, FollowUpCaseStatus.ESCALATED)
            appointment.follow_up_case.refresh_from_db(fields=["status", "updated_at"])
        return transition_follow_up_case(
            appointment.follow_up_case,
            FollowUpCaseStatus.APPOINTMENT_REQUIRED,
        )

    return appointment.follow_up_case
