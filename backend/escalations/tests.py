from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User, UserRole
from decision_engine.models import RiskAssessment
from patients.models import FollowUpCase, FollowUpCaseStatus, PatientProfile
from reports.models import SymptomReport
from workflows.models import (
    AppointmentPriority,
    CareStage,
    RecommendedAction,
    RiskLevel,
    SymptomRule,
    TreatmentType,
    TreatmentWorkflow,
    WorkflowStatus,
)

from .models import EscalationCase, EscalationStatus
from .services import create_escalation_for_assessment


class EscalationCaseTests(APITestCase):
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
        self.high_rule = SymptomRule.objects.create(
            stage=self.stage,
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
        self.profile = PatientProfile.objects.create(user=self.patient_user)
        self.other_profile = PatientProfile.objects.create(user=self.other_patient_user)
        self.case = FollowUpCase.objects.create(
            patient=self.profile,
            workflow=self.workflow,
            treatment_date=timezone.localdate() - timedelta(days=4),
            assigned_staff=self.dentist,
        )
        self.other_case = FollowUpCase.objects.create(
            patient=self.other_profile,
            workflow=self.workflow,
            treatment_date=timezone.localdate() - timedelta(days=4),
        )

    def make_report(self, follow_up_case=None, **overrides):
        follow_up_case = follow_up_case or self.case
        payload = {
            "follow_up_case": follow_up_case,
            "submitted_by": follow_up_case.patient.user,
            "pain_level": 8,
            "swelling": "SEVERE",
            "bleeding": "NONE",
            "fever": False,
            "bad_smell": True,
            "notes": "",
        }
        payload.update(overrides)
        return SymptomReport.objects.create(**payload)

    def make_assessment(self, risk_level=RiskLevel.HIGH, follow_up_case=None):
        report = self.make_report(follow_up_case=follow_up_case)
        return RiskAssessment.objects.create(
            report=report,
            detected_stage=self.stage,
            matched_rules=[],
            risk_level=risk_level,
            recommended_action=(
                RecommendedAction.ESCALATE_TO_DENTIST
                if risk_level in {RiskLevel.HIGH, RiskLevel.URGENT}
                else RecommendedAction.CONTINUE_MONITORING
            ),
            appointment_priority=(
                AppointmentPriority.URGENT
                if risk_level == RiskLevel.URGENT
                else AppointmentPriority.HIGH
                if risk_level == RiskLevel.HIGH
                else AppointmentPriority.NONE
            ),
            explanation="Test risk assessment.",
        )

    def test_high_assessment_creates_escalation_and_updates_case(self):
        assessment = self.make_assessment(RiskLevel.HIGH)

        escalation = create_escalation_for_assessment(assessment)

        self.assertIsNotNone(escalation)
        self.assertEqual(escalation.risk_assessment, assessment)
        self.assertEqual(escalation.report, assessment.report)
        self.assertEqual(escalation.follow_up_case, self.case)
        self.assertEqual(escalation.patient, self.profile)
        self.assertEqual(escalation.urgency, RiskLevel.HIGH)
        self.assertEqual(escalation.assigned_staff, self.dentist)
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, FollowUpCaseStatus.ESCALATED)

    def test_urgent_assessment_creates_urgent_escalation(self):
        assessment = self.make_assessment(RiskLevel.URGENT)

        escalation = create_escalation_for_assessment(assessment)

        self.assertEqual(escalation.urgency, RiskLevel.URGENT)
        self.assertEqual(EscalationCase.objects.count(), 1)

    def test_low_and_warning_assessments_do_not_create_escalation(self):
        low_assessment = self.make_assessment(RiskLevel.LOW)
        warning_assessment = self.make_assessment(RiskLevel.WARNING)

        self.assertIsNone(create_escalation_for_assessment(low_assessment))
        self.assertIsNone(create_escalation_for_assessment(warning_assessment))
        self.assertEqual(EscalationCase.objects.count(), 0)

    def test_escalation_creation_is_idempotent(self):
        assessment = self.make_assessment(RiskLevel.HIGH)

        first = create_escalation_for_assessment(assessment)
        second = create_escalation_for_assessment(assessment)

        self.assertEqual(first.id, second.id)
        self.assertEqual(EscalationCase.objects.count(), 1)

    def test_staff_can_list_view_and_update_escalation(self):
        escalation = create_escalation_for_assessment(self.make_assessment(RiskLevel.HIGH))
        self.client.force_authenticate(self.dentist)

        list_response = self.client.get("/api/escalations/cases/")
        detail_response = self.client.get(f"/api/escalations/cases/{escalation.id}/")
        update_response = self.client.patch(
            f"/api/escalations/cases/{escalation.id}/",
            {
                "status": EscalationStatus.IN_REVIEW,
                "staff_response": "Please contact the clinic today.",
            },
            format="json",
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(update_response.status_code, 200)
        escalation.refresh_from_db()
        self.assertEqual(escalation.status, EscalationStatus.IN_REVIEW)
        self.assertEqual(escalation.staff_response, "Please contact the clinic today.")

    def test_patient_can_view_only_own_escalation_and_cannot_update(self):
        own_escalation = create_escalation_for_assessment(self.make_assessment(RiskLevel.HIGH))
        other_escalation = create_escalation_for_assessment(
            self.make_assessment(RiskLevel.URGENT, follow_up_case=self.other_case)
        )
        self.client.force_authenticate(self.patient_user)

        list_response = self.client.get("/api/escalations/cases/")
        own_response = self.client.get(f"/api/escalations/cases/{own_escalation.id}/")
        other_response = self.client.get(f"/api/escalations/cases/{other_escalation.id}/")
        update_response = self.client.patch(
            f"/api/escalations/cases/{own_escalation.id}/",
            {"status": EscalationStatus.RESOLVED},
            format="json",
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual([item["id"] for item in list_response.data], [own_escalation.id])
        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(other_response.status_code, 404)
        self.assertEqual(update_response.status_code, 403)

    def test_appointment_required_status_updates_case_without_appointment_object(self):
        escalation = create_escalation_for_assessment(self.make_assessment(RiskLevel.HIGH))
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            f"/api/escalations/cases/{escalation.id}/",
            {"status": EscalationStatus.APPOINTMENT_REQUIRED},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, FollowUpCaseStatus.APPOINTMENT_REQUIRED)

    def test_invalid_escalation_transition_is_rejected_without_partial_update(self):
        escalation = create_escalation_for_assessment(self.make_assessment(RiskLevel.HIGH))
        self.client.force_authenticate(self.dentist)

        response = self.client.patch(
            f"/api/escalations/cases/{escalation.id}/",
            {
                "status": EscalationStatus.CLOSED,
                "staff_response": "This should not save.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        escalation.refresh_from_db()
        self.assertEqual(escalation.status, EscalationStatus.NEW)
        self.assertEqual(escalation.staff_response, "")

    def test_closed_escalation_cannot_be_edited(self):
        escalation = create_escalation_for_assessment(self.make_assessment(RiskLevel.HIGH))
        self.client.force_authenticate(self.admin)
        self.client.patch(
            f"/api/escalations/cases/{escalation.id}/",
            {"status": EscalationStatus.RESOLVED},
            format="json",
        )
        self.client.patch(
            f"/api/escalations/cases/{escalation.id}/",
            {"status": EscalationStatus.CLOSED},
            format="json",
        )

        response = self.client.patch(
            f"/api/escalations/cases/{escalation.id}/",
            {"staff_response": "Late edit."},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        escalation.refresh_from_db()
        self.assertEqual(escalation.status, EscalationStatus.CLOSED)
        self.assertEqual(escalation.staff_response, "")

    def test_report_creation_api_automatically_creates_escalation_for_high_risk(self):
        self.client.force_authenticate(self.patient_user)

        response = self.client.post(
            "/api/reports/symptom-reports/",
            {
                "follow_up_case": self.case.id,
                "pain_level": 8,
                "swelling": "SEVERE",
                "bleeding": "NONE",
                "fever": False,
                "bad_smell": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(RiskAssessment.objects.count(), 1)
        self.assertEqual(EscalationCase.objects.count(), 1)
        escalation = EscalationCase.objects.get()
        self.assertEqual(escalation.urgency, RiskLevel.HIGH)

    def test_evaluating_existing_high_assessment_creates_missing_escalation(self):
        assessment = self.make_assessment(RiskLevel.HIGH)
        self.client.force_authenticate(self.dentist)

        response = self.client.post(
            f"/api/decision-engine/reports/{assessment.report_id}/evaluate/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(EscalationCase.objects.count(), 1)
        self.assertEqual(EscalationCase.objects.get().risk_assessment, assessment)
