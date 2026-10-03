from rest_framework.routers import DefaultRouter

from .views import (
    AIAdviceBoundaryViewSet,
    CareStageViewSet,
    EscalationRuleViewSet,
    SymptomDefinitionViewSet,
    SymptomRuleViewSet,
    TreatmentWorkflowViewSet,
)


router = DefaultRouter()
router.register("treatment-workflows", TreatmentWorkflowViewSet, basename="treatment-workflow")
router.register("care-stages", CareStageViewSet, basename="care-stage")
router.register("symptom-definitions", SymptomDefinitionViewSet, basename="symptom-definition")
router.register("symptom-rules", SymptomRuleViewSet, basename="symptom-rule")
router.register("advice-boundaries", AIAdviceBoundaryViewSet, basename="advice-boundary")
router.register("escalation-rules", EscalationRuleViewSet, basename="escalation-rule")

urlpatterns = router.urls
