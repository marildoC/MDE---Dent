from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from accounts.models import UserRole
from workflows.models import TreatmentWorkflow, WorkflowStatus


class FollowUpCaseStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    ACTIVE = "ACTIVE", "Active"
    MONITORING = "MONITORING", "Monitoring"
    AI_GUIDANCE_PROVIDED = "AI_GUIDANCE_PROVIDED", "AI Guidance Provided"
    ESCALATED = "ESCALATED", "Escalated"
    APPOINTMENT_REQUIRED = "APPOINTMENT_REQUIRED", "Appointment Required"
    RESOLVED = "RESOLVED", "Resolved"
    CLOSED = "CLOSED", "Closed"


class PatientProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_profile",
    )
    phone = models.CharField(max_length=40, blank=True)
    dental_notes = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__username", "id"]

    def clean(self):
        if self.user and self.user.role != UserRole.PATIENT:
            raise ValidationError({"user": "Patient profile user must have PATIENT role."})

    def __str__(self):
        return f"Patient profile: {self.user.username}"


class FollowUpCase(models.Model):
    patient = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name="follow_up_cases",
    )
    workflow = models.ForeignKey(
        TreatmentWorkflow,
        on_delete=models.PROTECT,
        related_name="follow_up_cases",
    )
    treatment_date = models.DateField()
    status = models.CharField(
        max_length=32,
        choices=FollowUpCaseStatus.choices,
        default=FollowUpCaseStatus.ACTIVE,
    )
    assigned_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_follow_up_cases",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-treatment_date", "-id"]

    def clean(self):
        errors = {}
        if self.workflow and self.workflow.status != WorkflowStatus.ACTIVE:
            errors["workflow"] = "Only ACTIVE workflows can be assigned to patients."

        if self.assigned_staff and self.assigned_staff.role not in {
            UserRole.DENTIST,
            UserRole.ADMIN,
        }:
            errors["assigned_staff"] = "Assigned staff must be DENTIST or ADMIN."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.patient.user.username} - {self.workflow.name}"
