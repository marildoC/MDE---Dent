from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User, UserRole
from decision_engine.models import RiskAssessment
from escalations.models import EscalationCase, EscalationStatus
from patients.models import FollowUpCase, FollowUpCaseStatus, PatientProfile
from reports.models import SymptomReport
from workflows.models import (
    AppointmentPriority,
    CareStage,
    RecommendedAction,
    RiskLevel,
    TreatmentType,
    TreatmentWorkflow,
    WorkflowStatus,
)

from .models import Appointment, AppointmentStatus


class AppointmentTests(APITestCase):
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

    def make_report(self, follow_up_case=None):
        follow_up_case = follow_up_case or self.case
        return SymptomReport.objects.create(
            follow_up_case=follow_up_case,
            submitted_by=follow_up_case.patient.user,
            pain_level=8,
            swelling="SEVERE",
            bleeding="NONE",
            fever=False,
            bad_smell=True,
        )

    def make_assessment(
        self,
        follow_up_case=None,
        risk_level=RiskLevel.HIGH,
        appointment_priority=AppointmentPriority.HIGH,
    ):
        report = self.make_report(follow_up_case=follow_up_case)
        return RiskAssessment.objects.create(
            report=report,
            detected_stage=self.stage,
            matched_rules=[],
            risk_level=risk_level,
            recommended_action=RecommendedAction.ESCALATE_TO_DENTIST,
            appointment_priority=appointment_priority,
            explanation="Test assessment.",
        )

    def make_escalation(self, follow_up_case=None, **assessment_overrides):
        assessment = self.make_assessment(
            follow_up_case=follow_up_case,
            **assessment_overrides,
        )
        return EscalationCase.objects.create(
            risk_assessment=assessment,
            report=assessment.report,
            follow_up_case=assessment.report.follow_up_case,
            patient=assessment.report.follow_up_case.patient,
            urgency=assessment.risk_level,
            assigned_staff=assessment.report.follow_up_case.assigned_staff,
        )

    def test_staff_can_create_appointment_for_escalation(self):
        escalation = self.make_escalation()
        self.client.force_authenticate(self.dentist)

        response = self.client.post(
            "/api/appointments/appointments/",
            {
                "escalation_case": escalation.id,
                "scheduled_at": "2026-05-01T09:00:00Z",
                "notes": "Priority review.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        appointment = Appointment.objects.get()
        self.assertEqual(appointment.patient, self.profile)
        self.assertEqual(appointment.follow_up_case, self.case)
        self.assertEqual(appointment.risk_assessment, escalation.risk_assessment)
        self.assertEqual(appointment.priority, AppointmentPriority.HIGH)
        self.assertEqual(appointment.status, AppointmentStatus.PRIORITY_SUGGESTED)
        self.assertEqual(appointment.created_by, self.dentist)
        escalation.refresh_from_db()
        self.case.refresh_from_db()
        self.assertEqual(escalation.status, EscalationStatus.APPOINTMENT_REQUIRED)
        self.assertEqual(self.case.status, FollowUpCaseStatus.APPOINTMENT_REQUIRED)

    def test_priority_falls_back_to_escalation_urgency_when_assessment_priority_is_none(self):
        escalation = self.make_escalation(
            risk_level=RiskLevel.URGENT,
            appointment_priority=AppointmentPriority.NONE,
        )
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/api/appointments/appointments/",
            {"escalation_case": escalation.id},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["priority"], AppointmentPriority.URGENT)

    def test_patient_cannot_create_or_update_appointment(self):
        escalation = self.make_escalation()
        appointment = Appointment.objects.create(
            patient=self.profile,
            follow_up_case=self.case,
            escalation_case=escalation,
            risk_assessment=escalation.risk_assessment,
            priority=AppointmentPriority.HIGH,
            created_by=self.dentist,
        )
        self.client.force_authenticate(self.patient_user)

        create_response = self.client.post(
            "/api/appointments/appointments/",
            {"escalation_case": escalation.id},
            format="json",
        )
        update_response = self.client.patch(
            f"/api/appointments/appointments/{appointment.id}/",
            {"status": AppointmentStatus.CANCELLED},
            format="json",
        )

        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(update_response.status_code, 403)

    def test_patient_can_view_only_own_appointments(self):
        own_escalation = self.make_escalation()
        other_escalation = self.make_escalation(follow_up_case=self.other_case)
        own_appointment = Appointment.objects.create(
            patient=self.profile,
            follow_up_case=self.case,
            escalation_case=own_escalation,
            risk_assessment=own_escalation.risk_assessment,
            priority=AppointmentPriority.HIGH,
            created_by=self.dentist,
        )
        other_appointment = Appointment.objects.create(
            patient=self.other_profile,
            follow_up_case=self.other_case,
            escalation_case=other_escalation,
            risk_assessment=other_escalation.risk_assessment,
            priority=AppointmentPriority.HIGH,
            created_by=self.admin,
        )
        self.client.force_authenticate(self.patient_user)

        list_response = self.client.get("/api/appointments/appointments/")
        own_response = self.client.get(f"/api/appointments/appointments/{own_appointment.id}/")
        other_response = self.client.get(f"/api/appointments/appointments/{other_appointment.id}/")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual([item["id"] for item in list_response.data], [own_appointment.id])
        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(other_response.status_code, 404)

    def test_duplicate_appointment_for_same_escalation_is_rejected(self):
        escalation = self.make_escalation()
        Appointment.objects.create(
            patient=self.profile,
            follow_up_case=self.case,
            escalation_case=escalation,
            risk_assessment=escalation.risk_assessment,
            priority=AppointmentPriority.HIGH,
            created_by=self.dentist,
        )
        self.client.force_authenticate(self.dentist)

        response = self.client.post(
            "/api/appointments/appointments/",
            {"escalation_case": escalation.id},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_staff_can_update_appointment_status_and_details(self):
        escalation = self.make_escalation()
        appointment = Appointment.objects.create(
            patient=self.profile,
            follow_up_case=self.case,
            escalation_case=escalation,
            risk_assessment=escalation.risk_assessment,
            priority=AppointmentPriority.HIGH,
            created_by=self.dentist,
        )
        self.client.force_authenticate(self.dentist)

        response = self.client.patch(
            f"/api/appointments/appointments/{appointment.id}/",
            {
                "status": AppointmentStatus.SCHEDULED,
                "scheduled_at": "2026-05-01T10:30:00Z",
                "notes": "Scheduled by staff.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, AppointmentStatus.SCHEDULED)
        self.assertEqual(appointment.notes, "Scheduled by staff.")

    def test_invalid_appointment_transition_is_rejected(self):
        escalation = self.make_escalation()
        appointment = Appointment.objects.create(
            patient=self.profile,
            follow_up_case=self.case,
            escalation_case=escalation,
            risk_assessment=escalation.risk_assessment,
            priority=AppointmentPriority.HIGH,
            created_by=self.dentist,
        )
        self.client.force_authenticate(self.dentist)

        response = self.client.patch(
            f"/api/appointments/appointments/{appointment.id}/",
            {"status": AppointmentStatus.COMPLETED},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, AppointmentStatus.PRIORITY_SUGGESTED)

    def test_completed_appointment_resolves_follow_up_case(self):
        escalation = self.make_escalation()
        self.client.force_authenticate(self.dentist)
        create_response = self.client.post(
            "/api/appointments/appointments/",
            {"escalation_case": escalation.id},
            format="json",
        )
        appointment_id = create_response.data["id"]

        scheduled_response = self.client.patch(
            f"/api/appointments/appointments/{appointment_id}/",
            {"status": AppointmentStatus.SCHEDULED},
            format="json",
        )
        completed_response = self.client.patch(
            f"/api/appointments/appointments/{appointment_id}/",
            {"status": AppointmentStatus.COMPLETED},
            format="json",
        )

        self.assertEqual(scheduled_response.status_code, 200)
        self.assertEqual(completed_response.status_code, 200)
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, FollowUpCaseStatus.RESOLVED)

    def test_cancelled_appointment_does_not_resolve_follow_up_case(self):
        escalation = self.make_escalation()
        self.client.force_authenticate(self.admin)
        create_response = self.client.post(
            "/api/appointments/appointments/",
            {"escalation_case": escalation.id},
            format="json",
        )

        response = self.client.patch(
            f"/api/appointments/appointments/{create_response.data['id']}/",
            {"status": AppointmentStatus.CANCELLED},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, FollowUpCaseStatus.APPOINTMENT_REQUIRED)

    def test_cross_patient_linkage_is_rejected_by_model_validation(self):
        escalation = self.make_escalation()
        appointment = Appointment(
            patient=self.other_profile,
            follow_up_case=self.case,
            escalation_case=escalation,
            risk_assessment=escalation.risk_assessment,
            priority=AppointmentPriority.HIGH,
            created_by=self.dentist,
        )

        with self.assertRaises(Exception):
            appointment.full_clean()
