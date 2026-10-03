from django.core.exceptions import ValidationError

from .models import (
    AIAdviceBoundary,
    AppointmentPriority,
    CareStage,
    EscalationRule,
    RecommendedAction,
    RiskLevel,
    SymptomDataType,
    SymptomRule,
)
from .condition_formatting import format_condition
from .validators import LOGICAL_GROUPS, validate_condition_shape


ALLOWED_REPORT_FIELDS = {"day_after_treatment"}
REQUIRED_FORBIDDEN_TOPICS = {"diagnosis", "prescription"}


def validate_workflow(workflow):
    warnings = []
    checks, errors = _build_validation_checks(workflow)

    return {
        "is_valid": not errors,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
    }


def render_workflow_dsl_preview(workflow):
    stages = list(workflow.stages.all().order_by("sort_order", "start_day", "id"))
    symptoms = list(workflow.symptom_definitions.all().order_by("key"))
    boundaries = list(
        AIAdviceBoundary.objects.filter(workflow=workflow)
        .select_related("stage")
        .order_by("stage_id", "id")
    )
    escalation_rules = list(
        EscalationRule.objects.filter(symptom_rule__stage__workflow=workflow)
        .select_related("symptom_rule")
        .order_by("symptom_rule__stage__start_day", "symptom_rule_id")
    )

    lines = [
        f'workflow "{workflow.name}" {{',
        f"  treatment {_display_choice(workflow, 'treatment_type')}",
        f"  status {_display_choice(workflow, 'status')}",
    ]

    if stages:
        lines.append("")

    for index, stage in enumerate(stages):
        if index:
            lines.append("")
        lines.extend(_render_stage(stage, symptoms))

    if boundaries:
        lines.append("")
        lines.extend(_render_advice_boundaries(boundaries))

    if escalation_rules:
        lines.append("")
        lines.extend(_render_escalation_rules(escalation_rules))

    lines.append("}")
    return "\n".join(lines)


def _render_stage(stage, symptoms):
    lines = [f'  stage "{stage.name}" from day {stage.start_day} to day {stage.end_day} {{']

    for symptom in symptoms:
        lines.append(f"    symptom {symptom.key}: {_dsl_data_type(symptom.data_type)}")

    rules = list(stage.symptom_rules.all().order_by("id"))
    if symptoms and rules:
        lines.append("")

    for index, rule in enumerate(rules):
        if index:
            lines.append("")
        lines.extend(
            [
                f'    rule "{rule.name}" {{',
                f"      when {format_condition(rule.condition)}",
                f"      risk {rule.risk_level}",
                f"      action {rule.recommended_action}",
            ]
        )
        if rule.appointment_priority:
            lines.append(f"      appointment {rule.appointment_priority}")
        lines.append("    }")

    lines.append("  }")
    return lines


def _render_advice_boundaries(boundaries):
    lines = ["  advice_boundary {"]
    for boundary in boundaries:
        for topic in boundary.allowed_topics:
            lines.append(f"    allow {topic}")
        for topic in boundary.forbidden_topics:
            lines.append(f"    forbid {topic}")
        if boundary.required_disclaimer:
            lines.append("    require disclaimer")
    lines.append("  }")
    return lines


def _render_escalation_rules(escalation_rules):
    lines = ["  escalation {"]
    for escalation_rule in escalation_rules:
        lines.extend(
            [
                f'    rule "{escalation_rule.symptom_rule.name}"',
                f"    urgency {escalation_rule.urgency}",
                f"    appointment {escalation_rule.appointment_priority}",
            ]
        )
    lines.append("  }")
    return lines


def _display_choice(instance, field_name):
    display = getattr(instance, f"get_{field_name}_display", None)
    value = display() if display else str(getattr(instance, field_name))
    return value.replace("- Follow-Up", "").replace("-", " ")


def _dsl_data_type(data_type):
    return {
        SymptomDataType.INTEGER: "number",
        SymptomDataType.BOOLEAN: "boolean",
        SymptomDataType.CHOICE: "choice",
        SymptomDataType.TEXT: "text",
    }.get(data_type, str(data_type).lower())


def _build_validation_checks(workflow):
    stages = list(workflow.stages.all().order_by("start_day", "end_day", "id"))
    symptoms = list(workflow.symptom_definitions.all().order_by("key"))
    rules = list(
        SymptomRule.objects.filter(stage__workflow=workflow)
        .select_related("stage")
        .order_by("stage__start_day", "id")
    )

    checks = []
    errors = []

    _add_check(
        checks,
        errors,
        "stages_exist",
        "Workflow has at least one care stage",
        not stages,
        ["Workflow must have at least one care stage."] if not stages else [],
    )

    invalid_stage_messages = [
        f"Care stage '{stage.name}' has an invalid day range."
        for stage in stages
        if stage.end_day < stage.start_day
    ]
    _add_check(
        checks,
        errors,
        "stage_ranges_valid",
        "Care stages have valid day ranges",
        bool(invalid_stage_messages),
        invalid_stage_messages,
    )

    overlapping_stage_messages = [
        f"Care stages '{previous.name}' and '{current.name}' overlap."
        for previous, current in zip(stages, stages[1:])
        if current.start_day <= previous.end_day
    ]
    _add_check(
        checks,
        errors,
        "stage_ranges_do_not_overlap",
        "Care stages do not overlap",
        bool(overlapping_stage_messages),
        overlapping_stage_messages,
    )

    _add_check(
        checks,
        errors,
        "symptoms_exist",
        "Workflow has symptom definitions",
        not symptoms,
        ["Workflow must have at least one symptom definition."] if not symptoms else [],
    )

    symptom_keys = [symptom.key for symptom in symptoms]
    duplicate_symptom_messages = []
    if len(symptom_keys) != len(set(symptom_keys)):
        duplicate_symptom_messages.append("Symptom definitions must have unique keys within one workflow.")
    _add_check(
        checks,
        errors,
        "symptom_keys_unique",
        "Symptom keys are unique within the workflow",
        bool(duplicate_symptom_messages),
        duplicate_symptom_messages,
    )

    _add_check(
        checks,
        errors,
        "rules_exist",
        "Workflow has symptom rules",
        not rules,
        ["Workflow must have at least one symptom rule."] if not rules else [],
    )

    _add_condition_checks(checks, errors, rules, symptoms)
    _add_safety_checks(checks, errors, workflow, rules)
    _add_check(
        checks,
        errors,
        "workflow_can_be_activated",
        "Workflow can pass activation validation",
        bool(errors),
        ["Workflow cannot be activated until all static semantic checks pass."] if errors else [],
        include_in_errors=False,
    )

    return checks, errors


