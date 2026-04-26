from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    AIAdviceBoundary,
    CareStage,
    EscalationRule,
    SymptomDefinition,
    SymptomRule,
    TreatmentWorkflow,
)
from .validators import validate_condition_shape


class TreatmentWorkflowSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = TreatmentWorkflow
        fields = (
            "id",
            "name",
            "treatment_type",
            "status",
            "description",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_by", "created_by_username", "created_at", "updated_at")


class CareStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareStage
        fields = (
            "id",
            "workflow",
            "name",
            "start_day",
            "end_day",
            "description",
            "sort_order",
        )

    def validate(self, attrs):
        start_day = attrs.get("start_day", getattr(self.instance, "start_day", None))
        end_day = attrs.get("end_day", getattr(self.instance, "end_day", None))
        if start_day is not None and end_day is not None and end_day < start_day:
            raise serializers.ValidationError({"end_day": "End day cannot be before start day."})
        return attrs


class SymptomDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SymptomDefinition
        fields = (
            "id",
            "workflow",
            "key",
            "label",
            "data_type",
            "allowed_values",
            "min_value",
            "max_value",
            "description",
            "is_required",
        )


class SymptomRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SymptomRule
        fields = (
            "id",
            "stage",
            "name",
            "condition",
            "risk_level",
            "recommended_action",
            "appointment_priority",
            "explanation",
        )

    def validate_condition(self, value):
        try:
            validate_condition_shape(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value


class AIAdviceBoundarySerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAdviceBoundary
        fields = (
            "id",
            "workflow",
            "stage",
            "allowed_topics",
            "forbidden_topics",
            "required_disclaimer",
        )

    def validate(self, attrs):
        workflow = attrs.get("workflow", getattr(self.instance, "workflow", None))
        stage = attrs.get("stage", getattr(self.instance, "stage", None))
        if stage and workflow and stage.workflow_id != workflow.id:
            raise serializers.ValidationError({"stage": "Stage must belong to the selected workflow."})
        return attrs


class EscalationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscalationRule
        fields = (
            "id",
            "symptom_rule",
            "target_role",
            "urgency",
            "appointment_priority",
            "message",
        )
