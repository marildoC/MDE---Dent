from collections import Counter
from datetime import datetime, time, timedelta

from django.db.models import Count, Q
from django.utils import timezone

from appointments.models import Appointment, AppointmentStatus
from audit import actions as audit_actions
from audit.models import AuditLog
from decision_engine.models import RiskAssessment
from escalations.models import EscalationCase, EscalationStatus
from patients.models import FollowUpCase, FollowUpCaseStatus, PatientProfile
from reports.models import SymptomReport
from workflows.models import RiskLevel, TreatmentWorkflow, WorkflowStatus

from .suggestions import suggestions_for


UNSUPPORTED_MESSAGE = (
    "I can answer questions about patients, follow-up cases, reports, risk assessments, "
    "escalations, appointments, workflows, and audit history. This question is outside the "
    "currently supported Admin Intelligence scope."
)

UNRESOLVED_ESCALATION_STATUSES = (
    EscalationStatus.NEW,
    EscalationStatus.IN_REVIEW,
    EscalationStatus.WAITING_FOR_PATIENT,
    EscalationStatus.APPOINTMENT_REQUIRED,
)


def unsupported_response(question=""):
    return response(
        answer="I cannot answer that yet. Try one of these supported operational questions:",
        intent="unsupported",
        display_type="unsupported",
        data={"scope": UNSUPPORTED_MESSAGE},
        suggested_followups=suggested_questions_for_unsupported(question),
    )


def suggested_questions_for_unsupported(question):
    return suggestions_for(question)[:6]


def patient_not_found_response(patient_name):
    return response(
        answer=f"No matching patient record was found for '{patient_name}'.",
        intent="patient_not_found",
        display_type="summary",
        data={"patient": patient_name},
        suggested_followups=[
            "Show unresolved escalations",
            "Show today’s appointments",
            "Show active workflows",
        ],
    )


def response(
    *,
    answer,
    intent,
    display_type,
    data=None,
    columns=None,
    rows=None,
    cards=None,
    timeline=None,
    evidence=None,
    suggested_followups=None,
):
    return {
        "answer": answer,
        "intent": intent,
        "display_type": display_type,
        "data": data or {},
        "columns": columns or [],
        "rows": rows or [],
        "cards": cards or [],
        "timeline": timeline or [],
        "evidence": evidence or [],
        "suggested_followups": suggested_followups or [],
    }


def count_follow_up_cases_for_patient(patient):
    count = FollowUpCase.objects.filter(patient=patient).count()
    return response(
        answer=f"{patient.user.username} has {count} follow-up case{'s' if count != 1 else ''}.",
        intent="count_follow_up_cases_for_patient",
        display_type="summary",
        data={"patient": patient.user.username, "count": count},
        evidence=[patient_evidence(patient)],
        suggested_followups=patient_followups(patient.user.username),
    )


def latest_follow_up_case_for_patient(patient):
    follow_up_case = latest_case(patient)
    if not follow_up_case:
        return response(
            answer=f"{patient.user.username} has no follow-up cases.",
            intent="latest_follow_up_case_for_patient",
            display_type="summary",
            evidence=[patient_evidence(patient)],
            suggested_followups=patient_followups(patient.user.username),
        )

    return response(
        answer=f"Latest follow-up case for {patient.user.username} is case #{follow_up_case.id}.",
        intent="latest_follow_up_case_for_patient",
        display_type="cards",
        cards=[case_card(follow_up_case)],
        evidence=[patient_evidence(patient), case_evidence(follow_up_case)],
        suggested_followups=patient_followups(patient.user.username),
    )


def active_cases_for_patient(patient):
    cases = FollowUpCase.objects.filter(patient=patient).exclude(
        status__in=[FollowUpCaseStatus.RESOLVED, FollowUpCaseStatus.CLOSED]
    )
    cards = [case_card(item) for item in cases]
    count = len(cards)
    return response(
        answer=(
            f"{patient.user.username} has {count} active follow-up case{'s' if count != 1 else ''}."
        ),
        intent="active_cases_for_patient",
        display_type="cards" if cards else "summary",
        cards=cards,
        data={"patient": patient.user.username, "count": count},
        evidence=[patient_evidence(patient)],
        suggested_followups=patient_followups(patient.user.username),
    )


