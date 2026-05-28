import re
from dataclasses import dataclass

from django.core.exceptions import ValidationError


@dataclass(frozen=True)
class RecommendationViolation:
    field_name: str
    rule_name: str
    matched_text: str
    stage_label: str

    @property
    def message(self):
        return (
            "This patient-facing recommendation cannot be saved because it violates "
            f"global dental safety rules for {self.stage_label}: "
            f"'{self.matched_text}' is not allowed."
        )


MEDICINE_TERMS = (
    "antibiotic",
    "antibiotik",
    "amoxicillin",
    "exolin",
    "metronidazole",
)

GLOBAL_PATTERNS = (
    (
        "medicine_recommendation",
        re.compile(
            r"\b(take|start|use|continue|prescribe|recommend)\b.{0,60}"
            r"\b(antibiotic|antibiotik|amoxicillin|exolin|metronidazole)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "medicine_dosage",
        re.compile(
            r"\b(antibiotic|antibiotik|amoxicillin|exolin|metronidazole)\b"
            r".{0,40}(\b\d+\s*(mg|ml|days?)\b|\d+\s*%)",
            re.IGNORECASE,
        ),
    ),
)

STAGE_RULES = (
    {
        "name": "early_recovery_medicine_restriction",
        "label": "early recovery stages",
        "start_day": 0,
        "end_day": 3,
        "terms": ("exolin", "amoxicillin", "antibiotic", "antibiotik"),
    },
    {
        "name": "intermediate_recovery_medicine_restriction",
        "label": "intermediate recovery stages",
        "start_day": 4,
        "end_day": 7,
        "terms": ("exolin", "metronidazole", "antibiotic", "antibiotik"),
    },
    {
        "name": "late_recovery_medicine_restriction",
        "label": "late recovery stages",
        "start_day": 8,
        "end_day": None,
        "terms": ("exolin", "antibiotic", "antibiotik"),
    },
)


def validate_patient_recommendation_text(text, *, stage=None, field_name="text"):
    violation = find_patient_recommendation_violation(
        text,
        stage=stage,
        field_name=field_name,
    )
    if violation:
        raise ValidationError({field_name: violation.message})


def find_patient_recommendation_violation(text, *, stage=None, field_name="text"):
    normalized = (text or "").strip()
    if not normalized:
        return None

    for rule_name, pattern in GLOBAL_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return RecommendationViolation(
                field_name=field_name,
                rule_name=rule_name,
                matched_text=_matched_term(match.group(0)),
                stage_label=_stage_label(stage),
            )

    for rule in _matching_stage_rules(stage):
        term = _first_term_match(normalized, rule["terms"])
        if term:
            return RecommendationViolation(
                field_name=field_name,
                rule_name=rule["name"],
                matched_text=term,
                stage_label=_stage_label(stage, fallback=rule["label"]),
            )

    return None


def _matching_stage_rules(stage):
    if not stage:
        return ()

    matches = []
    for rule in STAGE_RULES:
        if _ranges_overlap(
            stage.start_day,
            stage.end_day,
            rule["start_day"],
            rule["end_day"],
        ):
            matches.append(rule)
    return matches


def _ranges_overlap(left_start, left_end, right_start, right_end):
    right_end = right_end if right_end is not None else left_end
    return left_start <= right_end and right_start <= left_end


def _first_term_match(text, terms):
    for term in terms:
        match = re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE)
        if match:
            return match.group(0)
    return ""


def _matched_term(text):
    medicine = _first_term_match(text, MEDICINE_TERMS)
    return medicine or text.strip()


def _stage_label(stage, fallback="the selected care stage"):
    if not stage:
        return fallback
    return f"{stage.name} (days {stage.start_day}-{stage.end_day})"
