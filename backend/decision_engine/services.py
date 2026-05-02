from django.core.exceptions import ValidationError

from audit import actions as audit_actions
from audit.services import record_audit
from reports.models import SymptomReport
from workflows.models import (
    AppointmentPriority,
    CareStage,
    RecommendedAction,
    RiskLevel,
    SymptomRule,
)
from workflows.validators import validate_condition_shape

from .models import RiskAssessment


RISK_ORDER = {
    RiskLevel.LOW: 0,
    RiskLevel.WARNING: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.URGENT: 3,
}

def assess_report(report):
    report = _report_with_context(report)
    try:
        return _ensure_downstream_outputs(report.risk_assessment)
    except RiskAssessment.DoesNotExist:
        pass

    if not report.id:
        raise ValueError("Report must be saved before assessment.")

    existing = RiskAssessment.objects.filter(report=report).first()
    if existing:
        return _ensure_downstream_outputs(existing)

    detected_stage = detect_stage(report)
    if not detected_stage:
        return _create_with_advice(
            report=report,
            detected_stage=None,
            matched_rules=[],
            risk_level=RiskLevel.WARNING,
            recommended_action=RecommendedAction.RECOMMEND_CONTACT,
            appointment_priority=AppointmentPriority.NORMAL,
            explanation=(
                "No care stage matched this report day in the assigned workflow. "
                "The safest recommendation is to contact the clinic."
            ),
        )

    matched_rules = _matching_rules(report, detected_stage)
    if not matched_rules:
        return _create_with_advice(
            report=report,
            detected_stage=detected_stage,
            matched_rules=[],
            risk_level=RiskLevel.LOW,
            recommended_action=RecommendedAction.CONTINUE_MONITORING,
            appointment_priority=AppointmentPriority.NONE,
            explanation=(
                f"No symptom rule matched this report in stage '{detected_stage.name}'. "
                "Continue monitoring according to the active workflow."
            ),
        )

    selected_rule = max(
        matched_rules,
        key=lambda rule: RISK_ORDER.get(rule.risk_level, -1),
    )
    matched_rule_trace = [_rule_trace(rule) for rule in matched_rules]

    return _create_with_advice(
        report=report,
        detected_stage=detected_stage,
        matched_rules=matched_rule_trace,
        risk_level=selected_rule.risk_level,
        recommended_action=selected_rule.recommended_action,
        appointment_priority=selected_rule.appointment_priority,
        explanation=selected_rule.explanation,
    )


def _create_with_advice(**kwargs):
    assessment = RiskAssessment.objects.create(**kwargs)
    record_audit(
        None,
        audit_actions.RISK_ASSESSMENT_CREATED,
        assessment,
        {
            "report_id": assessment.report_id,
            "risk_level": assessment.risk_level,
            "recommended_action": assessment.recommended_action,
            "appointment_priority": assessment.appointment_priority,
            "matched_rule_ids": [
                rule.get("id")
                for rule in assessment.matched_rules
                if isinstance(rule, dict) and rule.get("id") is not None
            ],
        },
    )
    return _ensure_downstream_outputs(assessment)


def _ensure_downstream_outputs(assessment):
    from ai_support.services import generate_advice_for_assessment
    from escalations.services import create_escalation_for_assessment

    generate_advice_for_assessment(assessment)
    create_escalation_for_assessment(assessment)
    return assessment


def detect_stage(report):
    workflow = report.follow_up_case.workflow
    return (
        CareStage.objects.filter(
            workflow=workflow,
            start_day__lte=report.day_after_treatment,
            end_day__gte=report.day_after_treatment,
        )
        .order_by("sort_order", "start_day", "id")
        .first()
    )


def _report_with_context(report):
    if isinstance(report, SymptomReport):
        report_id = report.id
    else:
        report_id = report

    return SymptomReport.objects.select_related(
        "follow_up_case",
        "follow_up_case__patient",
        "follow_up_case__patient__user",
        "follow_up_case__workflow",
        "risk_assessment",
    ).get(id=report_id)


def _matching_rules(report, stage):
    values = _report_values(report)
    rules = SymptomRule.objects.filter(stage=stage).order_by("id")

    return [rule for rule in rules if _condition_matches(rule.condition, values)]


def _report_values(report):
    values = {
        "bad_smell": report.bad_smell,
        "bleeding": report.bleeding,
        "fever": report.fever,
        "pain_level": report.pain_level,
        "swelling": report.swelling,
    }
    if isinstance(report.symptom_values, dict):
        values.update(report.symptom_values)
    values["day_after_treatment"] = report.day_after_treatment
    return values


def _condition_matches(condition, values):
    try:
        validate_condition_shape(condition)
    except ValidationError:
        return False

    return _evaluate_group(condition, values)


def _evaluate_group(condition, values):
    if "all" in condition:
        return all(_evaluate_item(item, values) for item in condition["all"])

    if "any" in condition:
        return any(_evaluate_item(item, values) for item in condition["any"])

    return False


def _evaluate_item(item, values):
    if "all" in item or "any" in item:
        return _evaluate_group(item, values)

    field = item["field"]
    if field not in values:
        return False

    return _compare(values[field], item["operator"], item["value"])


def _compare(actual, operator, expected):
    try:
        if operator == "=":
            return actual == expected
        if operator == "!=":
            return actual != expected
        if operator == ">":
            return actual > expected
        if operator == ">=":
            return actual >= expected
        if operator == "<":
            return actual < expected
        if operator == "<=":
            return actual <= expected
        if operator == "in":
            return actual in expected
    except TypeError:
        return False

    return False


def _rule_trace(rule):
    return {
        "id": rule.id,
        "name": rule.name,
        "risk_level": rule.risk_level,
        "recommended_action": rule.recommended_action,
        "appointment_priority": rule.appointment_priority,
        "explanation": rule.explanation,
    }