def latest_case_status_for_patient(patient):
    follow_up_case = latest_case(patient)
    if not follow_up_case:
        return response(
            answer=f"{patient.user.username} has no follow-up cases.",
            intent="latest_case_status_for_patient",
            display_type="summary",
            evidence=[patient_evidence(patient)],
            suggested_followups=patient_followups(patient.user.username),
        )

    return response(
        answer=(
            f"{patient.user.username}'s latest follow-up case is #{follow_up_case.id} "
            f"with status {follow_up_case.status}."
        ),
        intent="latest_case_status_for_patient",
        display_type="cards",
        cards=[case_card(follow_up_case)],
        evidence=[patient_evidence(patient), case_evidence(follow_up_case)],
        suggested_followups=patient_followups(patient.user.username),
    )


def reports_for_latest_case(patient):
    follow_up_case = latest_case(patient)
    if not follow_up_case:
        return response(
            answer=f"{patient.user.username} has no follow-up cases.",
            intent="reports_for_latest_case",
            display_type="summary",
            evidence=[patient_evidence(patient)],
            suggested_followups=patient_followups(patient.user.username),
        )

    reports = SymptomReport.objects.filter(follow_up_case=follow_up_case).select_related(
        "risk_assessment"
    )
    rows = [report_row(report) for report in reports]
    return response(
        answer=(
            f"Case #{follow_up_case.id} for {patient.user.username} has "
            f"{len(rows)} report{'s' if len(rows) != 1 else ''}."
        ),
        intent="reports_for_latest_case",
        display_type="table" if rows else "summary",
        columns=report_columns(),
        rows=rows,
        evidence=[patient_evidence(patient), case_evidence(follow_up_case)],
        suggested_followups=patient_followups(patient.user.username),
    )


def patient_count():
    count = PatientProfile.objects.count()
    return response(
        answer=f"There are {count} patient profile{'s' if count != 1 else ''} in the clinic.",
        intent="patient_count",
        display_type="summary",
        data={"count": count},
        suggested_followups=[
            "How many active follow-up cases are there?",
            "Show appointment-required cases",
            "Show unresolved escalations",
        ],
    )


def total_active_follow_up_cases():
    cases = FollowUpCase.objects.filter(status=FollowUpCaseStatus.ACTIVE).select_related(
        "patient__user", "workflow"
    )
    cards = [case_card(item) for item in cases]
    return response(
        answer=f"There are {len(cards)} active follow-up case{'s' if len(cards) != 1 else ''}.",
        intent="total_active_follow_up_cases",
        display_type="cards" if cards else "summary",
        data={"count": len(cards)},
        cards=cards,
        evidence=[case_evidence(item) for item in cases],
        suggested_followups=[
            "How many patient profiles exist?",
            "Show reports submitted today",
            "Show unresolved escalations",
        ],
    )


def reports_submitted_today():
    start, end = day_bounds()
    reports = SymptomReport.objects.filter(
        created_at__gte=start,
        created_at__lt=end,
    ).select_related(
        "follow_up_case",
        "follow_up_case__patient",
        "follow_up_case__patient__user",
        "risk_assessment",
    )
    rows = [report_row(item) for item in reports]
    return response(
        answer=f"There are {len(rows)} report{'s' if len(rows) != 1 else ''} submitted today.",
        intent="reports_submitted_today",
        display_type="table" if rows else "summary",
        data={"count": len(rows)},
        columns=report_columns(),
        rows=rows,
        evidence=[report_evidence(item) for item in reports],
        suggested_followups=report_followups(),
    )


def count_unresolved_escalations():
    escalations = EscalationCase.objects.filter(status__in=UNRESOLVED_ESCALATION_STATUSES)
    total = escalations.count()
    high = escalations.filter(urgency=RiskLevel.HIGH).count()
    urgent = escalations.filter(urgency=RiskLevel.URGENT).count()
    return response(
        answer=f"There are {total} unresolved escalation{'s' if total != 1 else ''}.",
        intent="count_unresolved_escalations",
        display_type="summary",
        data={"count": total, "high": high, "urgent": urgent},
        suggested_followups=escalation_followups(),
    )


def appointment_required_cases():
    cases = appointment_required_case_queryset()
    cards = [case_card(item) for item in cases]
    return response(
        answer=(
            f"Found {len(cards)} appointment-required case{'s' if len(cards) != 1 else ''}."
        ),
        intent="appointment_required_cases",
        display_type="cards" if cards else "summary",
        data={"count": len(cards)},
        cards=cards,
        evidence=[case_evidence(item) for item in cases],
        suggested_followups=appointment_followups(),
    )


