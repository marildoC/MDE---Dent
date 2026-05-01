from rest_framework import serializers

from ai_support.serializers import AdviceMessageSerializer
from workflows.condition_formatting import format_condition
from workflows.models import SymptomRule

from .models import RiskAssessment


class RiskAssessmentSerializer(serializers.ModelSerializer):
    advice_message = AdviceMessageSerializer(read_only=True)
    detected_stage_name = serializers.CharField(source="detected_stage.name", read_only=True)
    matched_rule_details = serializers.SerializerMethodField()
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
            "matched_rule_details",
            "risk_level",
            "recommended_action",
            "appointment_priority",
            "explanation",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_matched_rule_details(self, obj):
        if not isinstance(obj.matched_rules, list):
            return []

        matched_rule_ids = [
            item.get("id")
            for item in obj.matched_rules
            if isinstance(item, dict) and item.get("id") is not None
        ]
        rules_by_id = SymptomRule.objects.in_bulk(matched_rule_ids)

        details = []
        for item in obj.matched_rules:
            if not isinstance(item, dict):
                continue

            rule_id = item.get("id")
            rule = rules_by_id.get(rule_id)
            condition = rule.condition if rule else item.get("condition")
            details.append(
                {
                    "id": rule_id,
                    "name": item.get("name") or (rule.name if rule else "Matched rule"),
                    "condition_text": format_condition(condition),
                    "risk_level": item.get("risk_level") or (rule.risk_level if rule else ""),
                    "recommended_action": item.get("recommended_action")
                    or (rule.recommended_action if rule else ""),
                    "appointment_priority": item.get("appointment_priority")
                    or (rule.appointment_priority if rule else ""),
                }
            )

        return details
