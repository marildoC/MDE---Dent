from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    FollowUpCaseViewSet,
    PatientProfileViewSet,
    PatientUserViewSet,
    my_active_case,
)


router = DefaultRouter()
router.register("profiles", PatientProfileViewSet, basename="profile")
router.register("follow-up-cases", FollowUpCaseViewSet, basename="follow-up-case")
router.register("patient-users", PatientUserViewSet, basename="patient-user")

urlpatterns = [
    path("my-active-case/", my_active_case, name="my-active-case"),
    *router.urls,
]
