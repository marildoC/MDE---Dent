from .models import AuditLog


SENSITIVE_DETAIL_KEYS = {
    "advice",
    "allergies",
    "dental_notes",
    "emergency_contact",
    "image",
    "message",
    "notes",
    "required_disclaimer",
    "response",
    "staff_response",
}


def record_audit(actor, action, target, details=None):
    target_type = target.__class__.__name__
    target_id = str(target.pk)
    target_repr = str(target)[:255]

    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", True) else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_repr=target_repr,
        details=_sanitize_details(details or {}),
    )


def _sanitize_details(value):
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if key in SENSITIVE_DETAIL_KEYS:
                continue
            sanitized[key] = _sanitize_details(item)
        return sanitized

    if isinstance(value, (list, tuple)):
        return [_sanitize_details(item) for item in value]

    return value
