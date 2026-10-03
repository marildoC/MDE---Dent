from django.contrib import admin

from .models import AdviceMessage


@admin.register(AdviceMessage)
class AdviceMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "risk_assessment",
        "patient_username",
        "message_type",
        "source",
        "created_at",
    )
    list_filter = ("message_type", "source", "created_at")
    search_fields = (
        "risk_assessment__report__follow_up_case__patient__user__username",
        "message",
    )
    readonly_fields = ("created_at", "updated_at")

    def patient_username(self, obj):
        return obj.risk_assessment.report.follow_up_case.patient.user.username
