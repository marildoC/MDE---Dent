import json

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from accounts.models import UserRole
from audit import actions as audit_actions
from audit.services import record_audit
from decision_engine.serializers import RiskAssessmentSerializer
from patients.lifecycle import validate_reportable_case
from patients.serializers import FollowUpCaseSerializer
from workflows.models import SymptomDataType

from .models import SymptomIntensity, SymptomReport


LEGACY_SYMPTOM_DEFAULTS = {
    "pain_level": 0,
    "swelling": SymptomIntensity.NONE,
    "bleeding": SymptomIntensity.NONE,
    "fever": False,
    "bad_smell": False,
}
LEGACY_BOOLEAN_FIELDS = {"fever", "bad_smell"}
LEGACY_INTENSITY_FIELDS = {"swelling", "bleeding"}
LEGACY_INTENSITY_VALUES = {choice for choice, _label in SymptomIntensity.choices}


class SymptomReportSerializer(serializers.ModelSerializer):
    follow_up_case_detail = FollowUpCaseSerializer(source="follow_up_case", read_only=True)
    risk_assessment = RiskAssessmentSerializer(read_only=True)
    submitted_by_username = serializers.CharField(source="submitted_by.username", read_only=True)

    class Meta:
        model = SymptomReport
        fields = (
            "id",
            "follow_up_case",
            "follow_up_case_detail",
            "risk_assessment",
            "submitted_by",
            "submitted_by_username",
            "day_after_treatment",
            "pain_level",
            "swelling",
            "bleeding",
            "fever",
            "bad_smell",
            "symptom_values",
            "notes",
            "image",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "follow_up_case_detail",
            "risk_assessment",
            "submitted_by",
            "submitted_by_username",
            "day_after_treatment",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {
            "pain_level": {"required": False},
            "swelling": {"required": False},
            "bleeding": {"required": False},
            "fever": {"required": False},
            "bad_smell": {"required": False},
            "symptom_values": {"required": False},
        }

    def validate_follow_up_case(self, follow_up_case):
        request = self.context.get("request")
        user = request.user if request else None

        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Authentication is required.")

        if user.role != UserRole.PATIENT:
            raise serializers.ValidationError("Only patients can submit symptom reports.")

        if follow_up_case.patient.user_id != user.id:
            raise serializers.ValidationError("Report must belong to your own follow-up case.")

        try:
            validate_reportable_case(follow_up_case)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message) from exc

        return follow_up_case

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None

        if self.instance is None and user and user.role != UserRole.PATIENT:
            raise serializers.ValidationError("Only patients can submit symptom reports.")

        if self.instance is None:
            symptom_values = self._validated_symptom_values(attrs)
            attrs["symptom_values"] = symptom_values
            self._apply_legacy_field_values(attrs, symptom_values)

        return attrs

    def _validated_symptom_values(self, attrs):
        follow_up_case = attrs.get("follow_up_case")
        provided_values = _as_symptom_value_dict(attrs.get("symptom_values", {}))
        definitions = list(
            follow_up_case.workflow.symptom_definitions.all().order_by("key")
        )

        if not definitions:
            return _normalize_legacy_symptom_values(provided_values)

        definition_keys = {definition.key for definition in definitions}
        unknown_keys = sorted(set(provided_values) - definition_keys)
        if unknown_keys:
            raise serializers.ValidationError(
                {
                    "symptom_values": {
                        key: "This symptom is not defined by the assigned workflow."
                        for key in unknown_keys
                    }
                }
            )

        normalized = {}
        errors = {}
        for definition in definitions:
            has_value = definition.key in provided_values
            value = provided_values.get(definition.key)

            if not has_value and definition.key in attrs:
                has_value = True
                value = attrs[definition.key]

            if _is_blank(value):
                if definition.is_required:
                    errors[definition.key] = "This symptom value is required."
                continue

            try:
                normalized[definition.key] = _normalize_symptom_value(definition, value)
            except serializers.ValidationError as exc:
                errors[definition.key] = exc.detail

        if errors:
            raise serializers.ValidationError({"symptom_values": errors})

        return normalized

    def _apply_legacy_field_values(self, attrs, symptom_values):
        for field_name, default_value in LEGACY_SYMPTOM_DEFAULTS.items():
            attrs.setdefault(field_name, default_value)

        for field_name, value in symptom_values.items():
            fixed_value = _legacy_fixed_value(field_name, value)
            if fixed_value is not None:
                attrs[field_name] = fixed_value

    def create(self, validated_data):
        from decision_engine.services import assess_report

        request = self.context["request"]
        report = SymptomReport.objects.create(submitted_by=request.user, **validated_data)
        record_audit(
            request.user,
            audit_actions.SYMPTOM_REPORT_SUBMITTED,
            report,
            {
                "follow_up_case_id": report.follow_up_case_id,
                "patient_id": report.follow_up_case.patient_id,
                "day_after_treatment": report.day_after_treatment,
                "report_id": report.id,
            },
        )
        assess_report(report)
        return report


