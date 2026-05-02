from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from accounts.models import UserRole
from patients.models import FollowUpCase, FollowUpCaseStatus


class SymptomIntensity(models.TextChoices):
    NONE = "NONE", "None"
    MILD = "MILD", "Mild"
    SEVERE = "SEVERE", "Severe"


class SymptomReport(models.Model):
    follow_up_case = models.ForeignKey(
        FollowUpCase,
        on_delete=models.CASCADE,
        related_name="symptom_reports",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="symptom_reports",
    )
    day_after_treatment = models.PositiveIntegerField()
    pain_level = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    swelling = models.CharField(max_length=16, choices=SymptomIntensity.choices)
    bleeding = models.CharField(max_length=16, choices=SymptomIntensity.choices)
    fever = models.BooleanField(default=False)
    bad_smell = models.BooleanField(default=False)
    symptom_values = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    image = models.FileField(upload_to="symptom_reports/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def clean(self):
        errors = {}
        if self.submitted_by and self.submitted_by.role != UserRole.PATIENT:
            errors["submitted_by"] = "Only PATIENT users can submit symptom reports."

        if self.follow_up_case and self.submitted_by:
            case_user_id = self.follow_up_case.patient.user_id
            if case_user_id != self.submitted_by_id:
                errors["follow_up_case"] = "Report must belong to the submitting patient."

        if self.follow_up_case and self.follow_up_case.status in {
            FollowUpCaseStatus.CLOSED,
            FollowUpCaseStatus.RESOLVED,
        }:
            errors["follow_up_case"] = "Reports cannot be submitted for closed or resolved cases."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.follow_up_case and self.follow_up_case.treatment_date:
            delta = timezone.localdate() - self.follow_up_case.treatment_date
            self.day_after_treatment = max(0, delta.days)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Report for {self.follow_up_case} on day {self.day_after_treatment}"
