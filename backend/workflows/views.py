from rest_framework.viewsets import ModelViewSet

from accounts.permissions import IsAdminRole

from .models import (
    AIAdviceBoundary,
    CareStage,
    EscalationRule,
    SymptomDefinition,
    SymptomRule,
    TreatmentWorkflow,
)
from .serializers import (
    AIAdviceBoundarySerializer,
    CareStageSerializer,
    EscalationRuleSerializer,
    SymptomDefinitionSerializer,
    SymptomRuleSerializer,
    TreatmentWorkflowSerializer,
)


class AdminWorkflowViewSet(ModelViewSet):
    permission_classes = [IsAdminRole]


class TreatmentWorkflowViewSet(AdminWorkflowViewSet):
    queryset = TreatmentWorkflow.objects.select_related("created_by")
    serializer_class = TreatmentWorkflowSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class CareStageViewSet(AdminWorkflowViewSet):
    queryset = CareStage.objects.select_related("workflow")
    serializer_class = CareStageSerializer


class SymptomDefinitionViewSet(AdminWorkflowViewSet):
    queryset = SymptomDefinition.objects.select_related("workflow")
    serializer_class = SymptomDefinitionSerializer


class SymptomRuleViewSet(AdminWorkflowViewSet):
    queryset = SymptomRule.objects.select_related("stage", "stage__workflow")
    serializer_class = SymptomRuleSerializer


class AIAdviceBoundaryViewSet(AdminWorkflowViewSet):
    queryset = AIAdviceBoundary.objects.select_related("workflow", "stage")
    serializer_class = AIAdviceBoundarySerializer


class EscalationRuleViewSet(AdminWorkflowViewSet):
    queryset = EscalationRule.objects.select_related("symptom_rule", "symptom_rule__stage")
    serializer_class = EscalationRuleSerializer
