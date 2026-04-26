from rest_framework.test import APITestCase

from accounts.models import User, UserRole

from .models import (
    AIAdviceBoundary,
    AppointmentPriority,
    CareStage,
    EscalationRule,
    RecommendedAction,
    RiskLevel,
    SymptomDataType,
    SymptomDefinition,
    SymptomRule,
    TreatmentType,
    TreatmentWorkflow,
    WorkflowStatus,
)


VALID_CONDITION = {
    "all": [
        {"field": "pain_level", "operator": ">=", "value": 8},
        {"field": "bad_smell", "operator": "=", "value": True},
    ]
}


class WorkflowAPITests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            password="testpass123",
            role=UserRole.ADMIN,
        )
        self.patient = User.objects.create_user(
            username="patient",
            password="testpass123",
            role=UserRole.PATIENT,
        )

    def test_admin_can_create_workflow(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/api/workflows/treatment-workflows/",
            {
                "name": "Post-Extraction Follow-Up",
                "treatment_type": TreatmentType.POST_EXTRACTION,
                "status": WorkflowStatus.DRAFT,
                "description": "Structured post-extraction follow-up workflow.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(TreatmentWorkflow.objects.count(), 1)
        self.assertEqual(TreatmentWorkflow.objects.get().created_by, self.admin)

    def test_non_admin_cannot_create_workflow(self):
        self.client.force_authenticate(self.patient)

        response = self.client.post(
            "/api/workflows/treatment-workflows/",
            {"name": "Blocked", "treatment_type": TreatmentType.POST_EXTRACTION},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(TreatmentWorkflow.objects.count(), 0)

    def test_workflow_related_objects_can_be_created(self):
        self.client.force_authenticate(self.admin)
        workflow = TreatmentWorkflow.objects.create(
            name="Post-Extraction Follow-Up",
            treatment_type=TreatmentType.POST_EXTRACTION,
            created_by=self.admin,
        )

        stage_response = self.client.post(
            "/api/workflows/care-stages/",
            {
                "workflow": workflow.id,
                "name": "Day 4-7",
                "start_day": 4,
                "end_day": 7,
                "sort_order": 1,
            },
            format="json",
        )
        symptom_response = self.client.post(
            "/api/workflows/symptom-definitions/",
            {
                "workflow": workflow.id,
                "key": "pain_level",
                "label": "Pain level",
                "data_type": SymptomDataType.INTEGER,
                "min_value": 0,
                "max_value": 10,
            },
            format="json",
        )
        rule_response = self.client.post(
            "/api/workflows/symptom-rules/",
            {
                "stage": stage_response.data["id"],
                "name": "Severe pain with bad smell",
                "condition": VALID_CONDITION,
                "risk_level": RiskLevel.HIGH,
                "recommended_action": RecommendedAction.ESCALATE_TO_DENTIST,
                "appointment_priority": AppointmentPriority.HIGH,
                "explanation": "Severe pain with bad smell is high risk.",
            },
            format="json",
        )
        boundary_response = self.client.post(
            "/api/workflows/advice-boundaries/",
            {
                "workflow": workflow.id,
                "stage": stage_response.data["id"],
                "allowed_topics": ["aftercare reminders"],
                "forbidden_topics": ["diagnosis", "prescription"],
                "required_disclaimer": "Contact the clinic if symptoms worsen.",
            },
            format="json",
        )
        escalation_response = self.client.post(
            "/api/workflows/escalation-rules/",
            {
                "symptom_rule": rule_response.data["id"],
                "target_role": UserRole.DENTIST,
                "urgency": AppointmentPriority.HIGH,
                "appointment_priority": AppointmentPriority.HIGH,
                "message": "Dentist review required.",
            },
            format="json",
        )

        self.assertEqual(stage_response.status_code, 201)
        self.assertEqual(symptom_response.status_code, 201)
        self.assertEqual(rule_response.status_code, 201)
        self.assertEqual(boundary_response.status_code, 201)
        self.assertEqual(escalation_response.status_code, 201)
        self.assertEqual(CareStage.objects.count(), 1)
        self.assertEqual(SymptomDefinition.objects.count(), 1)
        self.assertEqual(SymptomRule.objects.count(), 1)
        self.assertEqual(AIAdviceBoundary.objects.count(), 1)
        self.assertEqual(EscalationRule.objects.count(), 1)

    def test_invalid_condition_shape_is_rejected(self):
        self.client.force_authenticate(self.admin)
        workflow = TreatmentWorkflow.objects.create(
            name="Post-Extraction Follow-Up",
            treatment_type=TreatmentType.POST_EXTRACTION,
            created_by=self.admin,
        )
        stage = CareStage.objects.create(
            workflow=workflow,
            name="Day 4-7",
            start_day=4,
            end_day=7,
        )

        response = self.client.post(
            "/api/workflows/symptom-rules/",
            {
                "stage": stage.id,
                "name": "Invalid condition",
                "condition": {"raw": "pain_level >= 8"},
                "risk_level": RiskLevel.HIGH,
                "recommended_action": RecommendedAction.ESCALATE_TO_DENTIST,
                "appointment_priority": AppointmentPriority.HIGH,
                "explanation": "Invalid shape should be rejected.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(SymptomRule.objects.count(), 0)

    def test_escalation_target_cannot_be_patient(self):
        self.client.force_authenticate(self.admin)
        workflow = TreatmentWorkflow.objects.create(
            name="Post-Extraction Follow-Up",
            treatment_type=TreatmentType.POST_EXTRACTION,
            created_by=self.admin,
        )
        stage = CareStage.objects.create(
            workflow=workflow,
            name="Day 4-7",
            start_day=4,
            end_day=7,
        )
        rule = SymptomRule.objects.create(
            stage=stage,
            name="High risk",
            condition=VALID_CONDITION,
            risk_level=RiskLevel.HIGH,
            recommended_action=RecommendedAction.ESCALATE_TO_DENTIST,
            appointment_priority=AppointmentPriority.HIGH,
            explanation="High risk.",
        )

        response = self.client.post(
            "/api/workflows/escalation-rules/",
            {
                "symptom_rule": rule.id,
                "target_role": UserRole.PATIENT,
                "urgency": AppointmentPriority.HIGH,
                "appointment_priority": AppointmentPriority.HIGH,
                "message": "Invalid target.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(EscalationRule.objects.count(), 0)
