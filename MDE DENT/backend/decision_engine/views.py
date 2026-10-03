from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from accounts.models import UserRole
from patients.views import is_staff_or_admin
from reports.models import SymptomReport

from .models import RiskAssessment
from .serializers import RiskAssessmentSerializer
from .services import assess_report


class RiskAssessmentViewSet(ReadOnlyModelViewSet):
    serializer_class = RiskAssessmentSerializer
    queryset = RiskAssessment.objects.select_related(
        "report",
        "report__follow_up_case",
        "report__follow_up_case__patient",
        "report__follow_up_case__patient__user",
        "report__follow_up_case__workflow",
        "advice_message",
        "detected_stage",
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        report_id = self.request.query_params.get("report")
        if report_id:
            queryset = queryset.filter(report_id=report_id)

        user = self.request.user
        if is_staff_or_admin(user):
            return queryset
        return queryset.filter(report__follow_up_case__patient__user=user)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def evaluate_report(request, report_id):
    report_queryset = SymptomReport.objects.select_related(
        "follow_up_case",
        "follow_up_case__patient",
        "follow_up_case__patient__user",
        "follow_up_case__workflow",
    )
    if is_staff_or_admin(request.user):
        report = report_queryset.filter(id=report_id).first()
    elif request.user.role == UserRole.PATIENT:
        report = report_queryset.filter(
            id=report_id,
            follow_up_case__patient__user=request.user,
        ).first()
    else:
        report = None

    if not report:
        return Response({"detail": "Report not found."}, status=404)

    assessment = assess_report(report)
    return Response(RiskAssessmentSerializer(assessment).data)
