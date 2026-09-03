import math
import re
from urllib.parse import urlparse

_PRIVATE_FIELD_PARTS = frozenset({"authorization", "credential", "password", "passwd", "secret", "token"})


def is_serializable_metadata_value(value):
    if isinstance(value, dict):
        return all(isinstance(key, str) and is_serializable_metadata_value(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(is_serializable_metadata_value(item) for item in value)
    if isinstance(value, float):
        return math.isfinite(value)
    return isinstance(value, (str, int, bool)) or value is None


def is_publishable_metadata_value(value):
    if not is_serializable_metadata_value(value):
        return False
    if isinstance(value, dict):
        return all(is_publishable_metadata_field(key, item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return all(is_publishable_metadata_value(item) for item in value)
    if not isinstance(value, str):
        return True
    value = value.strip().strip('"')
    if re.search(r"(?:^|[\s=\"'])(?:/[^/]|file://|\\\\|[A-Za-z]:[\\/])", value, re.IGNORECASE):
        return False
    for url in re.findall(r"(?:https?|ftp)://[^\s\"'<>]+", value, re.IGNORECASE):
        try:
            parsed = urlparse(url)
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                return False
        except ValueError:
            return False
    return True


def is_publishable_metadata_field(name, value):
    if not isinstance(name, str):
        return False
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized.lower()).strip("_")
    if any(part in normalized.split("_") for part in _PRIVATE_FIELD_PARTS):
        return False
    if any(part in normalized for part in ("api_key", "apikey", "private_key", "privatekey")):
        return False
    return is_publishable_metadata_value(value)
