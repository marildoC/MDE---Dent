from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User, UserRole
from decision_engine.models import RiskAssessment
from patients.models import FollowUpCase, PatientProfile
from reports.models import SymptomReport
from workflows.models import (
    AIAdviceBoundary,
    AppointmentPriority,
    CareStage,
    RecommendedAction,
    RiskLevel,
    TreatmentType,
    TreatmentWorkflow,
    WorkflowStatus,
)

from .models import AdviceMessage, AdviceMessageType
from .services import UNSAFE_TERMS, generate_advice_for_assessment


class AdviceMessageTests(APITestCase):
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
        self.other_patient_user = User.objects.create_user(
            username="other-patient",
            password="testpass123",
            role=UserRole.PATIENT,
        )
        self.workflow = TreatmentWorkflow.objects.create(
            name="Active Post-Extraction",
            treatment_type=TreatmentType.POST_EXTRACTION,
            status=WorkflowStatus.ACTIVE,
            created_by=self.admin,
        )
        self.stage = CareStage.objects.create(
            workflow=self.workflow,
            name="Day 0-7",
            start_day=0,
            end_day=7,
            sort_order=1,
        )
        AIAdviceBoundary.objects.create(
            workflow=self.workflow,
            stage=self.stage,
            required_disclaimer="This advice is limited to follow-up monitoring and clinic contact guidance.",
        )
        self.profile = PatientProfile.objects.create(user=self.patient_user)
        self.other_profile = PatientProfile.objects.create(user=self.other_patient_user)
        self.case = FollowUpCase.objects.create(
            patient=self.profile,
            workflow=self.workflow,
            treatment_date=timezone.localdate() - timedelta(days=2),
        )
        self.other_case = FollowUpCase.objects.create(
            patient=self.other_profile,
            workflow=self.workflow,
            treatment_date=timezone.localdate() - timedelta(days=2),
        )

    def make_report(self, follow_up_case=None, **overrides):
        follow_up_case = follow_up_case or self.case
        payload = {
            "follow_up_case": follow_up_case,
            "submitted_by": follow_up_case.patient.user,
            "pain_level": 3,
            "swelling": "MILD",
            "bleeding": "NONE",
            "fever": False,
            "bad_smell": False,
            "notes": "",
        }
        payload.update(overrides)
        return SymptomReport.objects.create(**payload)

    def make_assessment(self, risk_level=RiskLevel.LOW, follow_up_case=None):
        report = self.make_report(follow_up_case=follow_up_case)
        return RiskAssessment.objects.create(
            report=report,
            detected_stage=self.stage,
            matched_rules=[],
            risk_level=risk_level,
            recommended_action=RecommendedAction.CONTINUE_MONITORING,
            appointment_priority=AppointmentPriority.NONE,
            explanation="Test deterministic assessment.",
        )

    def test_generates_low_risk_aftercare_advice(self):
        assessment = self.make_assessment(RiskLevel.LOW)

        advice = generate_advice_for_assessment(assessment)

        self.assertEqual(advice.message_type, AdviceMessageType.LOW_RISK_AFTERCARE)
        self.assertIn("expected monitoring range", advice.message)
        self.assertIn("follow-up monitoring", advice.message)

    def test_generates_distinct_warning_high_and_urgent_advice(self):
        expected = {
            RiskLevel.WARNING: AdviceMessageType.WARNING_MONITORING,
            RiskLevel.HIGH: AdviceMessageType.HIGH_STAFF_REVIEW,
            RiskLevel.URGENT: AdviceMessageType.URGENT_ATTENTION,
        }

        for risk_level, message_type in expected.items():
            with self.subTest(risk_level=risk_level):
                assessment = self.make_assessment(risk_level)
                advice = generate_advice_for_assessment(assessment)

                self.assertEqual(advice.message_type, message_type)
                self.assertIn("clinic", advice.message.lower())

    def test_generation_is_idempotent(self):
        assessment = self.make_assessment(RiskLevel.HIGH)

        first = generate_advice_for_assessment(assessment)
        second = generate_advice_for_assessment(assessment)

        self.assertEqual(first.id, second.id)
        self.assertEqual(AdviceMessage.objects.count(), 1)

    def test_unsafe_boundary_disclaimer_is_not_included(self):
        AIAdviceBoundary.objects.filter(stage=self.stage).update(
            required_disclaimer="This does not provide diagnosis or prescription guidance."
        )
        assessment = self.make_assessment(RiskLevel.WARNING)

        advice = generate_advice_for_assessment(assessment)

        lowered = advice.message.lower()
        self.assertFalse(any(term in lowered for term in UNSAFE_TERMS))

    def test_global_policy_unsafe_boundary_disclaimer_is_not_included(self):
        AIAdviceBoundary.objects.filter(stage=self.stage).update(
            required_disclaimer="Continue antibiotic exolin for 3 days."
        )
        assessment = self.make_assessment(RiskLevel.WARNING)

        advice = generate_advice_for_assessment(assessment)

        lowered = advice.message.lower()
        self.assertNotIn("exolin", lowered)
        self.assertNotIn("antibiotic", lowered)

    def test_patient_can_generate_and_view_only_own_advice(self):
        own_assessment = self.make_assessment(RiskLevel.LOW)
        other_assessment = self.make_assessment(
            RiskLevel.URGENT,
            follow_up_case=self.other_case,
        )
        self.client.force_authenticate(self.patient_user)

        generate_response = self.client.post(
            f"/api/ai-support/risk-assessments/{own_assessment.id}/generate-advice/"
        )
        blocked_generate_response = self.client.post(
            f"/api/ai-support/risk-assessments/{other_assessment.id}/generate-advice/"
        )
        list_response = self.client.get("/api/ai-support/advice-messages/")

        self.assertEqual(generate_response.status_code, 200)
        self.assertEqual(blocked_generate_response.status_code, 404)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual([item["risk_assessment"] for item in list_response.data], [own_assessment.id])

    def test_staff_can_generate_and_view_advice(self):
        assessment = self.make_assessment(RiskLevel.HIGH)
        self.client.force_authenticate(self.dentist)

        generate_response = self.client.post(
            f"/api/ai-support/risk-assessments/{assessment.id}/generate-advice/"
        )
        list_response = self.client.get("/api/ai-support/advice-messages/")

        self.assertEqual(generate_response.status_code, 200)
        self.assertEqual(generate_response.data["message_type"], AdviceMessageType.HIGH_STAFF_REVIEW)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)

    def test_report_creation_api_automatically_creates_assessment_and_advice(self):
        self.client.force_authenticate(self.patient_user)

        response = self.client.post(
            "/api/reports/symptom-reports/",
            {
                "follow_up_case": self.case.id,
                "pain_level": 2,
                "swelling": "NONE",
                "bleeding": "NONE",
                "fever": False,
                "bad_smell": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(RiskAssessment.objects.count(), 1)
        self.assertEqual(AdviceMessage.objects.count(), 1)
        self.assertIsNotNone(response.data["risk_assessment"]["advice_message"])
