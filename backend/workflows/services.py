from django.core.exceptions import ValidationError

from .models import (
    AIAdviceBoundary,
    AppointmentPriority,
    CareStage,
    EscalationRule,
    RecommendedAction,
    RiskLevel,
    SymptomRule,
)
from .validators import LOGICAL_GROUPS, validate_condition_shape


ALLOWED_REPORT_FIELDS = {"day_after_treatment"}
REQUIRED_FORBIDDEN_TOPICS = {"diagnosis", "prescription"}


def validate_workflow(workflow):
    errors = []
    warnings = []

    stages = list(workflow.stages.all().order_by("start_day", "end_day", "id"))
    symptoms = list(workflow.symptom_definitions.all().order_by("key"))
    rules = list(
        SymptomRule.objects.filter(stage__workflow=workflow)
        .select_related("stage")
        .order_by("stage__start_day", "id")
    )

    _validate_structure(stages, symptoms, rules, errors)
    _validate_conditions(rules, symptoms, errors)
    _validate_safety(workflow, rules, errors)

    return {
        "is_valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def _validate_structure(stages, symptoms, rules, errors):
    if not stages:
        errors.append("Workflow must have at least one care stage.")

    if not symptoms:
        errors.append("Workflow must have at least one symptom definition.")

    if not rules:
        errors.append("Workflow must have at least one symptom rule.")

    symptom_keys = [symptom.key for symptom in symptoms]
    if len(symptom_keys) != len(set(symptom_keys)):
        errors.append("Symptom definitions must have unique keys within one workflow.")

    for stage in stages:
        if stage.end_day < stage.start_day:
            errors.append(f"Care stage '{stage.name}' has an invalid day range.")

    for previous, current in zip(stages, stages[1:]):
        if current.start_day <= previous.end_day:
            errors.append(
                f"Care stages '{previous.name}' and '{current.name}' overlap."
            )


def _validate_conditions(rules, symptoms, errors):
    allowed_fields = {symptom.key for symptom in symptoms} | ALLOWED_REPORT_FIELDS

    for rule in rules:
        try:
            validate_condition_shape(rule.condition)
        except ValidationError as exc:
            errors.append(f"Rule '{rule.name}' has invalid condition JSON: {'; '.join(exc.messages)}")
            continue

        for field in _condition_fields(rule.condition):
            if field not in allowed_fields:
                errors.append(
                    f"Rule '{rule.name}' references unknown condition field '{field}'."
                )


def _condition_fields(condition):
    fields = []
    for group in LOGICAL_GROUPS:
        if group not in condition:
            continue
        for item in condition[group]:
            if any(key in item for key in LOGICAL_GROUPS):
                fields.extend(_condition_fields(item))
            else:
                fields.append(item["field"])
    return fields


def _validate_safety(workflow, rules, errors):
    escalation_rule_ids = set(
        EscalationRule.objects.filter(symptom_rule__in=rules).values_list(
            "symptom_rule_id",
            flat=True,
        )
    )

    for rule in rules:
        if rule.risk_level in {RiskLevel.HIGH, RiskLevel.URGENT}:
            if rule.id not in escalation_rule_ids:
                errors.append(f"{rule.risk_level} rule '{rule.name}' must have an escalation rule.")

            if rule.recommended_action == RecommendedAction.SHOW_ADVICE:
                errors.append(
                    f"{rule.risk_level} rule '{rule.name}' cannot use only patient-facing advice."
                )

    workflow_boundaries = AIAdviceBoundary.objects.filter(workflow=workflow, stage__isnull=True)
    forbidden_topics = set()
    for boundary in workflow_boundaries:
        forbidden_topics.update(str(topic).strip().lower() for topic in boundary.forbidden_topics)

    missing_topics = REQUIRED_FORBIDDEN_TOPICS - forbidden_topics
    if missing_topics:
        errors.append(
            "Workflow-level AI advice boundary must forbid diagnosis and prescription."
        )

    invalid_escalations = EscalationRule.objects.filter(
        symptom_rule__stage__workflow=workflow,
        appointment_priority=AppointmentPriority.NONE,
    )
    if invalid_escalations.exists():
        errors.append("Escalation rules must define an appointment priority.")


def workflow_for_instance(instance):
    if hasattr(instance, "workflow"):
        return instance.workflow
    if hasattr(instance, "stage"):
        return instance.stage.workflow
    if hasattr(instance, "symptom_rule"):
        return instance.symptom_rule.stage.workflow
    return instance


def workflow_for_validated_data(validated_data):
    workflow = validated_data.get("workflow")
    if workflow:
        return workflow

    stage = validated_data.get("stage")
    if stage:
        return stage.workflow

    symptom_rule = validated_data.get("symptom_rule")
    if symptom_rule:
        return symptom_rule.stage.workflow

    return None
