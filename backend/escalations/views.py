from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from patients.views import is_staff_or_admin

from .models import EscalationCase
from .serializers import EscalationCaseSerializer, PatientEscalationCaseSerializer


class EscalationCaseViewSet(ModelViewSet):
    queryset = EscalationCase.objects.select_related(
        "risk_assessment",
        "risk_assessment__advice_message",
        "risk_assessment__detected_stage",
        "report",
        "report__submitted_by",
        "follow_up_case",
        "follow_up_case__workflow",
        "follow_up_case__assigned_staff",
        "patient",
        "patient__user",
        "assigned_staff",
    )

    def get_serializer_class(self):
        if is_staff_or_admin(self.request.user):
            return EscalationCaseSerializer
        return PatientEscalationCaseSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        report_id = self.request.query_params.get("report")
        follow_up_case_id = self.request.query_params.get("follow_up_case")

        if report_id:
            queryset = queryset.filter(report_id=report_id)
        if follow_up_case_id:
            queryset = queryset.filter(follow_up_case_id=follow_up_case_id)

        if is_staff_or_admin(self.request.user):
            return queryset
        return queryset.filter(patient__user=self.request.user)

    def create(self, request, *args, **kwargs):
        return Response({"detail": "Escalations are created by risk assessment."}, status=405)

    def update(self, request, *args, **kwargs):
        if not is_staff_or_admin(request.user):
            return Response({"detail": "Only staff/admin can update escalation cases."}, status=403)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not is_staff_or_admin(request.user):
            return Response({"detail": "Only staff/admin can update escalation cases."}, status=403)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "Escalation cases cannot be deleted."}, status=405)
