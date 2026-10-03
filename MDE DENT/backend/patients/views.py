from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from accounts.models import User, UserRole

from .models import FollowUpCase, FollowUpCaseStatus, PatientProfile
from .serializers import (
    FollowUpCaseSerializer,
    PatientProfileSerializer,
    PatientProfileWithUserSerializer,
    PatientUserSerializer,
)


def is_staff_or_admin(user):
    return user.is_authenticated and user.role in {UserRole.DENTIST, UserRole.ADMIN}


class StaffWritePatientReadMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if is_staff_or_admin(user):
            return queryset
        return queryset.filter(user=user) if self.basename == "profile" else queryset.filter(patient__user=user)

    def _can_write(self):
        return is_staff_or_admin(self.request.user)

    def create(self, request, *args, **kwargs):
        if not self._can_write():
            return Response({"detail": "Only staff/admin can create this resource."}, status=403)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not self._can_write():
            return Response({"detail": "Only staff/admin can update this resource."}, status=403)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not self._can_write():
            return Response({"detail": "Only staff/admin can update this resource."}, status=403)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not self._can_write():
            return Response({"detail": "Only staff/admin can delete this resource."}, status=403)
        return super().destroy(request, *args, **kwargs)


class PatientProfileViewSet(StaffWritePatientReadMixin, ModelViewSet):
    basename = "profile"
    queryset = PatientProfile.objects.select_related("user")
    serializer_class = PatientProfileSerializer


class FollowUpCaseViewSet(StaffWritePatientReadMixin, ModelViewSet):
    basename = "follow-up-case"
    queryset = FollowUpCase.objects.select_related(
        "patient",
        "patient__user",
        "workflow",
        "assigned_staff",
    ).prefetch_related("workflow__symptom_definitions")
    serializer_class = FollowUpCaseSerializer


class PatientUserViewSet(ReadOnlyModelViewSet):
    queryset = User.objects.filter(role=UserRole.PATIENT).order_by("username", "id")
    serializer_class = PatientUserSerializer

    def get_queryset(self):
        if is_staff_or_admin(self.request.user):
            return super().get_queryset()
        return super().get_queryset().filter(id=self.request.user.id)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_active_case(request):
    if request.user.role != UserRole.PATIENT:
        return Response(None)

    case = (
        FollowUpCase.objects.select_related(
            "patient",
            "patient__user",
            "workflow",
            "assigned_staff",
        )
        .prefetch_related("workflow__symptom_definitions")
        .filter(patient__user=request.user)
        .exclude(status=FollowUpCaseStatus.CLOSED)
        .order_by("-treatment_date", "-id")
        .first()
    )

    if not case:
        return Response(None)

    return Response(FollowUpCaseSerializer(case).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_profile_with_user(request):
    if not is_staff_or_admin(request.user):
        return Response({"detail": "Only staff/admin can create patient profiles."}, status=403)

    serializer = PatientProfileWithUserSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    profile = serializer.save()
    return Response(
        PatientProfileSerializer(profile, context={"request": request}).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_follow_up_cases(request):
    if request.user.role != UserRole.PATIENT:
        return Response([])

    cases = (
        FollowUpCase.objects.select_related(
            "patient",
            "patient__user",
            "workflow",
            "assigned_staff",
        )
        .prefetch_related("workflow__symptom_definitions")
        .filter(patient__user=request.user)
        .exclude(status=FollowUpCaseStatus.CLOSED)
        .order_by("-treatment_date", "-id")
    )

    return Response(FollowUpCaseSerializer(cases, many=True).data)
