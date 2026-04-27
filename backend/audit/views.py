from rest_framework.viewsets import ReadOnlyModelViewSet

from accounts.permissions import IsAdminRole

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAdminRole]
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.select_related("actor")

    def get_queryset(self):
        queryset = super().get_queryset()
        action = self.request.query_params.get("action")
        target_type = self.request.query_params.get("target_type")
        target_id = self.request.query_params.get("target_id")
        actor = self.request.query_params.get("actor")

        if action:
            queryset = queryset.filter(action=action)
        if target_type:
            queryset = queryset.filter(target_type=target_type)
        if target_id:
            queryset = queryset.filter(target_id=str(target_id))
        if actor:
            queryset = queryset.filter(actor_id=actor)

        return queryset
