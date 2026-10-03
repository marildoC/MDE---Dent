from django.core.exceptions import ValidationError


SUPPORTED_OPERATORS = {"=", "!=", ">", ">=", "<", "<=", "in"}
LOGICAL_GROUPS = {"all", "any"}


def validate_condition_shape(condition):
    if not isinstance(condition, dict):
        raise ValidationError("Condition must be an object.")

    group_keys = [key for key in condition if key in LOGICAL_GROUPS]
    if len(group_keys) != 1 or len(condition) != 1:
        raise ValidationError("Condition must contain exactly one logical group: all or any.")

    items = condition[group_keys[0]]
    if not isinstance(items, list) or not items:
        raise ValidationError("Condition group must contain at least one item.")

    for item in items:
        if not isinstance(item, dict):
            raise ValidationError("Condition items must be objects.")

        if any(key in item for key in LOGICAL_GROUPS):
            validate_condition_shape(item)
            continue

        missing = {"field", "operator", "value"} - set(item)
        if missing:
            raise ValidationError("Condition leaf items require field, operator, and value.")

        if item["operator"] not in SUPPORTED_OPERATORS:
            raise ValidationError(f"Unsupported operator: {item['operator']}.")

        if not isinstance(item["field"], str) or not item["field"]:
            raise ValidationError("Condition field must be a non-empty string.")
