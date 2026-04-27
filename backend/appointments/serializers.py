from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from audit import actions as audit_actions
from audit.services import record_audit
from escalations.models import EscalationCase
from escalations.serializers import EscalationCaseSerializer
from patients.serializers import FollowUpCaseSerializer, PatientProfileSerializer, PatientUserSerializer
from workflows.models import AppointmentPriority

from .models import Appointment, AppointmentStatus
from .services import (
    create_appointment_for_escalation,
    default_priority_for_escalation,
    sync_case_status_for_appointment,
    validate_appointment_transition,
)


class AppointmentSerializer(serializers.ModelSerializer):
    patient_detail = PatientProfileSerializer(source="patient", read_only=True)
    follow_up_case_detail = FollowUpCaseSerializer(source="follow_up_case", read_only=True)
    escalation_case_detail = EscalationCaseSerializer(source="escalation_case", read_only=True)
    created_by_detail = PatientUserSerializer(source="created_by", read_only=True)
    risk_level = serializers.CharField(source="risk_assessment.risk_level", read_only=True)
    recommended_action = serializers.CharField(
        source="risk_assessment.recommended_action",
        read_only=True,
    )

    class Meta:
        model = Appointment
        fields = (
            "id",
            "patient",
            "patient_detail",
            "follow_up_case",
            "follow_up_case_detail",
            "escalation_case",
            "escalation_case_detail",
            "risk_assessment",
            "risk_level",
            "recommended_action",
            "priority",
            "status",
            "scheduled_at",
            "notes",
            "created_by",
            "created_by_detail",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "patient",
            "patient_detail",
            "follow_up_case",
            "follow_up_case_detail",
            "escalation_case_detail",
            "risk_assessment",
            "risk_level",
            "recommended_action",
            "created_by",
            "created_by_detail",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {
            "priority": {"required": False},
            "status": {"required": False},
        }

    def validate_priority(self, priority):
        if priority == AppointmentPriority.NONE:
            raise serializers.ValidationError("Appointment priority cannot be NONE.")
        return priority

    def validate_escalation_case(self, escalation_case):
        if hasattr(escalation_case, "appointment"):
            raise serializers.ValidationError("Appointment already exists for this escalation case.")
        return escalation_case

    def create(self, validated_data):
        request = self.context["request"]
        escalation_case = validated_data["escalation_case"]
        try:
            return create_appointment_for_escalation(
                escalation_case=escalation_case,
                created_by=request.user,
                priority=validated_data.get("priority"),
                scheduled_at=validated_data.get("scheduled_at"),
                notes=validated_data.get("notes", ""),
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message)

    def update(self, instance, validated_data):
        validated_data.pop("escalation_case", None)
        if instance.status in {AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED}:
            raise serializers.ValidationError("Completed or cancelled appointments cannot be updated.")

        previous_status = instance.status
        next_status = validated_data.get("status")
        if next_status:
            try:
                validate_appointment_transition(instance.status, next_status)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"status": exc.message}) from exc

        try:
            with transaction.atomic():
                for field, value in validated_data.items():
                    setattr(instance, field, value)
                instance.full_clean()
                instance.save()
                if next_status:
                    sync_case_status_for_appointment(instance)
                record_audit(
                    self.context["request"].user,
                    audit_actions.APPOINTMENT_UPDATED,
                    instance,
                    {
                        "previous_status": previous_status,
                        "new_status": instance.status,
                        "priority": instance.priority,
                        "scheduled_at": instance.scheduled_at.isoformat()
                        if instance.scheduled_at
                        else None,
                        "escalation_case_id": instance.escalation_case_id,
                        "follow_up_case_id": instance.follow_up_case_id,
                    },
                )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message) from exc
        return instance


class PatientAppointmentSerializer(AppointmentSerializer):
    class Meta(AppointmentSerializer.Meta):
        read_only_fields = AppointmentSerializer.Meta.fields


class AppointmentCreateDefaultsSerializer(serializers.Serializer):
    escalation_case = serializers.PrimaryKeyRelatedField(
        queryset=EscalationCase.objects.select_related("risk_assessment")
    )

    def to_representation(self, instance):
        return {
            "escalation_case": instance.id,
            "priority": default_priority_for_escalation(instance),
        }
