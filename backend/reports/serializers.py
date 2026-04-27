from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from accounts.models import UserRole
from audit import actions as audit_actions
from audit.services import record_audit
from decision_engine.serializers import RiskAssessmentSerializer
from patients.lifecycle import validate_reportable_case
from patients.serializers import FollowUpCaseSerializer

from .models import SymptomReport


class SymptomReportSerializer(serializers.ModelSerializer):
    follow_up_case_detail = FollowUpCaseSerializer(source="follow_up_case", read_only=True)
    risk_assessment = RiskAssessmentSerializer(read_only=True)
    submitted_by_username = serializers.CharField(source="submitted_by.username", read_only=True)

    class Meta:
        model = SymptomReport
        fields = (
            "id",
            "follow_up_case",
            "follow_up_case_detail",
            "risk_assessment",
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
            "risk_assessment",
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

        try:
            validate_reportable_case(follow_up_case)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message) from exc

        return follow_up_case

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None

        if self.instance is None and user and user.role != UserRole.PATIENT:
            raise serializers.ValidationError("Only patients can submit symptom reports.")

        return attrs

    def create(self, validated_data):
        from decision_engine.services import assess_report

        request = self.context["request"]
        report = SymptomReport.objects.create(submitted_by=request.user, **validated_data)
        record_audit(
            request.user,
            audit_actions.SYMPTOM_REPORT_SUBMITTED,
            report,
            {
                "follow_up_case_id": report.follow_up_case_id,
                "patient_id": report.follow_up_case.patient_id,
                "day_after_treatment": report.day_after_treatment,
                "report_id": report.id,
            },
        )
        assess_report(report)
        return report
