from rest_framework import serializers

from accounts.models import User, UserRole
from workflows.models import WorkflowStatus
from workflows.serializers import TreatmentWorkflowSerializer

from .models import FollowUpCase, PatientProfile


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
