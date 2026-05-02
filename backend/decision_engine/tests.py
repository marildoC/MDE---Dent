from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User, UserRole
from patients.models import FollowUpCase, PatientProfile
from reports.models import SymptomReport
from workflows.models import (
    AppointmentPriority,
    CareStage,
    RecommendedAction,
    RiskLevel,
    SymptomDataType,
    SymptomDefinition,
    SymptomRule,
    TreatmentType,
    TreatmentWorkflow,
    WorkflowStatus,
)

from .models import RiskAssessment
from .services import assess_report, detect_stage


class DecisionEngineTests(APITestCase):
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
        self.stage_early = CareStage.objects.create(
            workflow=self.workflow,
            name="Day 0-3",
            start_day=0,
            end_day=3,
            sort_order=1,
        )
        self.stage_later = CareStage.objects.create(
            workflow=self.workflow,
            name="Day 4-7",
            start_day=4,
            end_day=7,
            sort_order=2,
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
        self.low_rule = SymptomRule.objects.create(
            stage=self.stage_early,
            name="Mild early pain",
            condition={"all": [{"field": "pain_level", "operator": "<=", "value": 3}]},
            risk_level=RiskLevel.LOW,
            recommended_action=RecommendedAction.CONTINUE_MONITORING,
            appointment_priority=AppointmentPriority.NONE,
            explanation="Mild pain in early recovery is low risk.",
        )
        self.high_rule = SymptomRule.objects.create(
            stage=self.stage_later,
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
            explanation="Severe pain with bad smell is high risk.",
        )
        self.urgent_rule = SymptomRule.objects.create(
            stage=self.stage_later,
            name="Fever",
            condition={"all": [{"field": "fever", "operator": "=", "value": True}]},
            risk_level=RiskLevel.URGENT,
            recommended_action=RecommendedAction.ESCALATE_TO_DENTIST,
            appointment_priority=AppointmentPriority.URGENT,
            explanation="Fever after extraction is urgent.",
        )
        self.profile = PatientProfile.objects.create(user=self.patient_user)
        self.other_profile = PatientProfile.objects.create(user=self.other_patient_user)
        self.case = FollowUpCase.objects.create(
            patient=self.profile,
            workflow=self.workflow,
            treatment_date=timezone.localdate() - timedelta(days=4),
        )
        self.other_case = FollowUpCase.objects.create(
            patient=self.other_profile,
            workflow=self.workflow,
            treatment_date=timezone.localdate() - timedelta(days=4),
        )

    def make_report(self, follow_up_case=None, **overrides):
        payload = {
            "follow_up_case": follow_up_case or self.case,
            "submitted_by": (follow_up_case or self.case).patient.user,
            "pain_level": 8,
            "swelling": "SEVERE",
            "bleeding": "NONE",
            "fever": False,
            "bad_smell": True,
            "notes": "",
        }
        payload.update(overrides)
        return SymptomReport.objects.create(**payload)

    def test_stage_is_detected_by_day_after_treatment(self):
        report = self.make_report()

        stage = detect_stage(report)

        self.assertEqual(stage, self.stage_later)

    def test_low_rule_match_creates_low_assessment(self):
        early_case = FollowUpCase.objects.create(
            patient=self.profile,
            workflow=self.workflow,
            treatment_date=timezone.localdate() - timedelta(days=1),
        )
        report = self.make_report(
            follow_up_case=early_case,
            pain_level=2,
            swelling="NONE",
            bad_smell=False,
        )

        assessment = assess_report(report)

        self.assertEqual(assessment.risk_level, RiskLevel.LOW)
        self.assertEqual(assessment.recommended_action, RecommendedAction.CONTINUE_MONITORING)
        self.assertEqual(assessment.detected_stage, self.stage_early)

    def test_pain_and_bad_smell_on_day_four_creates_high_assessment(self):
        report = self.make_report()

        assessment = assess_report(report)

        self.assertEqual(assessment.risk_level, RiskLevel.HIGH)
        self.assertEqual(assessment.recommended_action, RecommendedAction.ESCALATE_TO_DENTIST)
        self.assertEqual(assessment.appointment_priority, AppointmentPriority.HIGH)
        self.assertEqual(assessment.matched_rules[0]["id"], self.high_rule.id)

    def test_multiple_matches_select_highest_severity(self):
        report = self.make_report(fever=True)

        assessment = assess_report(report)

        self.assertEqual(assessment.risk_level, RiskLevel.URGENT)
        self.assertEqual(assessment.appointment_priority, AppointmentPriority.URGENT)
        self.assertEqual(
            {rule["id"] for rule in assessment.matched_rules},
            {self.high_rule.id, self.urgent_rule.id},
        )

    def test_no_matching_rule_creates_low_fallback(self):
        report = self.make_report(pain_level=4, swelling="MILD", bad_smell=False)

        assessment = assess_report(report)

        self.assertEqual(assessment.risk_level, RiskLevel.LOW)
        self.assertEqual(assessment.recommended_action, RecommendedAction.CONTINUE_MONITORING)
        self.assertEqual(assessment.matched_rules, [])

    def test_no_matching_stage_creates_warning_fallback(self):
        old_case = FollowUpCase.objects.create(
            patient=self.profile,
            workflow=self.workflow,
            treatment_date=timezone.localdate() - timedelta(days=12),
        )
        report = self.make_report(follow_up_case=old_case)

        assessment = assess_report(report)

        self.assertEqual(assessment.risk_level, RiskLevel.WARNING)
        self.assertEqual(assessment.recommended_action, RecommendedAction.RECOMMEND_CONTACT)
        self.assertIsNone(assessment.detected_stage)

    def test_dynamic_symptom_key_can_match_rule(self):
        SymptomDefinition.objects.create(
            workflow=self.workflow,
            key="numbness",
            label="Numbness",
            data_type=SymptomDataType.BOOLEAN,
        )
        dynamic_rule = SymptomRule.objects.create(
            stage=self.stage_later,
            name="Numbness reported",
            condition={"all": [{"field": "numbness", "operator": "=", "value": True}]},
            risk_level=RiskLevel.HIGH,
            recommended_action=RecommendedAction.ESCALATE_TO_DENTIST,
            appointment_priority=AppointmentPriority.HIGH,
            explanation="Numbness requires staff review.",
        )
        report = self.make_report(
            pain_level=2,
            swelling="MILD",
            bad_smell=False,
            symptom_values={"numbness": True},
        )

        assessment = assess_report(report)

        self.assertEqual(assessment.risk_level, RiskLevel.HIGH)
        self.assertEqual(assessment.matched_rules[0]["id"], dynamic_rule.id)

    def test_day_after_treatment_condition_still_matches(self):
        day_rule = SymptomRule.objects.create(
            stage=self.stage_later,
            name="Day four monitoring",
            condition={
                "all": [{"field": "day_after_treatment", "operator": ">=", "value": 4}]
            },
            risk_level=RiskLevel.WARNING,
            recommended_action=RecommendedAction.RECOMMEND_CONTACT,
            appointment_priority=AppointmentPriority.NORMAL,
            explanation="Day four report should be reviewed if symptoms are uncertain.",
        )
        report = self.make_report(pain_level=2, swelling="MILD", bad_smell=False)

        assessment = assess_report(report)

        self.assertEqual(assessment.risk_level, RiskLevel.WARNING)
        self.assertEqual(assessment.matched_rules[0]["id"], day_rule.id)

    def test_duplicate_evaluation_returns_existing_assessment(self):
        report = self.make_report()

        first = assess_report(report)
        second = assess_report(report)

        self.assertEqual(first.id, second.id)
        self.assertEqual(RiskAssessment.objects.count(), 1)

    def test_malformed_condition_does_not_crash_evaluation(self):
        SymptomRule.objects.create(
            stage=self.stage_later,
            name="Malformed",
            condition={"raw": "pain_level >= 8"},
            risk_level=RiskLevel.URGENT,
            recommended_action=RecommendedAction.ESCALATE_TO_DENTIST,
            appointment_priority=AppointmentPriority.URGENT,
            explanation="Malformed rule should not execute.",
        )
        report = self.make_report(pain_level=4, bad_smell=False)

        assessment = assess_report(report)

        self.assertEqual(assessment.risk_level, RiskLevel.LOW)

    def test_report_creation_api_automatically_creates_assessment(self):
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
        self.assertEqual(response.data["risk_assessment"]["risk_level"], RiskLevel.HIGH)
        self.assertEqual(
            response.data["risk_assessment"]["matched_rule_details"][0]["condition_text"],
            "pain_level >= 8 AND bad_smell = true",
        )

    def test_patient_cannot_evaluate_or_view_another_patient_assessment(self):
        report = self.make_report(follow_up_case=self.other_case)
        assessment = assess_report(report)
        self.client.force_authenticate(self.patient_user)

        evaluate_response = self.client.post(
            f"/api/decision-engine/reports/{report.id}/evaluate/"
        )
        detail_response = self.client.get(
            f"/api/decision-engine/risk-assessments/{assessment.id}/"
        )

        self.assertEqual(evaluate_response.status_code, 404)
        self.assertEqual(detail_response.status_code, 404)

    def test_staff_can_evaluate_and_view_assessments(self):
        report = self.make_report()
        self.client.force_authenticate(self.dentist)

        evaluate_response = self.client.post(
            f"/api/decision-engine/reports/{report.id}/evaluate/"
        )
        list_response = self.client.get("/api/decision-engine/risk-assessments/")

        self.assertEqual(evaluate_response.status_code, 200)
        self.assertEqual(evaluate_response.data["risk_level"], RiskLevel.HIGH)
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
