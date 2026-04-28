from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User, UserRole
from ai_support.models import AdviceMessage
from appointments.models import Appointment, AppointmentStatus
from audit import actions as audit_actions
from audit.models import AuditLog
from decision_engine.models import RiskAssessment
from escalations.models import EscalationCase, EscalationStatus
from patients.models import FollowUpCase, FollowUpCaseStatus, PatientProfile
from reports.models import SymptomReport
from workflows.models import (
    AppointmentPriority,
    RecommendedAction,
    RiskLevel,
    SymptomDataType,
    TreatmentType,
    WorkflowStatus,
)


class PostExtractionReliabilityTests(APITestCase):
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

    def test_post_extraction_high_risk_end_to_end_flow(self):
        workflow_id = self._create_workflow_via_api(
            rule={
                "name": "Severe pain with bad smell",
                "condition": {
                    "all": [
                        {"field": "pain_level", "operator": ">=", "value": 8},
                        {"field": "bad_smell", "operator": "=", "value": True},
                    ]
                },
                "risk_level": RiskLevel.HIGH,
                "recommended_action": RecommendedAction.ESCALATE_TO_DENTIST,
                "appointment_priority": AppointmentPriority.HIGH,
                "explanation": "Severe pain with bad smell requires staff review.",
                "escalation": True,
            },
        )
        follow_up_case_id = self._create_follow_up_case_via_api(workflow_id)

        self.client.force_authenticate(self.patient_user)
        report_response = self.client.post(
            "/api/reports/symptom-reports/",
            {
                "follow_up_case": follow_up_case_id,
                "pain_level": 8,
                "swelling": "SEVERE",
                "bleeding": "NONE",
                "fever": False,
                "bad_smell": True,
                "notes": "Patient note should not be copied to audit details.",
            },
            format="json",
        )

        self.assertEqual(report_response.status_code, 201)
        report = SymptomReport.objects.get(id=report_response.data["id"])
        assessment = RiskAssessment.objects.get(report=report)
        advice = AdviceMessage.objects.get(risk_assessment=assessment)
        escalation = EscalationCase.objects.get(risk_assessment=assessment)

        self.assertEqual(assessment.risk_level, RiskLevel.HIGH)
        self.assertEqual(assessment.recommended_action, RecommendedAction.ESCALATE_TO_DENTIST)
        self.assertEqual(assessment.appointment_priority, AppointmentPriority.HIGH)
        self.assertEqual(assessment.matched_rules[0]["name"], "Severe pain with bad smell")
        self.assertEqual(advice.risk_assessment_id, assessment.id)
        self.assertEqual(escalation.status, EscalationStatus.NEW)

        follow_up_case = FollowUpCase.objects.get(id=follow_up_case_id)
        self.assertEqual(follow_up_case.status, FollowUpCaseStatus.ESCALATED)

        self.client.force_authenticate(self.dentist)
        escalation_response = self.client.patch(
            f"/api/escalations/cases/{escalation.id}/",
            {
                "status": EscalationStatus.IN_REVIEW,
                "staff_response": "Staff response should not be copied to audit details.",
            },
            format="json",
        )
        self.assertEqual(escalation_response.status_code, 200)

        appointment_response = self.client.post(
            "/api/appointments/appointments/",
            {"escalation_case": escalation.id},
            format="json",
        )
        self.assertEqual(appointment_response.status_code, 201)

        appointment = Appointment.objects.get(id=appointment_response.data["id"])
        self.assertEqual(appointment.priority, AppointmentPriority.HIGH)
        self.assertEqual(appointment.status, AppointmentStatus.PRIORITY_SUGGESTED)

        scheduled_response = self.client.patch(
            f"/api/appointments/appointments/{appointment.id}/",
            {"status": AppointmentStatus.SCHEDULED},
            format="json",
        )
        completed_response = self.client.patch(
            f"/api/appointments/appointments/{appointment.id}/",
            {"status": AppointmentStatus.COMPLETED},
            format="json",
        )

        self.assertEqual(scheduled_response.status_code, 200)
        self.assertEqual(completed_response.status_code, 200)
        appointment.refresh_from_db()
        follow_up_case.refresh_from_db()
        escalation.refresh_from_db()
        self.assertEqual(appointment.status, AppointmentStatus.COMPLETED)
        self.assertEqual(follow_up_case.status, FollowUpCaseStatus.RESOLVED)
        self.assertEqual(escalation.status, EscalationStatus.APPOINTMENT_REQUIRED)

        for action in (
            audit_actions.WORKFLOW_VALIDATED,
            audit_actions.WORKFLOW_ACTIVATED,
            audit_actions.FOLLOW_UP_CASE_CREATED,
            audit_actions.SYMPTOM_REPORT_SUBMITTED,
            audit_actions.RISK_ASSESSMENT_CREATED,
            audit_actions.ADVICE_CREATED,
            audit_actions.ESCALATION_CREATED,
            audit_actions.ESCALATION_UPDATED,
            audit_actions.APPOINTMENT_CREATED,
            audit_actions.APPOINTMENT_UPDATED,
            audit_actions.FOLLOW_UP_CASE_STATUS_CHANGED,
        ):
            self.assertTrue(AuditLog.objects.filter(action=action).exists(), action)

        self.assertNotIn("Patient note should not be copied", str(AuditLog.objects.values("details")))
        self.assertNotIn("Staff response should not be copied", str(AuditLog.objects.values("details")))

    def test_post_extraction_low_risk_report_does_not_over_escalate(self):
        workflow_id = self._create_workflow_via_api(
            rule={
                "name": "Mild early pain",
                "condition": {"all": [{"field": "pain_level", "operator": "<=", "value": 3}]},
                "risk_level": RiskLevel.LOW,
                "recommended_action": RecommendedAction.CONTINUE_MONITORING,
                "appointment_priority": AppointmentPriority.NONE,
                "explanation": "Mild early pain is expected monitoring behavior.",
                "escalation": False,
            },
        )
        follow_up_case_id = self._create_follow_up_case_via_api(workflow_id, days_after_treatment=1)

        self.client.force_authenticate(self.patient_user)
        response = self.client.post(
            "/api/reports/symptom-reports/",
            {
                "follow_up_case": follow_up_case_id,
                "pain_level": 2,
                "swelling": "MILD",
                "bleeding": "NONE",
                "fever": False,
                "bad_smell": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        report = SymptomReport.objects.get(id=response.data["id"])
        assessment = RiskAssessment.objects.get(report=report)

        self.assertEqual(assessment.risk_level, RiskLevel.LOW)
        self.assertEqual(assessment.recommended_action, RecommendedAction.CONTINUE_MONITORING)
        self.assertEqual(AdviceMessage.objects.filter(risk_assessment=assessment).count(), 1)
        self.assertFalse(EscalationCase.objects.filter(risk_assessment=assessment).exists())
        self.assertEqual(Appointment.objects.count(), 0)

        follow_up_case = FollowUpCase.objects.get(id=follow_up_case_id)
        self.assertEqual(follow_up_case.status, FollowUpCaseStatus.ACTIVE)
        self.assertTrue(AuditLog.objects.filter(action=audit_actions.SYMPTOM_REPORT_SUBMITTED).exists())
        self.assertTrue(AuditLog.objects.filter(action=audit_actions.RISK_ASSESSMENT_CREATED).exists())
        self.assertTrue(AuditLog.objects.filter(action=audit_actions.ADVICE_CREATED).exists())
        self.assertFalse(AuditLog.objects.filter(action=audit_actions.ESCALATION_CREATED).exists())
        self.assertFalse(AuditLog.objects.filter(action=audit_actions.APPOINTMENT_CREATED).exists())

    def _create_workflow_via_api(self, *, rule):
        self.client.force_authenticate(self.admin)
        workflow_response = self.client.post(
            "/api/workflows/treatment-workflows/",
            {
                "name": "Post-Extraction Follow-Up",
                "treatment_type": TreatmentType.POST_EXTRACTION,
                "description": "Regression workflow for Post-Extraction follow-up.",
            },
            format="json",
        )
        self.assertEqual(workflow_response.status_code, 201)
        workflow_id = workflow_response.data["id"]

        stage_response = self.client.post(
            "/api/workflows/care-stages/",
            {
                "workflow": workflow_id,
                "name": "Day 0-7",
                "start_day": 0,
                "end_day": 7,
                "sort_order": 1,
            },
            format="json",
        )
        self.assertEqual(stage_response.status_code, 201)
        stage_id = stage_response.data["id"]

        for key, data_type in (
            ("pain_level", SymptomDataType.INTEGER),
            ("swelling", SymptomDataType.CHOICE),
            ("bleeding", SymptomDataType.CHOICE),
            ("fever", SymptomDataType.BOOLEAN),
            ("bad_smell", SymptomDataType.BOOLEAN),
        ):
            symptom_response = self.client.post(
                "/api/workflows/symptom-definitions/",
                {
                    "workflow": workflow_id,
                    "key": key,
                    "label": key.replace("_", " ").title(),
                    "data_type": data_type,
                },
                format="json",
            )
            self.assertEqual(symptom_response.status_code, 201)

        rule_payload = {
            "stage": stage_id,
            "name": rule["name"],
            "condition": rule["condition"],
            "risk_level": rule["risk_level"],
            "recommended_action": rule["recommended_action"],
            "appointment_priority": rule["appointment_priority"],
            "explanation": rule["explanation"],
        }
        rule_response = self.client.post(
            "/api/workflows/symptom-rules/",
            rule_payload,
            format="json",
        )
        self.assertEqual(rule_response.status_code, 201)

        boundary_response = self.client.post(
            "/api/workflows/advice-boundaries/",
            {
                "workflow": workflow_id,
                "allowed_topics": ["aftercare reminders"],
                "forbidden_topics": ["diagnosis", "prescription"],
                "required_disclaimer": "Contact the clinic if symptoms worsen.",
            },
            format="json",
        )
        self.assertEqual(boundary_response.status_code, 201)

        if rule["escalation"]:
            escalation_rule_response = self.client.post(
                "/api/workflows/escalation-rules/",
                {
                    "symptom_rule": rule_response.data["id"],
                    "target_role": UserRole.DENTIST,
                    "urgency": rule["appointment_priority"],
                    "appointment_priority": rule["appointment_priority"],
                    "message": "Dentist review required.",
                },
                format="json",
            )
            self.assertEqual(escalation_rule_response.status_code, 201)

        validate_response = self.client.post(
            f"/api/workflows/treatment-workflows/{workflow_id}/validate/"
        )
        self.assertEqual(validate_response.status_code, 200)
        self.assertTrue(validate_response.data["is_valid"])
        self.assertEqual(validate_response.data["status"], WorkflowStatus.VALIDATED)

        activate_response = self.client.post(
            f"/api/workflows/treatment-workflows/{workflow_id}/activate/"
        )
        self.assertEqual(activate_response.status_code, 200)
        self.assertEqual(activate_response.data["status"], WorkflowStatus.ACTIVE)

        return workflow_id

    def _create_follow_up_case_via_api(self, workflow_id, *, days_after_treatment=4):
        self.client.force_authenticate(self.dentist)
        profile_response = self.client.post(
            "/api/patients/profiles/",
            {"user": self.patient_user.id},
            format="json",
        )
        self.assertEqual(profile_response.status_code, 201)

        case_response = self.client.post(
            "/api/patients/follow-up-cases/",
            {
                "patient": profile_response.data["id"],
                "workflow": workflow_id,
                "treatment_date": str(timezone.localdate() - timedelta(days=days_after_treatment)),
                "assigned_staff": self.dentist.id,
            },
            format="json",
        )
        self.assertEqual(case_response.status_code, 201)
        self.assertEqual(case_response.data["status"], FollowUpCaseStatus.ACTIVE)

        return case_response.data["id"]
