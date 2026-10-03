from .validators import SUPPORTED_OPERATORS


UNSUPPORTED_CONDITION_TEXT = "Unsupported condition structure"


def format_condition(condition):
    if not isinstance(condition, dict):
        return UNSUPPORTED_CONDITION_TEXT

    if _is_leaf(condition):
        return _format_leaf(condition)

    if set(condition.keys()) == {"all"}:
        return _format_condition_group(condition["all"], "AND")

    if set(condition.keys()) == {"any"}:
        return _format_condition_group(condition["any"], "OR")

    return UNSUPPORTED_CONDITION_TEXT


def _format_condition_group(items, operator):
    if not isinstance(items, list) or not items:
        return UNSUPPORTED_CONDITION_TEXT

    formatted_items = []
    for item in items:
        if not isinstance(item, dict):
            return UNSUPPORTED_CONDITION_TEXT

        if _is_leaf(item):
            formatted_items.append(_format_leaf(item))
            continue

        formatted = format_condition(item)
        if formatted == UNSUPPORTED_CONDITION_TEXT:
            return formatted
        formatted_items.append(f"({formatted})")

    return f" {operator} ".join(formatted_items)


def _is_leaf(condition):
    return set(condition.keys()) == {"field", "operator", "value"}


def _format_leaf(condition):
    field = condition["field"]
    operator = condition["operator"]
    if (
        not isinstance(field, str)
        or not field
        or not isinstance(operator, str)
        or operator not in SUPPORTED_OPERATORS
    ):
        return UNSUPPORTED_CONDITION_TEXT
    return f"{field} {operator} {_format_condition_value(condition['value'])}"


def _format_condition_value(value):
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "[" + ", ".join(_format_condition_value(item) for item in value) + "]"
    if value is None:
        return "null"
    return str(value)
