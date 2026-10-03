from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from accounts.models import UserRole
from decision_engine.models import RiskAssessment
from escalations.models import EscalationCase
from patients.models import FollowUpCase, PatientProfile
from workflows.models import AppointmentPriority


class AppointmentStatus(models.TextChoices):
    REQUESTED = "REQUESTED", "Requested"
    PRIORITY_SUGGESTED = "PRIORITY_SUGGESTED", "Priority suggested"
    SCHEDULED = "SCHEDULED", "Scheduled"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class Appointment(models.Model):
    patient = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    follow_up_case = models.ForeignKey(
        FollowUpCase,
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    escalation_case = models.OneToOneField(
        EscalationCase,
        on_delete=models.CASCADE,
        related_name="appointment",
    )
    risk_assessment = models.ForeignKey(
        RiskAssessment,
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    priority = models.CharField(max_length=20, choices=AppointmentPriority.choices)
    status = models.CharField(
        max_length=32,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.PRIORITY_SUGGESTED,
    )
    scheduled_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_appointments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def clean(self):
        errors = {}

        if self.priority == AppointmentPriority.NONE:
            errors["priority"] = "Appointment priority cannot be NONE."

        if self.escalation_case:
            if self.patient_id and self.patient_id != self.escalation_case.patient_id:
                errors["patient"] = "Patient must match the escalation case patient."

            if (
                self.follow_up_case_id
                and self.follow_up_case_id != self.escalation_case.follow_up_case_id
            ):
                errors["follow_up_case"] = (
                    "Follow-up case must match the escalation case follow-up case."
                )

            if (
                self.risk_assessment_id
                and self.risk_assessment_id != self.escalation_case.risk_assessment_id
            ):
                errors["risk_assessment"] = (
                    "Risk assessment must match the escalation case risk assessment."
                )

        if self.created_by and self.created_by.role not in {UserRole.DENTIST, UserRole.ADMIN}:
            errors["created_by"] = "Appointment creator must be DENTIST or ADMIN."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.patient.user.username}: {self.priority} appointment"
