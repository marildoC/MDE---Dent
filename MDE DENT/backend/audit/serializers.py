from rest_framework import serializers

from accounts.serializers import CurrentUserSerializer

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_detail = CurrentUserSerializer(source="actor", read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "actor",
            "actor_detail",
            "action",
            "target_type",
            "target_id",
            "target_repr",
            "details",
            "created_at",
        )
        read_only_fields = fields
