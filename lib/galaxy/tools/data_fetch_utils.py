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


def staged_fetch_token_expiration(
    user: User | None, request: dict[str, Any], file_sources, user_context
) -> datetime | None:
    if user is None or not user.social_auth:
        return None
    if not fetch_uses_authorization_header(request, file_sources, user_context):
        return None
    expiration_times = []
    for auth in user.social_auth:
        extra_data = auth.extra_data or {}
        auth_time = extra_data.get("auth_time")
        expires = locate_token_expiration(extra_data)
        if auth_time is None or expires is None:
            continue
        expiration_times.append(datetime.fromtimestamp(int(auth_time) + int(expires), tz=timezone.utc))
    return min(expiration_times) if expiration_times else None
