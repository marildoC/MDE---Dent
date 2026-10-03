from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RiskAssessmentViewSet, evaluate_report

router = DefaultRouter()
router.register("risk-assessments", RiskAssessmentViewSet, basename="risk-assessment")

urlpatterns = [
    path("", include(router.urls)),
    path("reports/<int:report_id>/evaluate/", evaluate_report, name="evaluate-report"),
]
