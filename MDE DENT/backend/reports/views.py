from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.models import UserRole
from patients.views import is_staff_or_admin

from .models import SymptomReport
from .serializers import SymptomReportSerializer


class SymptomReportViewSet(ModelViewSet):
    serializer_class = SymptomReportSerializer
    queryset = SymptomReport.objects.select_related(
        "follow_up_case",
        "follow_up_case__patient",
        "follow_up_case__patient__user",
        "follow_up_case__workflow",
        "follow_up_case__assigned_staff",
        "risk_assessment",
        "risk_assessment__advice_message",
        "risk_assessment__detected_stage",
        "submitted_by",
    ).prefetch_related("follow_up_case__workflow__symptom_definitions")

    def get_queryset(self):
        queryset = super().get_queryset()
        follow_up_case_id = self.request.query_params.get("follow_up_case")
        if follow_up_case_id:
            queryset = queryset.filter(follow_up_case_id=follow_up_case_id)

        user = self.request.user
        if is_staff_or_admin(user):
            return queryset
        return queryset.filter(follow_up_case__patient__user=user)

    def create(self, request, *args, **kwargs):
        if request.user.role != UserRole.PATIENT:
            return Response({"detail": "Only patients can submit symptom reports."}, status=403)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return Response({"detail": "Symptom reports cannot be updated."}, status=405)

    def partial_update(self, request, *args, **kwargs):
        return Response({"detail": "Symptom reports cannot be updated."}, status=405)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "Symptom reports cannot be deleted."}, status=405)
