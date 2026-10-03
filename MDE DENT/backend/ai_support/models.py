from django.db import models

from decision_engine.models import RiskAssessment


class AdviceMessageType(models.TextChoices):
    LOW_RISK_AFTERCARE = "LOW_RISK_AFTERCARE", "Low-risk aftercare"
    WARNING_MONITORING = "WARNING_MONITORING", "Warning monitoring"
    HIGH_STAFF_REVIEW = "HIGH_STAFF_REVIEW", "High staff review"
    URGENT_ATTENTION = "URGENT_ATTENTION", "Urgent attention"


class AdviceSource(models.TextChoices):
    TEMPLATE = "TEMPLATE", "Template"


class AdviceMessage(models.Model):
    risk_assessment = models.OneToOneField(
        RiskAssessment,
        on_delete=models.CASCADE,
        related_name="advice_message",
    )
    message = models.TextField()
    message_type = models.CharField(max_length=40, choices=AdviceMessageType.choices)
    source = models.CharField(
        max_length=20,
        choices=AdviceSource.choices,
        default=AdviceSource.TEMPLATE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.risk_assessment}: {self.message_type}"