def _add_condition_checks(checks, errors, rules, symptoms):
    allowed_fields = {symptom.key for symptom in symptoms} | ALLOWED_REPORT_FIELDS
    shape_messages = []
    unknown_field_messages = []

    for rule in rules:
        try:
            validate_condition_shape(rule.condition)
        except ValidationError as exc:
            shape_messages.append(
                f"Rule '{rule.name}' has invalid condition JSON: {'; '.join(exc.messages)}"
            )
            continue

        for field in _condition_fields(rule.condition):
            if field not in allowed_fields:
                unknown_field_messages.append(
                    f"Rule '{rule.name}' references unknown condition field '{field}'."
                )

    _add_check(
        checks,
        errors,
        "rule_condition_shape_valid",
        "Rule condition JSON shape is valid",
        bool(shape_messages),
        shape_messages,
    )
    _add_check(
        checks,
        errors,
        "rule_operators_supported",
        "Rule operators are supported",
        bool(shape_messages),
        shape_messages,
        include_in_errors=False,
    )
    _add_check(
        checks,
        errors,
        "rule_references_known_fields",
        "Rules reference known symptoms or allowed report fields",
        bool(unknown_field_messages),
        unknown_field_messages,
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


def _add_safety_checks(checks, errors, workflow, rules):
    escalation_rule_ids = set(
        EscalationRule.objects.filter(symptom_rule__in=rules).values_list(
            "symptom_rule_id",
            flat=True,
        )
    )
    missing_escalation_messages = []
    advice_only_messages = []

    for rule in rules:
        if rule.risk_level in {RiskLevel.HIGH, RiskLevel.URGENT}:
            if rule.id not in escalation_rule_ids:
                missing_escalation_messages.append(
                    f"{rule.risk_level} rule '{rule.name}' must have an escalation rule."
                )

            if rule.recommended_action == RecommendedAction.SHOW_ADVICE:
                advice_only_messages.append(
                    f"{rule.risk_level} rule '{rule.name}' cannot use only patient-facing advice."
                )

    _add_check(
        checks,
        errors,
        "high_urgent_rules_have_escalation",
        "HIGH/URGENT rules have escalation behavior",
        bool(missing_escalation_messages),
        missing_escalation_messages,
    )
    _add_check(
        checks,
        errors,
        "high_urgent_rules_not_advice_only",
        "HIGH/URGENT rules are not handled only by patient-facing advice",
        bool(advice_only_messages),
        advice_only_messages,
    )

    workflow_boundaries = AIAdviceBoundary.objects.filter(workflow=workflow, stage__isnull=True)
    forbidden_topics = set()
    for boundary in workflow_boundaries:
        forbidden_topics.update(str(topic).strip().lower() for topic in boundary.forbidden_topics)

    missing_topics = REQUIRED_FORBIDDEN_TOPICS - forbidden_topics
    diagnosis_missing = "diagnosis" in missing_topics
    prescription_missing = "prescription" in missing_topics
    boundary_message = "Workflow-level AI advice boundary must forbid diagnosis and prescription."
    if missing_topics:
        errors.append(boundary_message)
    _add_check(
        checks,
        errors,
        "advice_boundary_forbids_diagnosis",
        "AI advice boundary forbids diagnosis",
        diagnosis_missing,
        [boundary_message] if diagnosis_missing else [],
        include_in_errors=False,
    )
    _add_check(
        checks,
        errors,
        "advice_boundary_forbids_prescription",
        "AI advice boundary forbids prescription",
        prescription_missing,
        [boundary_message] if prescription_missing else [],
        include_in_errors=False,
    )

    invalid_escalation_messages = []
    if EscalationRule.objects.filter(
        symptom_rule__stage__workflow=workflow,
        appointment_priority=AppointmentPriority.NONE,
    ).exists():
        invalid_escalation_messages.append("Escalation rules must define an appointment priority.")
    _add_check(
        checks,
        errors,
        "escalations_define_appointment_priority",
        "Escalation rules define appointment priority",
        bool(invalid_escalation_messages),
        invalid_escalation_messages,
    )


def _add_check(
    checks,
    errors,
    key,
    label,
    failed,
    messages,
    *,
    include_in_errors=True,
):
    messages = [message for message in messages if message]
    checks.append(
        {
            "key": key,
            "label": label,
            "status": "fail" if failed else "pass",
            "message": " ".join(messages),
        }
    )
    if failed and include_in_errors:
        errors.extend(messages)


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
