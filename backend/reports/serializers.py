from rest_framework import serializers

from accounts.models import UserRole
from patients.models import FollowUpCaseStatus
from patients.serializers import FollowUpCaseSerializer

from .models import SymptomReport


class SymptomReportSerializer(serializers.ModelSerializer):
    follow_up_case_detail = FollowUpCaseSerializer(source="follow_up_case", read_only=True)
    submitted_by_username = serializers.CharField(source="submitted_by.username", read_only=True)

    class Meta:
        model = SymptomReport
        fields = (
            "id",
            "follow_up_case",
            "follow_up_case_detail",
            "submitted_by",
            "submitted_by_username",
            "day_after_treatment",
            "pain_level",
            "swelling",
            "bleeding",
            "fever",
            "bad_smell",
            "notes",
            "image",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "follow_up_case_detail",
            "submitted_by",
            "submitted_by_username",
            "day_after_treatment",
            "created_at",
            "updated_at",
        )

    def validate_follow_up_case(self, follow_up_case):
        request = self.context.get("request")
        user = request.user if request else None

        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Authentication is required.")

        if user.role != UserRole.PATIENT:
            raise serializers.ValidationError("Only patients can submit symptom reports.")

        if follow_up_case.patient.user_id != user.id:
            raise serializers.ValidationError("Report must belong to your own follow-up case.")

        if follow_up_case.status in {FollowUpCaseStatus.CLOSED, FollowUpCaseStatus.RESOLVED}:
            raise serializers.ValidationError(
                "Reports cannot be submitted for closed or resolved cases."
            )

        return follow_up_case

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None

        if self.instance is None and user and user.role != UserRole.PATIENT:
            raise serializers.ValidationError("Only patients can submit symptom reports.")

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        return SymptomReport.objects.create(submitted_by=request.user, **validated_data)
