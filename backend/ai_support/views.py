from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from accounts.models import UserRole
from decision_engine.models import RiskAssessment
from patients.views import is_staff_or_admin

from .models import AdviceMessage
from .serializers import AdviceMessageSerializer
from .services import generate_advice_for_assessment


class AdviceMessageViewSet(ReadOnlyModelViewSet):
    serializer_class = AdviceMessageSerializer
    queryset = AdviceMessage.objects.select_related(
        "risk_assessment",
        "risk_assessment__report",
        "risk_assessment__report__follow_up_case",
        "risk_assessment__report__follow_up_case__patient",
        "risk_assessment__report__follow_up_case__patient__user",
        "risk_assessment__report__follow_up_case__workflow",
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        assessment_id = self.request.query_params.get("risk_assessment")
        if assessment_id:
            queryset = queryset.filter(risk_assessment_id=assessment_id)

        user = self.request.user
        if is_staff_or_admin(user):
            return queryset
        return queryset.filter(risk_assessment__report__follow_up_case__patient__user=user)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_advice(request, assessment_id):
    assessment_queryset = RiskAssessment.objects.select_related(
        "report",
        "report__follow_up_case",
        "report__follow_up_case__patient",
        "report__follow_up_case__patient__user",
        "report__follow_up_case__workflow",
        "detected_stage",
        "advice_message",
    )

    if is_staff_or_admin(request.user):
        assessment = assessment_queryset.filter(id=assessment_id).first()
    elif request.user.role == UserRole.PATIENT:
        assessment = assessment_queryset.filter(
            id=assessment_id,
            report__follow_up_case__patient__user=request.user,
        ).first()
    else:
        assessment = None

    if not assessment:
        return Response({"detail": "Risk assessment not found."}, status=404)

    advice = generate_advice_for_assessment(assessment)
    return Response(AdviceMessageSerializer(advice).data)
