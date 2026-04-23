from datetime import datetime
from typing import Any

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


def staged_fetch_token_expiration(user: User | None, request: dict[str, Any], file_sources, user_context) -> datetime | None:
    if user is None or not user.social_auth:
        return None
    uses_authorization_header = False
    for url in iter_fetch_urls(request):
        file_source_path = file_sources.get_file_source_path(url)
        serialized = file_source_path.file_source.to_dict(for_serialization=True, user_context=user_context)
        http_headers = serialized.get("http_headers") or {}
        if http_headers.get("Authorization"):
            uses_authorization_header = True
            break
    if not uses_authorization_header:
        return None
    expiration_times = [auth.expiration_time for auth in user.social_auth if auth.expiration_time is not None]
    return min(expiration_times) if expiration_times else None
