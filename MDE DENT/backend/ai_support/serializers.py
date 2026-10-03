from rest_framework import serializers

from .models import AdviceMessage


class AdviceMessageSerializer(serializers.ModelSerializer):
    patient_username = serializers.CharField(
        source="risk_assessment.report.follow_up_case.patient.user.username",
        read_only=True,
    )
    risk_level = serializers.CharField(source="risk_assessment.risk_level", read_only=True)

    class Meta:
        model = AdviceMessage
        fields = (
            "id",
            "risk_assessment",
            "patient_username",
            "risk_level",
            "message",
            "message_type",
            "source",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