def _as_symptom_value_dict(value):
    if value in (None, ""):
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise serializers.ValidationError(
                {"symptom_values": "Symptom values must be valid JSON."}
            ) from exc
    if not isinstance(value, dict):
        raise serializers.ValidationError({"symptom_values": "Symptom values must be an object."})
    return value


def _is_blank(value):
    return value is None or value == ""


def _normalize_symptom_value(definition, value):
    if definition.data_type == SymptomDataType.INTEGER:
        return _normalize_integer_value(definition, value)

    if definition.data_type == SymptomDataType.BOOLEAN:
        return _normalize_boolean_value(value)

    if definition.data_type == SymptomDataType.CHOICE:
        return _normalize_choice_value(definition, value)

    if definition.data_type == SymptomDataType.TEXT:
        return str(value)

    raise serializers.ValidationError("Unsupported symptom data type.")


def _normalize_integer_value(definition, value):
    if isinstance(value, bool):
        raise serializers.ValidationError("Integer symptoms must be numeric.")

    if isinstance(value, int):
        integer_value = value
    elif isinstance(value, float) and value.is_integer():
        integer_value = int(value)
    elif isinstance(value, str):
        stripped = value.strip()
        try:
            integer_value = int(stripped)
        except ValueError:
            try:
                float_value = float(stripped)
            except ValueError as exc:
                raise serializers.ValidationError(
                    "Integer symptoms must be numeric."
                ) from exc
            if not float_value.is_integer():
                raise serializers.ValidationError("Integer symptoms must be whole numbers.")
            integer_value = int(float_value)
    else:
        raise serializers.ValidationError("Integer symptoms must be numeric.")

    if definition.min_value is not None and integer_value < definition.min_value:
        raise serializers.ValidationError(
            f"Value must be greater than or equal to {definition.min_value}."
        )
    if definition.max_value is not None and integer_value > definition.max_value:
        raise serializers.ValidationError(
            f"Value must be less than or equal to {definition.max_value}."
        )

    return integer_value


def _normalize_boolean_value(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off"}:
            return False
    raise serializers.ValidationError("Boolean symptoms must be true or false.")


def _normalize_choice_value(definition, value):
    normalized = str(value)
    allowed_values = definition.allowed_values or []
    if allowed_values:
        allowed_strings = [str(item) for item in allowed_values]
        if normalized not in allowed_strings:
            raise serializers.ValidationError(
                "Choice value must be one of the workflow allowed values."
            )
    return normalized


def _normalize_legacy_symptom_values(provided_values):
    if not provided_values:
        return {}

    unknown_keys = sorted(set(provided_values) - set(LEGACY_SYMPTOM_DEFAULTS))
    if unknown_keys:
        raise serializers.ValidationError(
            {
                "symptom_values": {
                    key: "This symptom is not defined by the assigned workflow."
                    for key in unknown_keys
                }
            }
        )

    normalized = {}
    errors = {}
    for key, value in provided_values.items():
        try:
            if key == "pain_level":
                value = _normalize_legacy_pain_level(value)
            elif key in LEGACY_INTENSITY_FIELDS:
                value = _normalize_legacy_intensity(value)
            elif key in LEGACY_BOOLEAN_FIELDS:
                value = _normalize_boolean_value(value)
        except serializers.ValidationError as exc:
            errors[key] = exc.detail
            continue
        normalized[key] = value

    if errors:
        raise serializers.ValidationError({"symptom_values": errors})

    return normalized


def _normalize_legacy_pain_level(value):
    integer_value = _normalize_integer_value(
        type(
            "LegacyPainDefinition",
            (),
            {"min_value": 0, "max_value": 10},
        )(),
        value,
    )
    return integer_value


def _normalize_legacy_intensity(value):
    normalized = str(value)
    if normalized not in LEGACY_INTENSITY_VALUES:
        raise serializers.ValidationError("Value must be NONE, MILD, or SEVERE.")
    return normalized


def _legacy_fixed_value(field_name, value):
    if field_name == "pain_level":
        if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 10:
            return value
        return None

    if field_name in LEGACY_INTENSITY_FIELDS:
        normalized = str(value)
        if normalized in LEGACY_INTENSITY_VALUES:
            return normalized
        return None

    if field_name in LEGACY_BOOLEAN_FIELDS and isinstance(value, bool):
        return value

    return None