def appointments_scheduled_today(status_scheduled=False):
    appointments = appointments_for_today()
    if status_scheduled:
        appointments = appointments.filter(status=AppointmentStatus.SCHEDULED)
    rows = [appointment_row(item) for item in appointments]
    status_counts = dict(Counter(item.status for item in appointments))
    status_clause = " with status scheduled" if status_scheduled else " with a scheduled time"
    return response(
        answer=f"There are {len(rows)} appointments{status_clause} today.",
        intent="appointments_scheduled_today",
        display_type="table" if rows else "summary",
        columns=appointment_columns(),
        rows=rows,
        data={"count": len(rows), "status_breakdown": status_counts},
        evidence=[appointment_evidence(item) for item in appointments],
        suggested_followups=appointment_followups(),
    )


def todays_appointments():
    appointments = appointments_for_today()
    rows = [appointment_row(item) for item in appointments]
    return response(
        answer=f"Found {len(rows)} appointment{'s' if len(rows) != 1 else ''} scheduled today.",
        intent="todays_appointments",
        display_type="table" if rows else "summary",
        columns=appointment_columns(),
        rows=rows,
        evidence=[appointment_evidence(item) for item in appointments],
        suggested_followups=appointment_followups(),
    )


def appointments_for_patient(patient):
    appointments = Appointment.objects.filter(patient=patient).select_related(
        "patient__user",
        "follow_up_case",
        "follow_up_case__workflow",
        "escalation_case",
    )
    rows = [appointment_row(item) for item in appointments]
    return response(
        answer=(
            f"Found {len(rows)} appointment{'s' if len(rows) != 1 else ''} for "
            f"{patient.user.username}."
        ),
        intent="appointments_for_patient",
        display_type="table" if rows else "summary",
        columns=appointment_columns(),
        rows=rows,
        evidence=[patient_evidence(patient), *[appointment_evidence(item) for item in appointments]],
        suggested_followups=patient_followups(patient.user.username),
    )


def appointment_required_without_scheduled():
    cases = appointment_required_case_queryset()
    filtered = [
        item
        for item in cases
        if not item.appointments.filter(
            status=AppointmentStatus.SCHEDULED,
            scheduled_at__isnull=False,
        ).exists()
    ]
    return response(
        answer=(
            f"Found {len(filtered)} appointment-required case{'s' if len(filtered) != 1 else ''} "
            "without a scheduled appointment."
        ),
        intent="appointment_required_without_scheduled",
        display_type="cards" if filtered else "summary",
        cards=[case_card(item) for item in filtered],
        evidence=[case_evidence(item) for item in filtered],
        suggested_followups=appointment_followups(),
    )


def cancelled_appointments():
    appointments = Appointment.objects.filter(status=AppointmentStatus.CANCELLED).select_related(
        "patient__user", "follow_up_case", "follow_up_case__workflow", "escalation_case"
    )
    rows = [appointment_row(item) for item in appointments]
    return response(
        answer=f"Found {len(rows)} cancelled appointment{'s' if len(rows) != 1 else ''}.",
        intent="cancelled_appointments",
        display_type="table" if rows else "summary",
        columns=appointment_columns(),
        rows=rows,
        evidence=[appointment_evidence(item) for item in appointments],
        suggested_followups=appointment_followups(),
    )


def completed_appointments_today():
    start, end = day_bounds()
    appointments = Appointment.objects.filter(
        status=AppointmentStatus.COMPLETED,
        updated_at__gte=start,
        updated_at__lt=end,
    ).select_related("patient__user", "follow_up_case", "follow_up_case__workflow", "escalation_case")
    rows = [appointment_row(item) for item in appointments]
    return response(
        answer=f"Found {len(rows)} appointments completed today.",
        intent="completed_appointments_today",
        display_type="table" if rows else "summary",
        columns=appointment_columns(),
        rows=rows,
        evidence=[appointment_evidence(item) for item in appointments],
        suggested_followups=appointment_followups(),
    )


