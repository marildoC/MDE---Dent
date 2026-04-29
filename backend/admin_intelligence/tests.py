from datetime import datetime, time, timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User, UserRole
from appointments.models import Appointment, AppointmentStatus
from audit import actions as audit_actions
from audit.models import AuditLog
from audit.services import record_audit
from decision_engine.models import RiskAssessment
from escalations.models import EscalationCase, EscalationStatus
from patients.models import FollowUpCase, PatientProfile
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


class AdminIntelligenceAPITests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin1",
            password="testpass123",
            role=UserRole.ADMIN,
        )
        self.dentist = User.objects.create_user(
            username="dentist1",
            password="testpass123",
            role=UserRole.DENTIST,
        )
        self.patient_user = User.objects.create_user(
            username="patient1",
            password="testpass123",
            role=UserRole.PATIENT,
        )
        self.workflow = TreatmentWorkflow.objects.create(
            name="Post-Extraction Follow-Up",
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
        self.case = FollowUpCase.objects.create(
            patient=self.profile,
            workflow=self.workflow,
            treatment_date=timezone.localdate() - timedelta(days=4),
            assigned_staff=self.dentist,
        )
        self.report = SymptomReport.objects.create(
            follow_up_case=self.case,
            submitted_by=self.patient_user,
            pain_level=9,
            swelling="SEVERE",
            bleeding="NONE",
            fever=False,
            bad_smell=True,
        )
        self.assessment = RiskAssessment.objects.create(
            report=self.report,
            detected_stage=self.stage,
            matched_rules=[],
            risk_level=RiskLevel.HIGH,
            recommended_action=RecommendedAction.ESCALATE_TO_DENTIST,
            appointment_priority=AppointmentPriority.HIGH,
            explanation="High-risk test assessment.",
        )
        self.escalation = EscalationCase.objects.create(
            risk_assessment=self.assessment,
            report=self.report,
            follow_up_case=self.case,
            patient=self.profile,
            urgency=RiskLevel.HIGH,
            status=EscalationStatus.NEW,
            assigned_staff=self.dentist,
        )
        self.appointment = Appointment.objects.create(
            patient=self.profile,
            follow_up_case=self.case,
            escalation_case=self.escalation,
            risk_assessment=self.assessment,
            priority=AppointmentPriority.HIGH,
            status=AppointmentStatus.PRIORITY_SUGGESTED,
            scheduled_at=timezone.make_aware(datetime.combine(timezone.localdate(), time(10, 30))),
            created_by=self.admin,
        )
        record_audit(
            self.admin,
            audit_actions.FOLLOW_UP_CASE_CREATED,
            self.case,
            {
                "follow_up_case_id": self.case.id,
                "patient_id": self.profile.id,
                "workflow_id": self.workflow.id,
            },
        )

    def ask(self, question, user=None):
        self.client.force_authenticate(user or self.admin)
        return self.client.post(
            "/api/admin-intelligence/query/",
            {"question": question},
            format="json",
        )

    def test_admin_can_use_query_endpoint(self):
        response = self.ask("How many follow-up cases does patient1 have?")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "count_follow_up_cases_for_patient")
        self.assertEqual(response.data["data"]["count"], 1)

    def test_patient_cannot_use_query_endpoint(self):
        response = self.ask("Show recent audit events", user=self.patient_user)

        self.assertEqual(response.status_code, 403)

    def test_dentist_cannot_use_query_endpoint(self):
        response = self.ask("Show recent audit events", user=self.dentist)

        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_cannot_use_query_endpoint(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            "/api/admin-intelligence/query/",
            {"question": "Show recent audit events"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_unsupported_question_returns_safe_response(self):
        response = self.ask("Can you show patient billing trends?")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["display_type"], "unsupported")
        self.assertGreaterEqual(len(response.data["suggested_followups"]), 1)

    def test_keyword_specific_unsupported_suggestions(self):
        examples = [
            ("Can you show patient billing trends?", "Show latest follow-up case for patient1"),
            ("Can you optimize appointment staffing?", "Show completed appointments today"),
            ("Can escalation workload be forecast?", "Show unresolved urgent escalations"),
            ("Can workflow revenue be predicted?", "Show active workflows"),
            ("Can history anomalies be scored?", "Show recent audit events"),
            ("Can risk trends be forecast?", "Show high-risk reports today"),
        ]

        for question, expected_suggestion in examples:
            response = self.ask(question)
            self.assertEqual(response.status_code, 200, question)
            self.assertEqual(response.data["display_type"], "unsupported", question)
            self.assertIn(expected_suggestion, response.data["suggested_followups"], question)

    def test_latest_follow_up_case_by_patient(self):
        response = self.ask("Show latest follow-up case for patient1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "latest_follow_up_case_for_patient")
        self.assertEqual(response.data["cards"][0]["title"], f"Case #{self.case.id}")

    def test_appointments_scheduled_today(self):
        response = self.ask("How many appointments are scheduled today?")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "appointments_scheduled_today")
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(response.data["rows"][0]["patient"], "patient1")
        self.assertEqual(response.data["rows"][0]["status"], AppointmentStatus.PRIORITY_SUGGESTED)

    def test_appointments_with_status_scheduled_today_filters_status(self):
        response = self.ask("How many appointments with status scheduled today?")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "appointments_scheduled_today")
        self.assertEqual(response.data["data"]["count"], 0)

    def test_patient_count_question(self):
        response = self.ask("How many patients are in this clinic?")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "patient_count")
        self.assertEqual(response.data["data"]["count"], 1)

    def test_active_follow_up_case_count_question(self):
        response = self.ask("How many active follow-up cases are there?")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "total_active_follow_up_cases")
        self.assertEqual(response.data["data"]["count"], 1)

    def test_reports_submitted_today_question(self):
        response = self.ask("How many reports were submitted today?")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "reports_submitted_today")
        self.assertEqual(response.data["data"]["count"], 1)

    def test_unresolved_escalations_count_question(self):
        response = self.ask("How many unresolved escalations exist?")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "count_unresolved_escalations")
        self.assertEqual(response.data["data"]["count"], 1)

    def test_appointment_required_cases_question(self):
        self.case.status = "APPOINTMENT_REQUIRED"
        self.case.save(update_fields=["status"])

        response = self.ask("Show appointment-required cases")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "appointment_required_cases")
        self.assertEqual(response.data["data"]["count"], 1)

    def test_unresolved_urgent_escalations(self):
        urgent_report = SymptomReport.objects.create(
            follow_up_case=self.case,
            submitted_by=self.patient_user,
            pain_level=10,
            swelling="SEVERE",
            bleeding="SEVERE",
            fever=True,
            bad_smell=True,
        )
        urgent_assessment = RiskAssessment.objects.create(
            report=urgent_report,
            detected_stage=self.stage,
            matched_rules=[],
            risk_level=RiskLevel.URGENT,
            recommended_action=RecommendedAction.ESCALATE_TO_DENTIST,
            appointment_priority=AppointmentPriority.URGENT,
            explanation="Urgent test assessment.",
        )
        EscalationCase.objects.create(
            risk_assessment=urgent_assessment,
            report=urgent_report,
            follow_up_case=self.case,
            patient=self.profile,
            urgency=RiskLevel.URGENT,
            status=EscalationStatus.NEW,
        )

        response = self.ask("Show unresolved urgent escalations")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "urgent_unresolved_escalations")
        self.assertEqual(len(response.data["cards"]), 1)

    def test_active_workflows(self):
        response = self.ask("Which workflows are active?")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "active_workflows")
        self.assertEqual(response.data["rows"][0]["name"], "Post-Extraction Follow-Up")

    def test_recent_audit_events(self):
        response = self.ask("Show recent audit events")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "recent_audit_events")
        self.assertGreaterEqual(len(response.data["timeline"]), 1)

    def test_audit_trace_for_case(self):
        response = self.ask(f"Show audit trace for case {self.case.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "audit_trace_for_case")
        self.assertEqual(response.data["timeline"][0]["target"], f"FollowUpCase #{self.case.id}")

    def test_patient_not_found(self):
        response = self.ask("How many follow-up cases does missingpatient have?")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "patient_not_found")
        self.assertIn("No matching patient record", response.data["answer"])

    def test_typo_appointment_query_and_suggestions(self):
        response = self.ask("How many appointements are scheduled today?")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "appointments_scheduled_today")

        suggestions_response = self.client.get(
            "/api/admin-intelligence/suggestions/?q=appointement"
        )

        self.assertEqual(suggestions_response.status_code, 200)
        self.assertIn(
            "How many appointments are scheduled today?",
            suggestions_response.data["suggestions"],
        )

    def test_query_endpoint_is_read_only(self):
        counts_before = {
            "appointments": Appointment.objects.count(),
            "audit": AuditLog.objects.count(),
            "cases": FollowUpCase.objects.count(),
            "escalations": EscalationCase.objects.count(),
            "reports": SymptomReport.objects.count(),
            "risk_assessments": RiskAssessment.objects.count(),
            "workflows": TreatmentWorkflow.objects.count(),
        }

        response = self.ask("Show today’s appointments")

        counts_after = {
            "appointments": Appointment.objects.count(),
            "audit": AuditLog.objects.count(),
            "cases": FollowUpCase.objects.count(),
            "escalations": EscalationCase.objects.count(),
            "reports": SymptomReport.objects.count(),
            "risk_assessments": RiskAssessment.objects.count(),
            "workflows": TreatmentWorkflow.objects.count(),
        }
        self.assertEqual(response.status_code, 200)
        self.assertEqual(counts_after, counts_before)
