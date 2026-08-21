from datetime import (
    datetime,
    timezone,
)
from typing import (
    Any,
    Optional,
    TYPE_CHECKING,
)

from galaxy.authnz.psa_authnz import locate_token_expiration
from galaxy.files.sources.util import get_drs_object
from galaxy.files.uris import ensure_file_sources
from galaxy.model import User
from galaxy.schema.drs import ContentsObject

if TYPE_CHECKING:
    from galaxy.tools.data_fetch import UploadConfig


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


def drs_bundle_to_items(upload_config: "UploadConfig", target: dict[str, Any]) -> list[dict[str, Any]]:
    drs_uri = target["url"]
    file_sources = ensure_file_sources(upload_config.file_sources)
    file_source_path = file_sources.get_file_source_path(drs_uri)
    file_source = file_source_path.file_source

    if file_source.plugin_type != "drs":
        raise Exception(f"URI [{drs_uri}] did not resolve to a DRS file source")

    context = file_source._get_runtime_context(user_context=None)
    config = context.config
    headers = dict(config.http_headers or {})
    headers.update(target.get("headers") or {})
    resolved_headers = headers or None

    drs_object = get_drs_object(drs_uri, force_http=config.force_http, headers=resolved_headers)

    if not drs_object.contents:
        raise Exception(f"DRS object [{drs_uri}] is not a bundle")

    return _drs_contents_to_items(
        drs_uri,
        drs_object.contents,
        force_http=config.force_http,
        headers=resolved_headers,
    )


def _drs_contents_to_items(
    parent_uri: str,
    contents: list[ContentsObject],
    force_http: bool,
    headers: Optional[dict[str, str]],
) -> list[dict[str, Any]]:
    """
    Convert DRS bundle contents into a flat list of fetch items.
    """
    items = []

    for child in contents:
        child_uri = _drs_child_uri(parent_uri, child)
        child_object = get_drs_object(child_uri, force_http=force_http, headers=headers)
        name = child.name or child_object.name or child_object.id

        if child_object.contents:
            items.extend(
                _drs_contents_to_items(
                    child_uri,
                    child_object.contents,
                    force_http=force_http,
                    headers=headers,
                )
            )
        else:
            item: dict[str, Any] = {
                "src": "url",
                "url": child_uri,
                "name": name,
                "ext": "auto",
            }
            if headers:
                item["headers"] = headers
            items.append(item)

    return items


def _drs_child_uri(parent_uri: str, child: ContentsObject) -> str:
    if child.drs_uri:
        return child.drs_uri[0]

    if child.id:
        authority = parent_uri[len("drs://") :].split("/", 1)[0]
        return f"drs://{authority}/{child.id}"

    raise Exception(f"DRS bundle child [{child.name}] has no drs_uri or id")
