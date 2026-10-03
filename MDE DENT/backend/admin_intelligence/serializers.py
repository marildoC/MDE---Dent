from rest_framework import serializers


class AdminIntelligenceQuerySerializer(serializers.Serializer):
    question = serializers.CharField(max_length=500, trim_whitespace=True)

    def validate_question(self, value):
        if not value.strip():
            raise serializers.ValidationError("Question is required.")
        return value.strip()
