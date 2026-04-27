from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from patients.views import is_staff_or_admin

from .models import Appointment
from .serializers import AppointmentSerializer, PatientAppointmentSerializer


class AppointmentViewSet(ModelViewSet):
    queryset = Appointment.objects.select_related(
        "patient",
        "patient__user",
        "follow_up_case",
        "follow_up_case__workflow",
        "follow_up_case__assigned_staff",
        "escalation_case",
        "escalation_case__report",
        "escalation_case__risk_assessment",
        "escalation_case__risk_assessment__advice_message",
        "risk_assessment",
        "created_by",
    )

    def get_serializer_class(self):
        if is_staff_or_admin(self.request.user):
            return AppointmentSerializer
        return PatientAppointmentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        escalation_case_id = self.request.query_params.get("escalation_case")
        follow_up_case_id = self.request.query_params.get("follow_up_case")

        if escalation_case_id:
            queryset = queryset.filter(escalation_case_id=escalation_case_id)
        if follow_up_case_id:
            queryset = queryset.filter(follow_up_case_id=follow_up_case_id)

        if is_staff_or_admin(self.request.user):
            return queryset
        return queryset.filter(patient__user=self.request.user)

    def create(self, request, *args, **kwargs):
        if not is_staff_or_admin(request.user):
            return Response({"detail": "Only staff/admin can create appointments."}, status=403)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not is_staff_or_admin(request.user):
            return Response({"detail": "Only staff/admin can update appointments."}, status=403)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not is_staff_or_admin(request.user):
            return Response({"detail": "Only staff/admin can update appointments."}, status=403)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "Appointments cannot be deleted."}, status=405)
