from django.contrib import admin

from .models import RiskAssessment


@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "report",
        "patient_username",
        "detected_stage",
        "risk_level",
        "recommended_action",
        "appointment_priority",
        "created_at",
    )
    list_filter = ("risk_level", "recommended_action", "appointment_priority", "created_at")
    search_fields = (
        "report__submitted_by__username",
        "report__follow_up_case__patient__user__username",
        "detected_stage__name",
    )
    readonly_fields = ("created_at", "updated_at")

    def patient_username(self, obj):
        return obj.report.follow_up_case.patient.user.username
