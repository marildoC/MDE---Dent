from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "patient_username",
        "priority",
        "status",
        "scheduled_at",
        "created_at",
    )
    list_filter = ("priority", "status", "created_at")
    search_fields = (
        "patient__user__username",
        "notes",
    )
    readonly_fields = ("created_at", "updated_at")

    def patient_username(self, obj):
        return obj.patient.user.username
