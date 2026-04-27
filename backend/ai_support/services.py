from audit import actions as audit_actions
from audit.services import record_audit
from workflows.models import AIAdviceBoundary, RiskLevel

from .models import AdviceMessage, AdviceMessageType


UNSAFE_TERMS = {
    "antibiotic",
    "diagnosis",
    "diagnose",
    "medication",
    "medicine",
    "prescription",
    "prescribe",
}

TEMPLATES = {
    RiskLevel.LOW: (
        AdviceMessageType.LOW_RISK_AFTERCARE,
        "Your reported symptoms fit the expected monitoring range for this follow-up stage. "
        "Continue monitoring your symptoms and follow the aftercare instructions from your clinic.",
    ),
    RiskLevel.WARNING: (
        AdviceMessageType.WARNING_MONITORING,
        "Your symptoms should be monitored carefully. If they worsen, continue, or you feel "
        "uncertain, contact the clinic for guidance.",
    ),
    RiskLevel.HIGH: (
        AdviceMessageType.HIGH_STAFF_REVIEW,
        "Your report requires dental staff review. The clinic should review this case before "
        "further guidance is given.",
    ),
    RiskLevel.URGENT: (
        AdviceMessageType.URGENT_ATTENTION,
        "Your report indicates symptoms that may require urgent dental attention. Contact the "
        "clinic promptly, or follow local emergency instructions if symptoms are severe.",
    ),
}


def generate_advice_for_assessment(risk_assessment):
    try:
        return risk_assessment.advice_message
    except AdviceMessage.DoesNotExist:
        pass

    existing = AdviceMessage.objects.filter(risk_assessment=risk_assessment).first()
    if existing:
        return existing

    message_type, message = TEMPLATES[risk_assessment.risk_level]
    disclaimer = _boundary_disclaimer(risk_assessment)
    if disclaimer:
        message = f"{message} {disclaimer}"

    advice = AdviceMessage.objects.create(
        risk_assessment=risk_assessment,
        message=message,
        message_type=message_type,
    )
    record_audit(
        None,
        audit_actions.ADVICE_CREATED,
        advice,
        {
            "risk_assessment_id": risk_assessment.id,
            "message_type": advice.message_type,
            "source": "template",
        },
    )
    return advice


def _boundary_disclaimer(risk_assessment):
    workflow = risk_assessment.report.follow_up_case.workflow
    stage = risk_assessment.detected_stage
    boundary = None

    if stage:
        boundary = (
            AIAdviceBoundary.objects.filter(workflow=workflow, stage=stage)
            .order_by("id")
            .first()
        )

    if not boundary:
        boundary = (
            AIAdviceBoundary.objects.filter(workflow=workflow, stage__isnull=True)
            .order_by("id")
            .first()
        )

    if not boundary or not boundary.required_disclaimer:
        return ""

    disclaimer = boundary.required_disclaimer.strip()
    lowered = disclaimer.lower()
    if any(term in lowered for term in UNSAFE_TERMS):
        return ""

    return disclaimer
