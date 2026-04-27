from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "actor", "target_type", "target_id", "target_repr")
    list_filter = ("action", "target_type", "created_at")
    search_fields = ("action", "target_type", "target_id", "target_repr", "actor__username")
    readonly_fields = (
        "actor",
        "action",
        "target_type",
        "target_id",
        "target_repr",
        "details",
        "created_at",
    )
