from rest_framework.routers import DefaultRouter

from .views import EscalationCaseViewSet


router = DefaultRouter()
router.register("cases", EscalationCaseViewSet, basename="escalation-case")

urlpatterns = router.urls