def unresolved_escalations(urgent_only=False):
    escalations = EscalationCase.objects.filter(status__in=UNRESOLVED_ESCALATION_STATUSES)
    intent = "urgent_unresolved_escalations" if urgent_only else "unresolved_escalations"
    if urgent_only:
        escalations = escalations.filter(urgency=RiskLevel.URGENT)
    escalations = escalation_queryset(escalations)
    cards = [escalation_card(item) for item in escalations]
    qualifier = "urgent unresolved" if urgent_only else "unresolved"
    return response(
        answer=f"Found {len(cards)} {qualifier} escalation{'s' if len(cards) != 1 else ''}.",
        intent=intent,
        display_type="cards" if cards else "summary",
        cards=cards,
        evidence=[escalation_evidence(item) for item in escalations],
        suggested_followups=escalation_followups(),
    )


def escalations_for_patient(patient):
    escalations = escalation_queryset(EscalationCase.objects.filter(patient=patient))
    cards = [escalation_card(item) for item in escalations]
    return response(
        answer=(
            f"Found {len(cards)} escalation{'s' if len(cards) != 1 else ''} for "
            f"{patient.user.username}."
        ),
        intent="escalations_for_patient",
        display_type="cards" if cards else "summary",
        cards=cards,
        evidence=[patient_evidence(patient), *[escalation_evidence(item) for item in escalations]],
        suggested_followups=patient_followups(patient.user.username),
    )


def waiting_for_patient_escalations():
    escalations = escalation_queryset(
        EscalationCase.objects.filter(status=EscalationStatus.WAITING_FOR_PATIENT)
    )
    cards = [escalation_card(item) for item in escalations]
    return response(
        answer=f"Found {len(cards)} escalation{'s' if len(cards) != 1 else ''} waiting for patient.",
        intent="waiting_for_patient_escalations",
        display_type="cards" if cards else "summary",
        cards=cards,
        evidence=[escalation_evidence(item) for item in escalations],
        suggested_followups=escalation_followups(),
    )


def last_staff_response_for_patient(patient):
    escalation = (
        EscalationCase.objects.filter(patient=patient)
        .exclude(staff_response="")
        .select_related("patient__user", "follow_up_case", "risk_assessment")
        .order_by("-updated_at", "-id")
        .first()
    )
    if not escalation:
        return response(
            answer=f"No recorded staff response was found for {patient.user.username}.",
            intent="last_staff_response_for_patient",
            display_type="summary",
            evidence=[patient_evidence(patient)],
            suggested_followups=patient_followups(patient.user.username),
        )

    audit = (
        AuditLog.objects.select_related("actor")
        .filter(
            action=audit_actions.ESCALATION_UPDATED,
            target_type="EscalationCase",
            target_id=str(escalation.id),
        )
        .order_by("-created_at", "-id")
        .first()
    )
    actor = audit.actor.username if audit and audit.actor else "not recorded"
    return response(
        answer=(
            f"The latest recorded staff response for {patient.user.username} is on escalation "
            f"#{escalation.id}. The responding actor is {actor}."
        ),
        intent="last_staff_response_for_patient",
        display_type="cards",
        cards=[escalation_card(escalation)],
        evidence=[
            patient_evidence(patient),
            escalation_evidence(escalation),
            *([audit_evidence(audit)] if audit else []),
        ],
        suggested_followups=patient_followups(patient.user.username),
    )


def active_workflows(count_only=False):
    workflows = TreatmentWorkflow.objects.filter(status=WorkflowStatus.ACTIVE).annotate(
        case_count=Count("follow_up_cases")
    )
    if count_only:
        count = workflows.count()
        return response(
            answer=f"There are {count} active workflow{'s' if count != 1 else ''}.",
            intent="count_active_workflows",
            display_type="summary",
            data={"count": count},
            suggested_followups=workflow_followups(),
        )
    rows = [workflow_row(item) for item in workflows]
    return response(
        answer=f"Found {len(rows)} active workflow{'s' if len(rows) != 1 else ''}.",
        intent="active_workflows",
        display_type="table" if rows else "summary",
        columns=workflow_columns(),
        rows=rows,
        evidence=[workflow_evidence(item) for item in workflows],
        suggested_followups=workflow_followups(),
    )


def workflows_by_status():
    rows = [
        {"status": item["status"], "count": item["count"]}
        for item in TreatmentWorkflow.objects.values("status").annotate(count=Count("id")).order_by("status")
    ]
    return response(
        answer="Workflow counts by status are shown below.",
        intent="workflows_by_status",
        display_type="table" if rows else "summary",
        columns=[
            {"key": "status", "label": "Status"},
            {"key": "count", "label": "Count"},
        ],
        rows=rows,
        suggested_followups=workflow_followups(),
    )


