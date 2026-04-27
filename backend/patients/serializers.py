from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from accounts.models import User, UserRole
from audit import actions as audit_actions
from audit.services import record_audit
from workflows.models import WorkflowStatus
from workflows.serializers import TreatmentWorkflowSerializer

from .lifecycle import validate_follow_up_case_transition
from .models import FollowUpCase, FollowUpCaseStatus, PatientProfile


class PatientUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role")
        read_only_fields = fields


class PatientProfileSerializer(serializers.ModelSerializer):
    user_detail = PatientUserSerializer(source="user", read_only=True)

    class Meta:
        model = PatientProfile
        fields = (
            "id",
            "user",
            "user_detail",
            "phone",
            "dental_notes",
            "allergies",
            "emergency_contact",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("user_detail", "created_at", "updated_at")

    def validate_user(self, user):
        if user.role != UserRole.PATIENT:
            raise serializers.ValidationError("Patient profile user must have PATIENT role.")
        return user


class FollowUpCaseSerializer(serializers.ModelSerializer):
    patient_detail = PatientProfileSerializer(source="patient", read_only=True)
    workflow_detail = TreatmentWorkflowSerializer(source="workflow", read_only=True)
    assigned_staff_detail = PatientUserSerializer(source="assigned_staff", read_only=True)

    class Meta:
        model = FollowUpCase
        fields = (
            "id",
            "patient",
            "patient_detail",
            "workflow",
            "workflow_detail",
            "treatment_date",
            "status",
            "assigned_staff",
            "assigned_staff_detail",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "patient_detail",
            "workflow_detail",
            "assigned_staff_detail",
            "created_at",
            "updated_at",
        )

    def validate_workflow(self, workflow):
        if workflow.status != WorkflowStatus.ACTIVE:
            raise serializers.ValidationError("Only ACTIVE workflows can be assigned to patients.")
        return workflow

    def validate_assigned_staff(self, assigned_staff):
        if assigned_staff and assigned_staff.role not in {UserRole.DENTIST, UserRole.ADMIN}:
            raise serializers.ValidationError("Assigned staff must be DENTIST or ADMIN.")
        return assigned_staff

    def validate(self, attrs):
        status = attrs.get("status")
        if self.instance is None and status and status not in {
            FollowUpCaseStatus.CREATED,
            FollowUpCaseStatus.ACTIVE,
        }:
            raise serializers.ValidationError(
                {"status": "Follow-up cases must start as CREATED or ACTIVE."}
            )
        if self.instance is not None and status:
            try:
                validate_follow_up_case_transition(self.instance.status, status)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"status": exc.message}) from exc
        return attrs

    def create(self, validated_data):
        follow_up_case = super().create(validated_data)
        request = self.context.get("request")
        record_audit(
            request.user if request else None,
            audit_actions.FOLLOW_UP_CASE_CREATED,
            follow_up_case,
            {
                "patient_id": follow_up_case.patient_id,
                "workflow_id": follow_up_case.workflow_id,
                "assigned_staff_id": follow_up_case.assigned_staff_id,
                "status": follow_up_case.status,
            },
        )
        return follow_up_case

    def update(self, instance, validated_data):
        previous_status = instance.status
        follow_up_case = super().update(instance, validated_data)
        next_status = follow_up_case.status

        if previous_status != next_status:
            request = self.context.get("request")
            record_audit(
                request.user if request else None,
                audit_actions.FOLLOW_UP_CASE_STATUS_CHANGED,
                follow_up_case,
                {
                    "patient_id": follow_up_case.patient_id,
                    "workflow_id": follow_up_case.workflow_id,
                    "previous_status": previous_status,
                    "new_status": next_status,
                },
            )

        return follow_up_case
