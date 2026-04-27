from django.contrib import admin

from .models import EscalationCase


@admin.register(EscalationCase)
class EscalationCaseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "patient_username",
        "urgency",
        "status",
        "assigned_staff",
        "created_at",
    )
    list_filter = ("urgency", "status", "created_at")
    search_fields = (
        "patient__user__username",
        "staff_response",
        "report__notes",
    )
    readonly_fields = ("created_at", "updated_at", "resolved_at")

    def patient_username(self, obj):
        return obj.patient.user.username
