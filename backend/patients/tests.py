from datetime import date

from rest_framework.test import APITestCase

from accounts.models import User, UserRole
from workflows.models import TreatmentType, TreatmentWorkflow, WorkflowStatus

from .models import FollowUpCase, FollowUpCaseStatus, PatientProfile


class PatientFollowUpRuntimeTests(APITestCase):
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
        self.active_workflow = TreatmentWorkflow.objects.create(
            name="Active Post-Extraction",
            treatment_type=TreatmentType.POST_EXTRACTION,
            status=WorkflowStatus.ACTIVE,
            created_by=self.admin,
        )
        self.draft_workflow = TreatmentWorkflow.objects.create(
            name="Draft Post-Extraction",
            treatment_type=TreatmentType.POST_EXTRACTION,
            status=WorkflowStatus.DRAFT,
            created_by=self.admin,
        )

    def test_profile_can_be_created_for_patient_user(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/api/patients/profiles/",
            {"user": self.patient_user.id, "phone": "123"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(PatientProfile.objects.count(), 1)

    def test_profile_cannot_be_created_for_dentist_user(self):
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/api/patients/profiles/",
            {"user": self.dentist.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(PatientProfile.objects.count(), 0)

    def test_active_workflow_can_be_assigned_to_patient(self):
        profile = PatientProfile.objects.create(user=self.patient_user)
        self.client.force_authenticate(self.dentist)

        response = self.client.post(
            "/api/patients/follow-up-cases/",
            {
                "patient": profile.id,
                "workflow": self.active_workflow.id,
                "treatment_date": "2026-04-26",
                "assigned_staff": self.dentist.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(FollowUpCase.objects.count(), 1)
        self.assertEqual(FollowUpCase.objects.get().status, FollowUpCaseStatus.ACTIVE)

    def test_non_active_workflow_cannot_be_assigned(self):
        profile = PatientProfile.objects.create(user=self.patient_user)
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/api/patients/follow-up-cases/",
            {
                "patient": profile.id,
                "workflow": self.draft_workflow.id,
                "treatment_date": "2026-04-26",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(FollowUpCase.objects.count(), 0)

    def test_patient_can_view_own_case_but_not_other_patient_case(self):
        profile = PatientProfile.objects.create(user=self.patient_user)
        other_profile = PatientProfile.objects.create(user=self.other_patient_user)
        own_case = FollowUpCase.objects.create(
            patient=profile,
            workflow=self.active_workflow,
            treatment_date=date(2026, 4, 26),
        )
        other_case = FollowUpCase.objects.create(
            patient=other_profile,
            workflow=self.active_workflow,
            treatment_date=date(2026, 4, 26),
        )
        self.client.force_authenticate(self.patient_user)

        own_response = self.client.get(f"/api/patients/follow-up-cases/{own_case.id}/")
        other_response = self.client.get(f"/api/patients/follow-up-cases/{other_case.id}/")

        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(other_response.status_code, 404)

    def test_patient_cannot_create_follow_up_case(self):
        profile = PatientProfile.objects.create(user=self.patient_user)
        self.client.force_authenticate(self.patient_user)

        response = self.client.post(
            "/api/patients/follow-up-cases/",
            {
                "patient": profile.id,
                "workflow": self.active_workflow.id,
                "treatment_date": "2026-04-26",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(FollowUpCase.objects.count(), 0)

    def test_staff_can_view_and_manage_follow_up_cases(self):
        profile = PatientProfile.objects.create(user=self.patient_user)
        case = FollowUpCase.objects.create(
            patient=profile,
            workflow=self.active_workflow,
            treatment_date=date(2026, 4, 26),
        )
        self.client.force_authenticate(self.dentist)

        list_response = self.client.get("/api/patients/follow-up-cases/")
        update_response = self.client.patch(
            f"/api/patients/follow-up-cases/{case.id}/",
            {"notes": "Reviewed by staff."},
            format="json",
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(update_response.status_code, 200)
        case.refresh_from_db()
        self.assertEqual(case.notes, "Reviewed by staff.")

    def test_my_active_case_returns_own_case_or_null(self):
        profile = PatientProfile.objects.create(user=self.patient_user)
        case = FollowUpCase.objects.create(
            patient=profile,
            workflow=self.active_workflow,
            treatment_date=date(2026, 4, 26),
        )
        self.client.force_authenticate(self.patient_user)

        case_response = self.client.get("/api/patients/my-active-case/")
        case_id = case.id
        case.delete()
        null_response = self.client.get("/api/patients/my-active-case/")

        self.assertEqual(case_response.status_code, 200)
        self.assertEqual(case_response.data["id"], case_id)
        self.assertEqual(case_response.data["workflow_detail"]["name"], self.active_workflow.name)
        self.assertEqual(null_response.status_code, 200)
        self.assertIsNone(null_response.data)
