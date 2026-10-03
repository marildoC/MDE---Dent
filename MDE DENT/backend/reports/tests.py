from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User, UserRole
from patients.models import FollowUpCase, FollowUpCaseStatus, PatientProfile
from workflows.models import (
    SymptomDataType,
    SymptomDefinition,
    TreatmentType,
    TreatmentWorkflow,
    WorkflowStatus,
)

from .models import SymptomReport


class SymptomReportTests(APITestCase):
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
        self.profile = PatientProfile.objects.create(user=self.patient_user)
        self.other_profile = PatientProfile.objects.create(user=self.other_patient_user)
        self.case = FollowUpCase.objects.create(
            patient=self.profile,
            workflow=self.workflow,
            treatment_date=timezone.localdate() - timedelta(days=3),
        )
        self.other_case = FollowUpCase.objects.create(
            patient=self.other_profile,
            workflow=self.workflow,
            treatment_date=timezone.localdate() - timedelta(days=2),
        )

    def report_payload(self, follow_up_case=None, **overrides):
        payload = {
            "follow_up_case": (follow_up_case or self.case).id,
            "pain_level": 4,
            "swelling": "MILD",
            "bleeding": "NONE",
            "fever": False,
            "bad_smell": False,
            "notes": "Mild soreness.",
        }
        payload.update(overrides)
        return payload

    def test_patient_can_create_report_for_own_active_case(self):
        self.client.force_authenticate(self.patient_user)

        response = self.client.post(
            "/api/reports/symptom-reports/",
            self.report_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        report = SymptomReport.objects.get()
        self.assertEqual(report.submitted_by, self.patient_user)
        self.assertEqual(report.follow_up_case, self.case)
        self.assertEqual(report.day_after_treatment, 3)

    def test_patient_cannot_create_report_for_another_patient_case(self):
        self.client.force_authenticate(self.patient_user)

        response = self.client.post(
            "/api/reports/symptom-reports/",
            self.report_payload(self.other_case),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(SymptomReport.objects.count(), 0)

    def test_patient_cannot_submit_for_closed_or_resolved_case(self):
        self.client.force_authenticate(self.patient_user)

        for status in (FollowUpCaseStatus.CLOSED, FollowUpCaseStatus.RESOLVED):
            self.case.status = status
            self.case.save(update_fields=["status"])
            response = self.client.post(
                "/api/reports/symptom-reports/",
                self.report_payload(),
                format="json",
            )

            self.assertEqual(response.status_code, 400)

        self.assertEqual(SymptomReport.objects.count(), 0)

    def test_patient_can_view_own_reports_only(self):
        own_report = SymptomReport.objects.create(
            follow_up_case=self.case,
            submitted_by=self.patient_user,
            pain_level=2,
            swelling="NONE",
            bleeding="NONE",
            fever=False,
            bad_smell=False,
        )
        other_report = SymptomReport.objects.create(
            follow_up_case=self.other_case,
            submitted_by=self.other_patient_user,
            pain_level=5,
            swelling="MILD",
            bleeding="NONE",
            fever=False,
            bad_smell=False,
        )
        self.client.force_authenticate(self.patient_user)

        list_response = self.client.get("/api/reports/symptom-reports/")
        own_response = self.client.get(f"/api/reports/symptom-reports/{own_report.id}/")
        other_response = self.client.get(f"/api/reports/symptom-reports/{other_report.id}/")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual([item["id"] for item in list_response.data], [own_report.id])
        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(other_response.status_code, 404)

    def test_staff_can_view_reports_but_cannot_create_them(self):
        report = SymptomReport.objects.create(
            follow_up_case=self.case,
            submitted_by=self.patient_user,
            pain_level=2,
            swelling="NONE",
            bleeding="NONE",
            fever=False,
            bad_smell=False,
        )
        self.client.force_authenticate(self.dentist)

        list_response = self.client.get("/api/reports/symptom-reports/")
        detail_response = self.client.get(f"/api/reports/symptom-reports/{report.id}/")
        create_response = self.client.post(
            "/api/reports/symptom-reports/",
            self.report_payload(),
            format="json",
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(create_response.status_code, 403)

    def test_invalid_pain_level_and_choices_are_rejected(self):
        self.client.force_authenticate(self.patient_user)

        pain_response = self.client.post(
            "/api/reports/symptom-reports/",
            self.report_payload(pain_level=11),
            format="json",
        )
        choice_response = self.client.post(
            "/api/reports/symptom-reports/",
            self.report_payload(swelling="MODERATE"),
            format="json",
        )

        self.assertEqual(pain_response.status_code, 400)
        self.assertEqual(choice_response.status_code, 400)
        self.assertEqual(SymptomReport.objects.count(), 0)

    def test_optional_image_is_not_required(self):
        self.client.force_authenticate(self.patient_user)

        response = self.client.post(
            "/api/reports/symptom-reports/",
            self.report_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertFalse(SymptomReport.objects.get().image)

    def test_legacy_dynamic_payload_works_without_workflow_symptom_definitions(self):
        self.client.force_authenticate(self.patient_user)

        response = self.client.post(
            "/api/reports/symptom-reports/",
            {
                "follow_up_case": self.case.id,
                "symptom_values": {
                    "pain_level": "3",
                    "swelling": "MILD",
                    "bleeding": "NONE",
                    "fever": "false",
                    "bad_smell": "false",
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        report = SymptomReport.objects.get(id=response.data["id"])
        self.assertEqual(report.symptom_values["pain_level"], 3)
        self.assertEqual(report.pain_level, 3)
        self.assertEqual(report.swelling, "MILD")

    def test_patient_can_submit_workflow_defined_dynamic_symptoms(self):
        SymptomDefinition.objects.create(
            workflow=self.workflow,
            key="pain_level",
            label="Pain level",
            data_type=SymptomDataType.INTEGER,
            min_value=0,
            max_value=10,
        )
        SymptomDefinition.objects.create(
            workflow=self.workflow,
            key="swelling",
            label="Swelling",
            data_type=SymptomDataType.CHOICE,
            allowed_values=["NONE", "MILD", "SEVERE"],
        )
        SymptomDefinition.objects.create(
            workflow=self.workflow,
            key="numbness",
            label="Numbness",
            data_type=SymptomDataType.BOOLEAN,
        )
        SymptomDefinition.objects.create(
            workflow=self.workflow,
            key="extra_notes",
            label="Extra notes",
            data_type=SymptomDataType.TEXT,
            is_required=False,
        )
        self.client.force_authenticate(self.patient_user)

        response = self.client.post(
            "/api/reports/symptom-reports/",
            {
                "follow_up_case": self.case.id,
                "symptom_values": {
                    "pain_level": "4",
                    "swelling": "MILD",
                    "numbness": "true",
                    "extra_notes": "Lip feels numb.",
                },
                "notes": "Supporting note stays separate.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        report = SymptomReport.objects.get(id=response.data["id"])
        self.assertEqual(
            report.symptom_values,
            {
                "pain_level": 4,
                "swelling": "MILD",
                "numbness": True,
                "extra_notes": "Lip feels numb.",
            },
        )
        self.assertEqual(report.pain_level, 4)
        self.assertEqual(report.swelling, "MILD")
        self.assertEqual(report.bleeding, "NONE")
        self.assertFalse(report.fever)
        self.assertFalse(report.bad_smell)

    def test_dynamic_choice_value_must_match_workflow_allowed_values(self):
        SymptomDefinition.objects.create(
            workflow=self.workflow,
            key="swelling",
            label="Swelling",
            data_type=SymptomDataType.CHOICE,
            allowed_values=["NONE", "MILD", "SEVERE"],
        )
        self.client.force_authenticate(self.patient_user)

        response = self.client.post(
            "/api/reports/symptom-reports/",
            {
                "follow_up_case": self.case.id,
                "symptom_values": {"swelling": "MODERATE"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(SymptomReport.objects.count(), 0)
