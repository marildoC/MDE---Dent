from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from accounts.models import UserRole
from ai_support.serializers import AdviceMessageSerializer
from audit import actions as audit_actions
from audit.services import record_audit
from decision_engine.serializers import RiskAssessmentSerializer
from patients.serializers import FollowUpCaseSerializer, PatientProfileSerializer, PatientUserSerializer
from reports.serializers import SymptomReportSerializer

from .models import EscalationCase, EscalationStatus
from .services import update_escalation_status, validate_escalation_transition


class EscalationCaseSerializer(serializers.ModelSerializer):
    patient_detail = PatientProfileSerializer(source="patient", read_only=True)
    follow_up_case_detail = FollowUpCaseSerializer(source="follow_up_case", read_only=True)
    report_detail = SymptomReportSerializer(source="report", read_only=True)
    risk_assessment_detail = RiskAssessmentSerializer(source="risk_assessment", read_only=True)
    advice_message = AdviceMessageSerializer(
        source="risk_assessment.advice_message",
        read_only=True,
    )
    assigned_staff_detail = PatientUserSerializer(source="assigned_staff", read_only=True)

    class Meta:
        model = EscalationCase
        fields = (
            "id",
            "risk_assessment",
            "risk_assessment_detail",
            "report",
            "report_detail",
            "follow_up_case",
            "follow_up_case_detail",
            "patient",
            "patient_detail",
            "status",
            "urgency",
            "assigned_staff",
            "assigned_staff_detail",
            "staff_response",
            "advice_message",
            "resolved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "risk_assessment",
            "risk_assessment_detail",
            "report",
            "report_detail",
            "follow_up_case",
            "follow_up_case_detail",
            "patient",
            "patient_detail",
            "urgency",
            "advice_message",
            "assigned_staff_detail",
            "resolved_at",
            "created_at",
            "updated_at",
        )

    def validate_assigned_staff(self, assigned_staff):
        if assigned_staff and assigned_staff.role not in {UserRole.DENTIST, UserRole.ADMIN}:
            raise serializers.ValidationError("Assigned staff must be DENTIST or ADMIN.")
        return assigned_staff

    def update(self, instance, validated_data):
        status = validated_data.pop("status", None)
        staff_response_changed = "staff_response" in validated_data
        if instance.status == EscalationStatus.CLOSED:
            raise serializers.ValidationError("Closed escalations cannot be updated.")
        if status:
            try:
                validate_escalation_transition(instance.status, status)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"status": exc.message}) from exc

        with transaction.atomic():
            for field, value in validated_data.items():
                setattr(instance, field, value)

            update_fields = list(validated_data.keys())
            if update_fields:
                update_fields.append("updated_at")
                instance.save(update_fields=update_fields)
                record_audit(
                    self.context["request"].user,
                    audit_actions.ESCALATION_UPDATED,
                    instance,
                    {
                        "status": instance.status,
                        "staff_response_changed": staff_response_changed,
                        "assigned_staff_id": instance.assigned_staff_id,
                    },
                )

            if status:
                update_escalation_status(instance, status)

        return instance


class PatientEscalationCaseSerializer(EscalationCaseSerializer):
    class Meta(EscalationCaseSerializer.Meta):
        read_only_fields = EscalationCaseSerializer.Meta.fields


def escalation_status_choices():
    return [choice for choice, _ in EscalationStatus.choices]
