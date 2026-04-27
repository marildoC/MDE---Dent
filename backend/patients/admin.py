from django.contrib import admin

from .models import FollowUpCase, PatientProfile


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "created_at", "updated_at")
    search_fields = ("user__username", "user__email", "phone")


@admin.register(FollowUpCase)
class FollowUpCaseAdmin(admin.ModelAdmin):
    list_display = ("patient", "workflow", "treatment_date", "status", "assigned_staff")
    list_filter = ("status", "workflow", "treatment_date")
    search_fields = ("patient__user__username", "workflow__name", "assigned_staff__username")
