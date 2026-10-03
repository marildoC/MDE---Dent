from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from accounts.models import UserRole

from .validators import validate_condition_shape


class WorkflowStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    VALIDATED = "VALIDATED", "Validated"
    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"


class TreatmentType(models.TextChoices):
    POST_EXTRACTION = "POST_EXTRACTION", "Post-Extraction Follow-Up"


class SymptomDataType(models.TextChoices):
    INTEGER = "INTEGER", "Integer"
    BOOLEAN = "BOOLEAN", "Boolean"
    CHOICE = "CHOICE", "Choice"
    TEXT = "TEXT", "Text"


class RiskLevel(models.TextChoices):
    LOW = "LOW", "Low"
    WARNING = "WARNING", "Warning"
    HIGH = "HIGH", "High"
    URGENT = "URGENT", "Urgent"


class RecommendedAction(models.TextChoices):
    SHOW_ADVICE = "SHOW_ADVICE", "Show Advice"
    CONTINUE_MONITORING = "CONTINUE_MONITORING", "Continue Monitoring"
    RECOMMEND_CONTACT = "RECOMMEND_CONTACT", "Recommend Contact"
    ESCALATE_TO_DENTIST = "ESCALATE_TO_DENTIST", "Escalate To Dentist"
    PRIORITIZE_APPOINTMENT = "PRIORITIZE_APPOINTMENT", "Prioritize Appointment"


class AppointmentPriority(models.TextChoices):
    NONE = "NONE", "None"
    LOW = "LOW", "Low"
    NORMAL = "NORMAL", "Normal"
    HIGH = "HIGH", "High"
    URGENT = "URGENT", "Urgent"


ESCALATION_TARGET_ROLE_CHOICES = (
    (UserRole.DENTIST, "Dentist"),
    (UserRole.ADMIN, "Admin"),
)


class TreatmentWorkflow(models.Model):
    name = models.CharField(max_length=160)
    treatment_type = models.CharField(
        max_length=40,
        choices=TreatmentType.choices,
        default=TreatmentType.POST_EXTRACTION,
    )
    status = models.CharField(
        max_length=20,
        choices=WorkflowStatus.choices,
        default=WorkflowStatus.DRAFT,
    )
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_workflows",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self):
        return self.name


class CareStage(models.Model):
    workflow = models.ForeignKey(
        TreatmentWorkflow,
        on_delete=models.CASCADE,
        related_name="stages",
    )
    name = models.CharField(max_length=120)
    start_day = models.PositiveIntegerField()
    end_day = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["workflow", "sort_order", "start_day", "id"]

    def clean(self):
        if self.end_day < self.start_day:
            raise ValidationError({"end_day": "End day cannot be before start day."})

    def __str__(self):
        return f"{self.workflow}: {self.name}"


class SymptomDefinition(models.Model):
    workflow = models.ForeignKey(
        TreatmentWorkflow,
        on_delete=models.CASCADE,
        related_name="symptom_definitions",
    )
    key = models.SlugField(max_length=80)
    label = models.CharField(max_length=120)
    data_type = models.CharField(max_length=20, choices=SymptomDataType.choices)
    allowed_values = models.JSONField(default=list, blank=True)
    min_value = models.IntegerField(null=True, blank=True)
    max_value = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True)
    is_required = models.BooleanField(default=True)

    class Meta:
        ordering = ["workflow", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "key"],
                name="unique_symptom_key_per_workflow",
            )
        ]

    def __str__(self):
        return f"{self.workflow}: {self.key}"


class SymptomRule(models.Model):
    stage = models.ForeignKey(
        CareStage,
        on_delete=models.CASCADE,
        related_name="symptom_rules",
    )
    name = models.CharField(max_length=160)
    condition = models.JSONField()
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

    class Meta:
        ordering = ["stage", "id"]

    def clean(self):
        validate_condition_shape(self.condition)

    def __str__(self):
        return f"{self.stage}: {self.name}"


class AIAdviceBoundary(models.Model):
    workflow = models.ForeignKey(
        TreatmentWorkflow,
        on_delete=models.CASCADE,
        related_name="advice_boundaries",
    )
    stage = models.ForeignKey(
        CareStage,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="advice_boundaries",
    )
    allowed_topics = models.JSONField(default=list, blank=True)
    forbidden_topics = models.JSONField(default=list, blank=True)
    required_disclaimer = models.TextField(blank=True)

    class Meta:
        ordering = ["workflow", "stage_id", "id"]

    def __str__(self):
        scope = self.stage.name if self.stage else "workflow"
        return f"{self.workflow}: advice boundary ({scope})"


class EscalationRule(models.Model):
    symptom_rule = models.OneToOneField(
        SymptomRule,
        on_delete=models.CASCADE,
        related_name="escalation_rule",
    )
    target_role = models.CharField(
        max_length=20,
        choices=ESCALATION_TARGET_ROLE_CHOICES,
        default=UserRole.DENTIST,
    )
    urgency = models.CharField(
        max_length=20,
        choices=AppointmentPriority.choices,
        default=AppointmentPriority.HIGH,
    )
    appointment_priority = models.CharField(
        max_length=20,
        choices=AppointmentPriority.choices,
        default=AppointmentPriority.HIGH,
    )
    message = models.TextField()

    class Meta:
        ordering = ["symptom_rule", "id"]

    def __str__(self):
        return f"Escalation for {self.symptom_rule}"
