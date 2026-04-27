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
from .services import validate_workflow


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
        self.dentist = User.objects.create_user(
            username="dentist",
            password="testpass123",
            role=UserRole.DENTIST,
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

    def test_dentist_can_list_only_active_workflows_read_only(self):
        active_workflow = TreatmentWorkflow.objects.create(
            name="Active workflow",
            treatment_type=TreatmentType.POST_EXTRACTION,
            status=WorkflowStatus.ACTIVE,
            created_by=self.admin,
        )
        TreatmentWorkflow.objects.create(
            name="Draft workflow",
            treatment_type=TreatmentType.POST_EXTRACTION,
            status=WorkflowStatus.DRAFT,
            created_by=self.admin,
        )
        self.client.force_authenticate(self.dentist)

        list_response = self.client.get("/api/workflows/treatment-workflows/")
        create_response = self.client.post(
            "/api/workflows/treatment-workflows/",
            {"name": "Blocked", "treatment_type": TreatmentType.POST_EXTRACTION},
            format="json",
        )
        update_response = self.client.patch(
            f"/api/workflows/treatment-workflows/{active_workflow.id}/",
            {"description": "Blocked"},
            format="json",
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual([item["id"] for item in list_response.data], [active_workflow.id])
        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(update_response.status_code, 403)

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


class WorkflowValidationLifecycleTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="workflow-admin",
            password="testpass123",
            role=UserRole.ADMIN,
        )
        self.patient = User.objects.create_user(
            username="workflow-patient",
            password="testpass123",
            role=UserRole.PATIENT,
        )

    def _workflow(self, name="Post-Extraction Follow-Up"):
        return TreatmentWorkflow.objects.create(
            name=name,
            treatment_type=TreatmentType.POST_EXTRACTION,
            created_by=self.admin,
        )

    def _complete_workflow(self):
        workflow = self._workflow()
        stage = CareStage.objects.create(
            workflow=workflow,
            name="Day 4-7",
            start_day=4,
            end_day=7,
        )
        SymptomDefinition.objects.create(
            workflow=workflow,
            key="pain_level",
            label="Pain level",
            data_type=SymptomDataType.INTEGER,
            min_value=0,
            max_value=10,
        )
        SymptomDefinition.objects.create(
            workflow=workflow,
            key="bad_smell",
            label="Bad smell",
            data_type=SymptomDataType.BOOLEAN,
        )
        rule = SymptomRule.objects.create(
            stage=stage,
            name="Severe pain with bad smell",
            condition=VALID_CONDITION,
            risk_level=RiskLevel.HIGH,
            recommended_action=RecommendedAction.ESCALATE_TO_DENTIST,
            appointment_priority=AppointmentPriority.HIGH,
            explanation="Severe pain with bad smell is high risk.",
        )
        AIAdviceBoundary.objects.create(
            workflow=workflow,
            allowed_topics=["aftercare reminders"],
            forbidden_topics=["diagnosis", "prescription"],
            required_disclaimer="Contact the clinic if symptoms worsen.",
        )
        EscalationRule.objects.create(
            symptom_rule=rule,
            target_role=UserRole.DENTIST,
            urgency=AppointmentPriority.HIGH,
            appointment_priority=AppointmentPriority.HIGH,
            message="Dentist review required.",
        )
        return workflow

    def test_empty_workflow_fails_validation(self):
        workflow = self._workflow()

        result = validate_workflow(workflow)

        self.assertFalse(result["is_valid"])
        self.assertIn("Workflow must have at least one care stage.", result["errors"])
        self.assertIn("Workflow must have at least one symptom definition.", result["errors"])
        self.assertIn("Workflow must have at least one symptom rule.", result["errors"])

    def test_overlapping_stages_fail_validation(self):
        workflow = self._workflow()
        CareStage.objects.create(workflow=workflow, name="Day 0-3", start_day=0, end_day=3)
        CareStage.objects.create(workflow=workflow, name="Day 3-7", start_day=3, end_day=7)

        result = validate_workflow(workflow)

        self.assertFalse(result["is_valid"])
        self.assertIn("Care stages 'Day 0-3' and 'Day 3-7' overlap.", result["errors"])

    def test_unknown_condition_field_fails_validation(self):
        workflow = self._workflow()
        stage = CareStage.objects.create(workflow=workflow, name="Day 4-7", start_day=4, end_day=7)
        SymptomDefinition.objects.create(
            workflow=workflow,
            key="pain_level",
            label="Pain level",
            data_type=SymptomDataType.INTEGER,
        )
        SymptomRule.objects.create(
            stage=stage,
            name="Unknown field",
            condition={"all": [{"field": "unknown_symptom", "operator": "=", "value": True}]},
            risk_level=RiskLevel.LOW,
            recommended_action=RecommendedAction.CONTINUE_MONITORING,
            explanation="Unknown field.",
        )

        result = validate_workflow(workflow)

        self.assertFalse(result["is_valid"])
        self.assertIn(
            "Rule 'Unknown field' references unknown condition field 'unknown_symptom'.",
            result["errors"],
        )

    def test_high_rule_without_escalation_fails_validation(self):
        workflow = self._workflow()
        stage = CareStage.objects.create(workflow=workflow, name="Day 4-7", start_day=4, end_day=7)
        SymptomDefinition.objects.create(
            workflow=workflow,
            key="pain_level",
            label="Pain level",
            data_type=SymptomDataType.INTEGER,
        )
        SymptomRule.objects.create(
            stage=stage,
            name="High pain",
            condition={"all": [{"field": "pain_level", "operator": ">=", "value": 8}]},
            risk_level=RiskLevel.HIGH,
            recommended_action=RecommendedAction.ESCALATE_TO_DENTIST,
            appointment_priority=AppointmentPriority.HIGH,
            explanation="High pain.",
        )

        result = validate_workflow(workflow)

        self.assertFalse(result["is_valid"])
        self.assertIn("HIGH rule 'High pain' must have an escalation rule.", result["errors"])

    def test_missing_ai_boundary_fails_validation(self):
        workflow = self._complete_workflow()
        workflow.advice_boundaries.all().delete()

        result = validate_workflow(workflow)

        self.assertFalse(result["is_valid"])
        self.assertIn(
            "Workflow-level AI advice boundary must forbid diagnosis and prescription.",
            result["errors"],
        )

    def test_complete_workflow_passes_validation(self):
        workflow = self._complete_workflow()

        result = validate_workflow(workflow)

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["errors"], [])

    def test_validate_action_moves_valid_draft_to_validated(self):
        workflow = self._complete_workflow()
        self.client.force_authenticate(self.admin)

        response = self.client.post(f"/api/workflows/treatment-workflows/{workflow.id}/validate/")

        workflow.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_valid"])
        self.assertEqual(workflow.status, WorkflowStatus.VALIDATED)

    def test_invalid_workflow_cannot_be_validated(self):
        workflow = self._workflow()
        self.client.force_authenticate(self.admin)

        response = self.client.post(f"/api/workflows/treatment-workflows/{workflow.id}/validate/")

        workflow.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_valid"])
        self.assertEqual(workflow.status, WorkflowStatus.DRAFT)

    def test_validated_workflow_can_be_activated_and_archived(self):
        workflow = self._complete_workflow()
        workflow.status = WorkflowStatus.VALIDATED
        workflow.save(update_fields=["status"])
        self.client.force_authenticate(self.admin)

        activate_response = self.client.post(
            f"/api/workflows/treatment-workflows/{workflow.id}/activate/"
        )
        workflow.refresh_from_db()
        archive_response = self.client.post(
            f"/api/workflows/treatment-workflows/{workflow.id}/archive/"
        )

        self.assertEqual(activate_response.status_code, 200)
        self.assertEqual(activate_response.data["status"], WorkflowStatus.ACTIVE)
        self.assertEqual(archive_response.status_code, 200)
        workflow.refresh_from_db()
        self.assertEqual(workflow.status, WorkflowStatus.ARCHIVED)

    def test_invalid_stale_validated_workflow_cannot_be_activated(self):
        workflow = self._workflow()
        workflow.status = WorkflowStatus.VALIDATED
        workflow.save(update_fields=["status"])
        self.client.force_authenticate(self.admin)

        response = self.client.post(f"/api/workflows/treatment-workflows/{workflow.id}/activate/")

        workflow.refresh_from_db()
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data["is_valid"])
        self.assertEqual(workflow.status, WorkflowStatus.VALIDATED)

    def test_non_admin_cannot_run_lifecycle_actions(self):
        workflow = self._complete_workflow()
        self.client.force_authenticate(self.patient)

        validate_response = self.client.post(
            f"/api/workflows/treatment-workflows/{workflow.id}/validate/"
        )
        activate_response = self.client.post(
            f"/api/workflows/treatment-workflows/{workflow.id}/activate/"
        )
        archive_response = self.client.post(
            f"/api/workflows/treatment-workflows/{workflow.id}/archive/"
        )

        self.assertEqual(validate_response.status_code, 403)
        self.assertEqual(activate_response.status_code, 403)
        self.assertEqual(archive_response.status_code, 403)

    def test_active_workflow_structure_cannot_be_edited(self):
        workflow = self._complete_workflow()
        workflow.status = WorkflowStatus.ACTIVE
        workflow.save(update_fields=["status"])
        self.client.force_authenticate(self.admin)

        update_response = self.client.patch(
            f"/api/workflows/treatment-workflows/{workflow.id}/",
            {"description": "Changed"},
            format="json",
        )
        create_stage_response = self.client.post(
            "/api/workflows/care-stages/",
            {
                "workflow": workflow.id,
                "name": "Day 8-10",
                "start_day": 8,
                "end_day": 10,
            },
            format="json",
        )

        self.assertEqual(update_response.status_code, 400)
        self.assertEqual(create_stage_response.status_code, 400)
