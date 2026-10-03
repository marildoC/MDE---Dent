from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User, UserRole
from appointments.models import Appointment, AppointmentStatus
from audit import actions
from audit.models import AuditLog
from audit.services import record_audit
from decision_engine.models import RiskAssessment
from escalations.models import EscalationCase
from patients.models import FollowUpCase, FollowUpCaseStatus, PatientProfile
from reports.models import SymptomReport
from workflows.models import (
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


class AuditLogTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            password="testpass123",
            role=UserRole.ADMIN,
        )
        self.dentist = User.objects.create_user(
            username="dentist",
            password="testpass123",
            role=UserRole.DENTIST,
        )
        self.patient_user = User.objects.create_user(
            username="patient",
            password="testpass123",
            role=UserRole.PATIENT,
        )
        self.workflow = TreatmentWorkflow.objects.create(
            name="Post-Extraction Follow-Up",
            treatment_type=TreatmentType.POST_EXTRACTION,
            created_by=self.admin,
        )

    def complete_workflow(self):
        stage = CareStage.objects.create(
            workflow=self.workflow,
            name="Day 0-7",
            start_day=0,
            end_day=7,
            sort_order=1,
        )
        for key, data_type in (
            ("pain_level", SymptomDataType.INTEGER),
            ("swelling", SymptomDataType.CHOICE),
            ("bleeding", SymptomDataType.CHOICE),
            ("fever", SymptomDataType.BOOLEAN),
            ("bad_smell", SymptomDataType.BOOLEAN),
        ):
            SymptomDefinition.objects.create(
                workflow=self.workflow,
                key=key,
                label=key.replace("_", " ").title(),
                data_type=data_type,
            )
        rule = SymptomRule.objects.create(
            stage=stage,
            name="Severe pain with bad smell",
            condition={
                "all": [
                    {"field": "pain_level", "operator": ">=", "value": 8},
                    {"field": "bad_smell", "operator": "=", "value": True},
                ]
            },
            risk_level=RiskLevel.HIGH,
            recommended_action=RecommendedAction.ESCALATE_TO_DENTIST,
            appointment_priority=AppointmentPriority.HIGH,
            explanation="Severe pain with bad smell requires staff review.",
        )
        AIAdviceBoundary.objects.create(
            workflow=self.workflow,
            required_disclaimer="Contact the clinic if symptoms worsen.",
            forbidden_topics=["diagnosis", "prescription"],
        )
        EscalationRule.objects.create(
            symptom_rule=rule,
            target_role=UserRole.DENTIST,
            urgency=AppointmentPriority.HIGH,
            appointment_priority=AppointmentPriority.HIGH,
            message="Dentist review required.",
        )
        return self.workflow

    def create_active_case(self):
        self.workflow.status = WorkflowStatus.ACTIVE
        self.workflow.save(update_fields=["status"])
        profile = PatientProfile.objects.create(user=self.patient_user)
        return FollowUpCase.objects.create(
            patient=profile,
            workflow=self.workflow,
            treatment_date=timezone.localdate() - timedelta(days=4),
            assigned_staff=self.dentist,
        )

    def test_record_audit_sanitizes_sensitive_details(self):
        audit_log = record_audit(
            self.admin,
            actions.FOLLOW_UP_CASE_CREATED,
            self.workflow,
            {
                "notes": "Do not store this.",
                "staff_response": "Do not store this either.",
                "workflow_id": self.workflow.id,
            },
        )

        self.assertEqual(audit_log.actor, self.admin)
        self.assertEqual(audit_log.action, actions.FOLLOW_UP_CASE_CREATED)
        self.assertEqual(audit_log.details, {"workflow_id": self.workflow.id})

    def test_admin_can_view_audit_logs_but_patient_cannot(self):
        record_audit(self.admin, actions.WORKFLOW_ACTIVATED, self.workflow, {})

        self.client.force_authenticate(self.admin)
        admin_response = self.client.get("/api/audit/logs/")

        self.client.force_authenticate(self.patient_user)
        patient_response = self.client.get("/api/audit/logs/")

        self.client.force_authenticate(user=None)
        anonymous_response = self.client.get("/api/audit/logs/")

        self.assertEqual(admin_response.status_code, 200)
        self.assertEqual(len(admin_response.data), 1)
        self.assertEqual(patient_response.status_code, 403)
        self.assertEqual(anonymous_response.status_code, 401)

    def test_workflow_lifecycle_actions_create_audit_logs(self):
        self.complete_workflow()
        self.client.force_authenticate(self.admin)

        validate_response = self.client.post(
            f"/api/workflows/treatment-workflows/{self.workflow.id}/validate/"
        )
        activate_response = self.client.post(
            f"/api/workflows/treatment-workflows/{self.workflow.id}/activate/"
        )
        archive_response = self.client.post(
            f"/api/workflows/treatment-workflows/{self.workflow.id}/archive/"
        )

        self.assertEqual(validate_response.status_code, 200)
        self.assertEqual(activate_response.status_code, 200)
        self.assertEqual(archive_response.status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action=actions.WORKFLOW_VALIDATED).exists())
        self.assertTrue(AuditLog.objects.filter(action=actions.WORKFLOW_ACTIVATED).exists())
        self.assertTrue(AuditLog.objects.filter(action=actions.WORKFLOW_ARCHIVED).exists())

    def test_follow_up_case_create_and_status_change_create_audit_logs(self):
        self.workflow.status = WorkflowStatus.ACTIVE
        self.workflow.save(update_fields=["status"])
        profile = PatientProfile.objects.create(user=self.patient_user)
        self.client.force_authenticate(self.dentist)

        create_response = self.client.post(
            "/api/patients/follow-up-cases/",
            {
                "patient": profile.id,
                "workflow": self.workflow.id,
                "treatment_date": "2026-04-26",
                "assigned_staff": self.dentist.id,
            },
            format="json",
        )
        update_response = self.client.patch(
            f"/api/patients/follow-up-cases/{create_response.data['id']}/",
            {"status": FollowUpCaseStatus.MONITORING},
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(update_response.status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action=actions.FOLLOW_UP_CASE_CREATED).exists())
        self.assertTrue(
            AuditLog.objects.filter(action=actions.FOLLOW_UP_CASE_STATUS_CHANGED).exists()
        )

    def test_report_submission_creates_downstream_audit_logs_without_notes(self):
        self.complete_workflow()
        follow_up_case = self.create_active_case()
        self.client.force_authenticate(self.patient_user)

        response = self.client.post(
            "/api/reports/symptom-reports/",
            {
                "follow_up_case": follow_up_case.id,
                "pain_level": 8,
                "swelling": "SEVERE",
                "bleeding": "NONE",
                "fever": False,
                "bad_smell": True,
                "notes": "Sensitive patient note.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        for action in (
            actions.SYMPTOM_REPORT_SUBMITTED,
            actions.RISK_ASSESSMENT_CREATED,
            actions.ADVICE_CREATED,
            actions.ESCALATION_CREATED,
            actions.FOLLOW_UP_CASE_STATUS_CHANGED,
        ):
            self.assertTrue(AuditLog.objects.filter(action=action).exists(), action)

        report_log = AuditLog.objects.get(action=actions.SYMPTOM_REPORT_SUBMITTED)
        self.assertNotIn("notes", report_log.details)
        self.assertNotIn("Sensitive patient note.", str(report_log.details))

    def test_escalation_and_appointment_updates_create_audit_logs(self):
        follow_up_case = self.create_active_case()
        report = SymptomReport.objects.create(
            follow_up_case=follow_up_case,
            submitted_by=self.patient_user,
            pain_level=8,
            swelling="SEVERE",
            bleeding="NONE",
            fever=False,
            bad_smell=True,
        )
        assessment = RiskAssessment.objects.create(
            report=report,
            detected_stage=None,
            matched_rules=[],
            risk_level=RiskLevel.HIGH,
            recommended_action=RecommendedAction.ESCALATE_TO_DENTIST,
            appointment_priority=AppointmentPriority.HIGH,
            explanation="Test assessment.",
        )
        escalation = EscalationCase.objects.create(
            risk_assessment=assessment,
            report=report,
            follow_up_case=follow_up_case,
            patient=follow_up_case.patient,
            urgency=RiskLevel.HIGH,
            assigned_staff=self.dentist,
        )
        self.client.force_authenticate(self.dentist)

        escalation_response = self.client.patch(
            f"/api/escalations/cases/{escalation.id}/",
            {
                "status": "IN_REVIEW",
                "staff_response": "Sensitive staff response.",
            },
            format="json",
        )
        appointment_response = self.client.post(
            "/api/appointments/appointments/",
            {"escalation_case": escalation.id},
            format="json",
        )
        appointment = Appointment.objects.get(id=appointment_response.data["id"])
        appointment_update_response = self.client.patch(
            f"/api/appointments/appointments/{appointment.id}/",
            {"status": AppointmentStatus.SCHEDULED},
            format="json",
        )

        self.assertEqual(escalation_response.status_code, 200)
        self.assertEqual(appointment_response.status_code, 201)
        self.assertEqual(appointment_update_response.status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action=actions.ESCALATION_UPDATED).exists())
        self.assertTrue(AuditLog.objects.filter(action=actions.APPOINTMENT_CREATED).exists())
        self.assertTrue(AuditLog.objects.filter(action=actions.APPOINTMENT_UPDATED).exists())
        self.assertNotIn("Sensitive staff response.", str(AuditLog.objects.values_list("details")))
