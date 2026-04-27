from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.models import UserRole
from accounts.permissions import IsAdminOrDentistReadOnly, IsAdminRole

from .models import (
    AIAdviceBoundary,
    CareStage,
    EscalationRule,
    SymptomDefinition,
    SymptomRule,
    TreatmentWorkflow,
    WorkflowStatus,
)
from .serializers import (
    AIAdviceBoundarySerializer,
    CareStageSerializer,
    EscalationRuleSerializer,
    SymptomDefinitionSerializer,
    SymptomRuleSerializer,
    TreatmentWorkflowSerializer,
)
from .services import validate_workflow, workflow_for_instance, workflow_for_validated_data


class AdminWorkflowViewSet(ModelViewSet):
    permission_classes = [IsAdminRole]

    def _ensure_workflow_can_be_edited(self, workflow):
        if workflow and workflow.status == WorkflowStatus.ACTIVE:
            raise ValidationError("Active workflows cannot be edited directly.")

    def perform_create(self, serializer):
        self._ensure_workflow_can_be_edited(
            workflow_for_validated_data(serializer.validated_data)
        )
        serializer.save()

    def perform_update(self, serializer):
        self._ensure_workflow_can_be_edited(workflow_for_instance(serializer.instance))
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_workflow_can_be_edited(workflow_for_instance(instance))
        instance.delete()


class TreatmentWorkflowViewSet(AdminWorkflowViewSet):
    permission_classes = [IsAdminOrDentistReadOnly]
    queryset = TreatmentWorkflow.objects.select_related("created_by")
    serializer_class = TreatmentWorkflowSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.role == UserRole.DENTIST and not user.is_superuser:
            return queryset.filter(status=WorkflowStatus.ACTIVE)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="validate")
    def validate_workflow_action(self, request, pk=None):
        workflow = self.get_object()
        result = validate_workflow(workflow)

        if result["is_valid"] and workflow.status == WorkflowStatus.DRAFT:
            workflow.status = WorkflowStatus.VALIDATED
            workflow.save(update_fields=["status", "updated_at"])

        return Response(
            {
                **result,
                "status": workflow.status,
            }
        )

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        workflow = self.get_object()
        if workflow.status != WorkflowStatus.VALIDATED:
            return Response(
                {
                    "detail": "Only validated workflows can be activated.",
                    "status": workflow.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = validate_workflow(workflow)
        if not result["is_valid"]:
            return Response(
                {
                    **result,
                    "status": workflow.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        workflow.status = WorkflowStatus.ACTIVE
        workflow.save(update_fields=["status", "updated_at"])
        return Response({"status": workflow.status})

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        workflow = self.get_object()
        if workflow.status != WorkflowStatus.ACTIVE:
            return Response(
                {
                    "detail": "Only active workflows can be archived.",
                    "status": workflow.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        workflow.status = WorkflowStatus.ARCHIVED
        workflow.save(update_fields=["status", "updated_at"])
        return Response({"status": workflow.status})


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
