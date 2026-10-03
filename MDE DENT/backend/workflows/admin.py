from django.contrib import admin

from .models import (
    AIAdviceBoundary,
    CareStage,
    EscalationRule,
    SymptomDefinition,
    SymptomRule,
    TreatmentWorkflow,
)


class CareStageInline(admin.TabularInline):
    model = CareStage
    extra = 0


class SymptomDefinitionInline(admin.TabularInline):
    model = SymptomDefinition
    extra = 0


@admin.register(TreatmentWorkflow)
class TreatmentWorkflowAdmin(admin.ModelAdmin):
    list_display = ("name", "treatment_type", "status", "created_by", "updated_at")
    list_filter = ("treatment_type", "status")
    search_fields = ("name", "description")
    inlines = (CareStageInline, SymptomDefinitionInline)


@admin.register(CareStage)
class CareStageAdmin(admin.ModelAdmin):
    list_display = ("name", "workflow", "start_day", "end_day", "sort_order")
    list_filter = ("workflow",)
    search_fields = ("name", "workflow__name")


@admin.register(SymptomDefinition)
class SymptomDefinitionAdmin(admin.ModelAdmin):
    list_display = ("key", "label", "workflow", "data_type", "is_required")
    list_filter = ("workflow", "data_type", "is_required")
    search_fields = ("key", "label", "workflow__name")


@admin.register(SymptomRule)
class SymptomRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "stage", "risk_level", "recommended_action", "appointment_priority")
    list_filter = ("risk_level", "recommended_action", "appointment_priority")
    search_fields = ("name", "stage__name", "stage__workflow__name")


@admin.register(AIAdviceBoundary)
class AIAdviceBoundaryAdmin(admin.ModelAdmin):
    list_display = ("workflow", "stage")
    list_filter = ("workflow",)


@admin.register(EscalationRule)
class EscalationRuleAdmin(admin.ModelAdmin):
    list_display = ("symptom_rule", "target_role", "urgency", "appointment_priority")
    list_filter = ("target_role", "urgency", "appointment_priority")
