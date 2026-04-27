from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from accounts.models import UserRole
from decision_engine.models import RiskAssessment
from patients.models import FollowUpCase, PatientProfile
from reports.models import SymptomReport
from workflows.models import RiskLevel


class EscalationStatus(models.TextChoices):
    NEW = "NEW", "New"
    IN_REVIEW = "IN_REVIEW", "In review"
    WAITING_FOR_PATIENT = "WAITING_FOR_PATIENT", "Waiting for patient"
    APPOINTMENT_REQUIRED = "APPOINTMENT_REQUIRED", "Appointment required"
    RESOLVED = "RESOLVED", "Resolved"
    CLOSED = "CLOSED", "Closed"


class EscalationCase(models.Model):
    risk_assessment = models.OneToOneField(
        RiskAssessment,
        on_delete=models.CASCADE,
        related_name="escalation_case",
    )
    report = models.ForeignKey(
        SymptomReport,
        on_delete=models.CASCADE,
        related_name="escalation_cases",
    )
    follow_up_case = models.ForeignKey(
        FollowUpCase,
        on_delete=models.CASCADE,
        related_name="escalation_cases",
    )
    patient = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name="escalation_cases",
    )
    status = models.CharField(
        max_length=32,
        choices=EscalationStatus.choices,
        default=EscalationStatus.NEW,
    )
    urgency = models.CharField(
        max_length=20,
        choices=(
            (RiskLevel.HIGH, "High"),
            (RiskLevel.URGENT, "Urgent"),
        ),
    )
    assigned_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_escalation_cases",
    )
    staff_response = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def clean(self):
        errors = {}
        if self.risk_assessment:
            if self.risk_assessment.risk_level not in {RiskLevel.HIGH, RiskLevel.URGENT}:
                errors["risk_assessment"] = "Escalations require HIGH or URGENT risk."

            if self.report_id and self.report_id != self.risk_assessment.report_id:
                errors["report"] = "Report must match the risk assessment report."

        if self.report:
            if self.follow_up_case_id and self.follow_up_case_id != self.report.follow_up_case_id:
                errors["follow_up_case"] = "Follow-up case must match the report."

            if self.patient_id and self.patient_id != self.report.follow_up_case.patient_id:
                errors["patient"] = "Patient must match the report follow-up case."

        if self.urgency not in {RiskLevel.HIGH, RiskLevel.URGENT}:
            errors["urgency"] = "Escalation urgency must be HIGH or URGENT."

        if self.assigned_staff and self.assigned_staff.role not in {
            UserRole.DENTIST,
            UserRole.ADMIN,
        }:
            errors["assigned_staff"] = "Assigned staff must be DENTIST or ADMIN."

        if errors:
            raise ValidationError(errors)

    def mark_resolved_timestamp(self):
        if self.status in {EscalationStatus.RESOLVED, EscalationStatus.CLOSED}:
            self.resolved_at = self.resolved_at or timezone.now()
        else:
            self.resolved_at = None

    def __str__(self):
        return f"{self.patient.user.username}: {self.urgency} escalation"
