from django.contrib import admin

from .models import SymptomReport


@admin.register(SymptomReport)
class SymptomReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "follow_up_case",
        "submitted_by",
        "day_after_treatment",
        "pain_level",
        "fever",
        "bad_smell",
        "created_at",
    )
    list_filter = ("swelling", "bleeding", "fever", "bad_smell", "created_at")
    search_fields = (
        "submitted_by__username",
        "follow_up_case__patient__user__username",
        "follow_up_case__workflow__name",
    )
    readonly_fields = ("day_after_treatment", "created_at", "updated_at")