def workflow_with_most_escalations():
    workflows = TreatmentWorkflow.objects.all()
    counts = []
    for workflow in workflows:
        count = EscalationCase.objects.filter(follow_up_case__workflow=workflow).count()
        counts.append((count, workflow))
    if not counts:
        return response(
            answer="No workflows were found.",
            intent="workflow_with_most_escalations",
            display_type="summary",
            suggested_followups=workflow_followups(),
        )
    count, workflow = max(counts, key=lambda item: (item[0], item[1].id))
    return response(
        answer=f"{workflow.name} has the most escalations ({count}).",
        intent="workflow_with_most_escalations",
        display_type="table",
        columns=[
            {"key": "workflow_id", "label": "Workflow ID"},
            {"key": "name", "label": "Workflow"},
            {"key": "escalations", "label": "Escalations"},
        ],
        rows=[{"workflow_id": workflow.id, "name": workflow.name, "escalations": count}],
        evidence=[workflow_evidence(workflow)],
        suggested_followups=workflow_followups(),
    )


def post_extraction_workflow_status():
    workflows = TreatmentWorkflow.objects.filter(name__icontains="Post-Extraction")
    rows = [workflow_row(item) for item in workflows]
    return response(
        answer=f"Found {len(rows)} Post-Extraction workflow record{'s' if len(rows) != 1 else ''}.",
        intent="post_extraction_workflow_status",
        display_type="table" if rows else "summary",
        columns=workflow_columns(),
        rows=rows,
        evidence=[workflow_evidence(item) for item in workflows],
        suggested_followups=workflow_followups(),
    )


def risk_reports_today(risk_level):
    start, end = day_bounds()
    assessments = assessment_queryset(
        RiskAssessment.objects.filter(
            risk_level=risk_level,
            created_at__gte=start,
            created_at__lt=end,
        )
    )
    rows = [assessment_report_row(item) for item in assessments]
    return response(
        answer=f"Found {len(rows)} {risk_level.lower()}-risk report{'s' if len(rows) != 1 else ''} today.",
        intent=f"{risk_level.lower()}_risk_reports_today",
        display_type="table" if rows else "summary",
        columns=assessment_report_columns(),
        rows=rows,
        evidence=[assessment_evidence(item) for item in assessments],
        suggested_followups=report_followups(),
    )


def urgent_reports_this_week():
    start, end = week_bounds()
    assessments = assessment_queryset(
        RiskAssessment.objects.filter(
            risk_level=RiskLevel.URGENT,
            created_at__gte=start,
            created_at__lt=end,
        )
    )
    rows = [assessment_report_row(item) for item in assessments]
    return response(
        answer=f"Found {len(rows)} urgent report{'s' if len(rows) != 1 else ''} this week.",
        intent="urgent_reports_this_week",
        display_type="table" if rows else "summary",
        columns=assessment_report_columns(),
        rows=rows,
        evidence=[assessment_evidence(item) for item in assessments],
        suggested_followups=report_followups(),
    )


def latest_high_risk_reports():
    assessments = assessment_queryset(
        RiskAssessment.objects.filter(risk_level=RiskLevel.HIGH).order_by("-created_at", "-id")[:10]
    )
    rows = [assessment_report_row(item) for item in assessments]
    return response(
        answer=f"Showing {len(rows)} latest high-risk report{'s' if len(rows) != 1 else ''}.",
        intent="latest_high_risk_reports",
        display_type="table" if rows else "summary",
        columns=assessment_report_columns(),
        rows=rows,
        evidence=[assessment_evidence(item) for item in assessments],
        suggested_followups=report_followups(),
    )


def reports_produced_escalation():
    escalations = list(escalation_queryset(EscalationCase.objects.all())[:20])
    rows = [assessment_report_row(item.risk_assessment) for item in escalations]
    return response(
        answer=f"Found {len(rows)} report{'s' if len(rows) != 1 else ''} that produced escalation.",
        intent="reports_produced_escalation",
        display_type="table" if rows else "summary",
        columns=assessment_report_columns(),
        rows=rows,
        evidence=[escalation_evidence(item) for item in escalations],
        suggested_followups=report_followups(),
    )


