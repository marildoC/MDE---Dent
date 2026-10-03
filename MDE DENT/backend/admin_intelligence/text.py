import re


def normalize(value):
    normalized = value.lower()
    normalized = normalized.replace("\u2019", "'").replace("\u2018", "'")
    normalized = normalized.replace("\u201c", '"').replace("\u201d", '"')
    normalized = normalized.replace("follow-up", "follow up")
    normalized = normalized.replace("post-extraction", "post extraction")
    normalized = normalized.replace("appointment-required", "appointment required")
    normalized = normalized.replace("waiting-for-patient", "waiting for patient")
    normalized = re.sub(r"[^a-z0-9_#'\s-]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized
