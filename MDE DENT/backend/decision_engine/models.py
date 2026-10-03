from django.db import models

from reports.models import SymptomReport
from workflows.models import (
    AppointmentPriority,
    CareStage,
    RecommendedAction,
    RiskLevel,
)


class RiskAssessment(models.Model):
    report = models.OneToOneField(
        SymptomReport,
        on_delete=models.CASCADE,
        related_name="risk_assessment",
    )
    detected_stage = models.ForeignKey(
        CareStage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="risk_assessments",
    )
    matched_rules = models.JSONField(default=list, blank=True)
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices)
    recommended_action = models.CharField(
        max_length=40,
        choices=RecommendedAction.choices,
    )
    appointment_priority = models.CharField(
        max_length=20,
        choices=AppointmentPriority.choices,
        default=AppointmentPriority.NONE,
    )
    explanation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.report}: {self.risk_level}"