def audit_trace_for_case(case_id):
    follow_up_case = FollowUpCase.objects.filter(id=case_id).select_related("patient__user", "workflow").first()
    if not follow_up_case:
        return response(
            answer=f"No follow-up case was found with id {case_id}.",
            intent="audit_trace_for_case",
            display_type="summary",
            data={"case_id": case_id},
            suggested_followups=["Show recent audit events", "Show active workflows"],
        )

    logs = audit_logs_for_case(case_id)
    return response(
        answer=f"Found {len(logs)} audit event{'s' if len(logs) != 1 else ''} for case #{case_id}.",
        intent="audit_trace_for_case",
        display_type="timeline" if logs else "summary",
        timeline=[audit_timeline_item(item) for item in logs],
        evidence=[case_evidence(follow_up_case), *[audit_evidence(item) for item in logs]],
        suggested_followups=["Show appointment updates today", "Show recent audit events"],
    )


def workflow_activation_actor(workflow_id):
    workflow = TreatmentWorkflow.objects.filter(id=workflow_id).first()
    if not workflow:
        return response(
            answer=f"No workflow was found with id {workflow_id}.",
            intent="workflow_activation_actor",
            display_type="summary",
            data={"workflow_id": workflow_id},
            suggested_followups=workflow_followups(),
        )
    log = (
        AuditLog.objects.select_related("actor")
        .filter(
            action=audit_actions.WORKFLOW_ACTIVATED,
            target_type="TreatmentWorkflow",
            target_id=str(workflow_id),
        )
        .order_by("-created_at", "-id")
        .first()
    )
    if not log:
        return response(
            answer=f"No activation audit event was found for workflow #{workflow_id}.",
            intent="workflow_activation_actor",
            display_type="summary",
            evidence=[workflow_evidence(workflow)],
            suggested_followups=workflow_followups(),
        )
    actor = log.actor.username if log.actor else "System"
    return response(
        answer=f"Workflow #{workflow_id} was activated by {actor}.",
        intent="workflow_activation_actor",
        display_type="timeline",
        timeline=[audit_timeline_item(log)],
        evidence=[workflow_evidence(workflow), audit_evidence(log)],
        suggested_followups=workflow_followups(),
    )


def actions_by_actor_today(actor):
    start, end = day_bounds()
    logs = AuditLog.objects.select_related("actor").filter(
        actor=actor,
        created_at__gte=start,
        created_at__lt=end,
    )
    count = logs.count()
    return response(
        answer=f"{actor.username} performed {count} audited action{'s' if count != 1 else ''} today.",
        intent="actions_by_actor_today",
        display_type="timeline" if logs else "summary",
        timeline=[audit_timeline_item(item) for item in logs],
        evidence=[audit_evidence(item) for item in logs],
        suggested_followups=["Show recent audit events", "Show appointment updates today"],
    )


def recent_audit_events():
    logs = AuditLog.objects.select_related("actor").order_by("-created_at", "-id")[:15]
    return response(
        answer=f"Showing {len(logs)} recent audit event{'s' if len(logs) != 1 else ''}.",
        intent="recent_audit_events",
        display_type="timeline" if logs else "summary",
        timeline=[audit_timeline_item(item) for item in logs],
        evidence=[audit_evidence(item) for item in logs],
        suggested_followups=["Show appointment updates today", "Show active workflows"],
    )


def appointment_updates_today():
    start, end = day_bounds()
    logs = AuditLog.objects.select_related("actor").filter(
        action__in=[audit_actions.APPOINTMENT_CREATED, audit_actions.APPOINTMENT_UPDATED],
        created_at__gte=start,
        created_at__lt=end,
    )
    count = logs.count()
    return response(
        answer=f"Found {count} appointment audit update{'s' if count != 1 else ''} today.",
        intent="appointment_updates_today",
        display_type="timeline" if logs else "summary",
        timeline=[audit_timeline_item(item) for item in logs],
        evidence=[audit_evidence(item) for item in logs],
        suggested_followups=appointment_followups(),
    )


def latest_case(patient):
    return (
        FollowUpCase.objects.filter(patient=patient)
        .select_related("patient__user", "workflow", "assigned_staff")
        .order_by("-treatment_date", "-id")
        .first()
    )


def appointments_for_today():
    start, end = day_bounds()
    return Appointment.objects.filter(
        scheduled_at__gte=start,
        scheduled_at__lt=end,
    ).select_related(
        "patient__user",
        "follow_up_case",
        "follow_up_case__workflow",
        "escalation_case",
    )


