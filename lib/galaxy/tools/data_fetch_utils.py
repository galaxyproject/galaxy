from datetime import (
    datetime,
    timezone,
)
from typing import Any

from galaxy.authnz.psa_authnz import locate_token_expiration
from galaxy.model import User


def iter_fetch_urls(value: Any):
    if isinstance(value, dict):
        if value.get("src") == "url" and "url" in value:
            yield value["url"]
        for child in value.values():
            yield from iter_fetch_urls(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_fetch_urls(child)


def fetch_uses_authorization_header(request: dict[str, Any], file_sources, user_context) -> bool:
    for url in iter_fetch_urls(request):
        file_source_path = file_sources.get_file_source_path(url)
        serialized = file_source_path.file_source.to_dict(for_serialization=True, user_context=user_context)
        http_headers = serialized.get("http_headers") or {}
        if http_headers.get("Authorization"):
            return True
    return False


def compute_token_expiry_for_provider(user: User | None, provider: str) -> datetime | None:
    """Return the expiry for a specific OIDC provider's token, if available."""
    if user is None or not user.social_auth:
        return None
    for auth in user.social_auth:
        if auth.provider != provider:
            continue
        extra_data = auth.extra_data or {}
        auth_time = extra_data.get("auth_time")
        expires = locate_token_expiration(extra_data)
        if auth_time is None or expires is None:
            return None
        return datetime.fromtimestamp(int(auth_time) + int(expires), tz=timezone.utc)
    return None
