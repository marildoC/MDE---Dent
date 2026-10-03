from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AdviceMessageViewSet, generate_advice

router = DefaultRouter()
router.register("advice-messages", AdviceMessageViewSet, basename="advice-message")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "risk-assessments/<int:assessment_id>/generate-advice/",
        generate_advice,
        name="generate-advice",
    ),
]