def appointment_required_case_queryset():
    return (
        FollowUpCase.objects.filter(
            Q(status=FollowUpCaseStatus.APPOINTMENT_REQUIRED)
            | Q(escalation_cases__status=EscalationStatus.APPOINTMENT_REQUIRED)
        )
        .select_related("patient__user", "workflow", "assigned_staff")
        .distinct()
    )


def day_bounds(day=None):
    current_day = day or timezone.localdate()
    timezone_info = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(current_day, time.min), timezone_info)
    end = start + timedelta(days=1)
    return start, end


def week_bounds():
    today = timezone.localdate()
    start_day = today - timedelta(days=today.weekday())
    start, _ = day_bounds(start_day)
    return start, start + timedelta(days=7)


def escalation_queryset(queryset):
    return queryset.select_related(
        "patient__user",
        "report",
        "follow_up_case",
        "follow_up_case__workflow",
        "risk_assessment",
        "assigned_staff",
        "appointment",
    ).order_by("-created_at", "-id")


def assessment_queryset(queryset):
    return queryset.select_related(
        "report",
        "report__follow_up_case",
        "report__follow_up_case__patient",
        "report__follow_up_case__patient__user",
        "report__follow_up_case__workflow",
    ).order_by("-created_at", "-id")


def audit_logs_for_case(case_id):
    logs = AuditLog.objects.select_related("actor").order_by("created_at", "id")
    matched = []
    for log in logs:
        if log.target_type == "FollowUpCase" and log.target_id == str(case_id):
            matched.append(log)
            continue
        details = log.details if isinstance(log.details, dict) else {}
        if str(details.get("follow_up_case_id")) == str(case_id):
            matched.append(log)
    return matched


def case_card(follow_up_case):
    report_count = follow_up_case.symptom_reports.count()
    latest_assessment = (
        RiskAssessment.objects.filter(report__follow_up_case=follow_up_case)
        .order_by("-created_at", "-id")
        .first()
    )
    fields = [
        {"label": "Patient", "value": follow_up_case.patient.user.username},
        {"label": "Follow-up case", "value": follow_up_case.id},
        {"label": "Workflow/treatment", "value": follow_up_case.workflow.name},
        {"label": "Status", "value": follow_up_case.status},
        {"label": "Treatment date", "value": str(follow_up_case.treatment_date)},
        {"label": "Reports count", "value": report_count},
    ]
    if latest_assessment:
        fields.append({"label": "Latest risk", "value": latest_assessment.risk_level})
    return {"title": f"Case #{follow_up_case.id}", "fields": fields}


def escalation_card(escalation):
    return {
        "title": f"Escalation #{escalation.id}",
        "fields": [
            {"label": "Patient", "value": escalation.patient.user.username},
            {"label": "Urgency", "value": escalation.urgency},
            {"label": "Status", "value": escalation.status},
            {"label": "Report day", "value": escalation.report.day_after_treatment},
            {"label": "Risk level", "value": escalation.risk_assessment.risk_level},
            {
                "label": "Staff response",
                "value": "Recorded" if escalation.staff_response else "Not recorded",
            },
            {
                "label": "Appointment exists",
                "value": "Yes" if hasattr(escalation, "appointment") else "No",
            },
            {"label": "Updated", "value": format_dt(escalation.updated_at)},
        ],
    }


def appointment_columns():
    return [
        {"key": "patient", "label": "Patient"},
        {"key": "scheduled_at", "label": "Scheduled time/date"},
        {"key": "priority", "label": "Priority"},
        {"key": "status", "label": "Status"},
        {"key": "follow_up_case", "label": "Follow-up case"},
        {"key": "escalation_status", "label": "Escalation status"},
    ]


def appointment_row(appointment):
    return {
        "id": appointment.id,
        "patient": appointment.patient.user.username,
        "scheduled_at": format_dt(appointment.scheduled_at) if appointment.scheduled_at else "Unscheduled",
        "priority": appointment.priority,
        "status": appointment.status,
        "follow_up_case": appointment.follow_up_case_id,
        "escalation_status": appointment.escalation_case.status,
    }


def report_columns():
    return [
        {"key": "report_id", "label": "Report"},
        {"key": "created_at", "label": "Created"},
        {"key": "day", "label": "Day"},
        {"key": "pain_level", "label": "Pain"},
        {"key": "swelling", "label": "Swelling"},
        {"key": "bleeding", "label": "Bleeding"},
        {"key": "fever", "label": "Fever"},
        {"key": "bad_smell", "label": "Bad smell/taste"},
        {"key": "risk_level", "label": "Risk"},
    ]


