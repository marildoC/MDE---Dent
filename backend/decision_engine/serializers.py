from rest_framework import serializers

from ai_support.serializers import AdviceMessageSerializer

from .models import RiskAssessment


class RiskAssessmentSerializer(serializers.ModelSerializer):
    advice_message = AdviceMessageSerializer(read_only=True)
    detected_stage_name = serializers.CharField(source="detected_stage.name", read_only=True)
    patient_username = serializers.CharField(
        source="report.follow_up_case.patient.user.username",
        read_only=True,
    )
    report_day_after_treatment = serializers.IntegerField(
        source="report.day_after_treatment",
        read_only=True,
    )

    class Meta:
        model = RiskAssessment
        fields = (
            "id",
            "advice_message",
            "report",
            "patient_username",
            "report_day_after_treatment",
            "detected_stage",
            "detected_stage_name",
            "matched_rules",
            "risk_level",
            "recommended_action",
            "appointment_priority",
            "explanation",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