def report_row(report):
    assessment = getattr(report, "risk_assessment", None)
    return {
        "report_id": report.id,
        "created_at": format_dt(report.created_at),
        "day": report.day_after_treatment,
        "pain_level": f"{report.pain_level}/10",
        "swelling": report.swelling,
        "bleeding": report.bleeding,
        "fever": "Yes" if report.fever else "No",
        "bad_smell": "Yes" if report.bad_smell else "No",
        "risk_level": assessment.risk_level if assessment else "Unavailable",
    }


def assessment_report_columns():
    return [
        {"key": "report_id", "label": "Report"},
        {"key": "patient", "label": "Patient"},
        {"key": "case_id", "label": "Case"},
        {"key": "risk_level", "label": "Risk"},
        {"key": "recommended_action", "label": "Action"},
        {"key": "appointment_priority", "label": "Appointment priority"},
        {"key": "created_at", "label": "Assessed"},
    ]


def assessment_report_row(assessment):
    report = assessment.report
    follow_up_case = report.follow_up_case
    return {
        "report_id": report.id,
        "patient": follow_up_case.patient.user.username,
        "case_id": follow_up_case.id,
        "risk_level": assessment.risk_level,
        "recommended_action": assessment.recommended_action,
        "appointment_priority": assessment.appointment_priority,
        "created_at": format_dt(assessment.created_at),
    }


def workflow_columns():
    return [
        {"key": "workflow_id", "label": "Workflow ID"},
        {"key": "name", "label": "Workflow"},
        {"key": "treatment_type", "label": "Treatment type"},
        {"key": "status", "label": "Status"},
        {"key": "case_count", "label": "Cases"},
    ]


def workflow_row(workflow):
    return {
        "workflow_id": workflow.id,
        "name": workflow.name,
        "treatment_type": workflow.treatment_type,
        "status": workflow.status,
        "case_count": getattr(workflow, "case_count", workflow.follow_up_cases.count()),
    }


def audit_timeline_item(log):
    return {
        "id": log.id,
        "timestamp": format_dt(log.created_at),
        "actor": log.actor.username if log.actor else "System",
        "action": log.action,
        "target": f"{log.target_type} #{log.target_id}",
        "summary": compact_details(log.details),
    }


def compact_details(details):
    if not isinstance(details, dict) or not details:
        return ""
    safe_items = []
    for key, value in details.items():
        if isinstance(value, (dict, list)):
            continue
        safe_items.append(f"{key}: {value}")
    return " | ".join(safe_items[:4])


def format_dt(value):
    if not value:
        return ""
    return timezone.localtime(value).isoformat()


def patient_evidence(patient):
    return {"type": "PatientProfile", "id": patient.id}


def case_evidence(follow_up_case):
    return {"type": "FollowUpCase", "id": follow_up_case.id}


def report_evidence(report):
    return {"type": "SymptomReport", "id": report.id}


def assessment_evidence(assessment):
    return {"type": "RiskAssessment", "id": assessment.id}


def escalation_evidence(escalation):
    return {"type": "EscalationCase", "id": escalation.id}


def appointment_evidence(appointment):
    return {"type": "Appointment", "id": appointment.id}


def workflow_evidence(workflow):
    return {"type": "TreatmentWorkflow", "id": workflow.id}


def audit_evidence(log):
    return {"type": "AuditLog", "id": log.id}


def patient_followups(username):
    return [
        f"Show latest follow-up case for {username}",
        f"Show appointments for {username}",
        f"Show escalations for {username}",
        f"Show reports for {username}'s latest case",
    ]


def appointment_followups():
    return [
        "Show today’s appointments",
        "Show cancelled appointments",
        "Show appointment-required cases without scheduled appointment",
    ]


def escalation_followups():
    return [
        "Show unresolved escalations",
        "Show unresolved urgent escalations",
        "Which escalations are waiting for patient?",
    ]


def workflow_followups():
    return [
        "Which workflows are active?",
        "Show workflows by status",
        "Which workflow has most escalations?",
    ]


def report_followups():
    return [
        "How many high-risk reports today?",
        "How many urgent reports this week?",
        "Which reports produced escalation?",
    ]
