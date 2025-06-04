import json
import logging
import time
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
)
from urllib.parse import quote

from galaxy import exceptions
from galaxy.files import (
    ConfiguredFileSources,
    FileSourcesUserContext,
)
from galaxy.files.models import (
    FilesSourceOptions,
    PartialFilesSourceProperties,
)
from galaxy.files.uris import stream_url_to_file
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    requests,
)
from galaxy.util.config_parsers import IpAllowedListEntryT
from galaxy.util.path import StrPath

log = logging.getLogger(__name__)


def _not_implemented(drs_uri: str, desc: str) -> NotImplementedError:
    missing_client_func = f"Galaxy client cannot currently fetch URIs {desc}."
    header = f"Missing client functionality required to fetch DRS URI {drs_uri}."
    rest_of_message = """Currently Galaxy client only works with HTTP/HTTPS targets but extensions for
    other types would be gladly welcomed by the Galaxy team. Please
    report use cases not covered by this function to our issue tracker
    at https://github.com/galaxyproject/galaxy/issues/new.
    """
    return NotImplementedError(f"{header} {missing_client_func} {rest_of_message}")


class RetryOptions:
    retry_times: int = 5
    override_retry_after: Optional[float] = None


def retry_and_get(get_url: str, retry_options: RetryOptions, headers: Optional[dict] = None) -> requests.Response:
    response = requests.get(get_url, timeout=DEFAULT_SOCKET_TIMEOUT, headers=headers)
    response.raise_for_status()
    if response.status_code == 202:
        if retry_options.retry_times == 0:
            raise Exception("Timeout waiting on DRS URI response")
        if "Retry-After" not in response.headers:
            raise ValueError("Remote DRS URI response invalid (Retry-After must be specified for 202 statuses)")
        retry_after = retry_options.override_retry_after or float(response.headers["Retry-After"])
        time.sleep(retry_after)
        retry_options.retry_times -= 1
        return retry_and_get(get_url, retry_options)
    else:
        return response


def _get_access_info(obj_url: str, access_method: dict, headers=None) -> tuple[str, dict]:
    try:
        access_url = access_method["access_url"]
    except KeyError:
        access_id = access_method["access_id"]
        access_get_url = f"{obj_url}/access/{access_id}"
        access_response = requests.get(access_get_url, timeout=DEFAULT_SOCKET_TIMEOUT, headers=headers)
        access_response.raise_for_status()
        access_response_object = access_response.json()
        access_url = access_response_object

    url = access_url["url"]
    headers_list = access_url.get("headers") or []
    headers_as_dict = {}
    for header_str in headers_list:
        key, value = header_str.split(": ", 1)
        headers_as_dict[key] = value

    return url, headers_as_dict


class CompactIdentifierResolver:
    _instance: Optional["CompactIdentifierResolver"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, cache_ttl: int = 86400):
        if not hasattr(self, "_cache"):
            self._cache: Dict[str, Dict] = {}
            self._cache_ttl = cache_ttl

    @classmethod
    def _reset_singleton(cls):
        """Reset the singleton instance - for testing only."""
        cls._instance = None

    def _is_cached(self, prefix: str) -> bool:
        if prefix not in self._cache:
            return False
        cached_time = self._cache[prefix].get("timestamp", 0)
        return (time.time() - cached_time) < self._cache_ttl

    def _cache_result(self, prefix: str, url_pattern: str):
        self._cache[prefix] = {"url_pattern": url_pattern, "timestamp": time.time()}

    def _query_identifiers_org(self, prefix: str) -> Optional[str]:
        try:
            namespace_url = (
                f"https://registry.api.identifiers.org/restApi/namespaces/search/findByPrefix?prefix={prefix}"
            )
            response = requests.get(namespace_url, timeout=DEFAULT_SOCKET_TIMEOUT)
            response.raise_for_status()

            namespace_data = response.json()
            if not namespace_data or "_links" not in namespace_data:
                return None

            if "resources" in namespace_data["_links"]:
                resources_url = namespace_data["_links"]["resources"]["href"]
            else:
                return None
            response = requests.get(resources_url, timeout=DEFAULT_SOCKET_TIMEOUT)
            response.raise_for_status()

            resources = response.json()
            if "_embedded" in resources and "resources" in resources["_embedded"]:
                official_resource = None
                fallback_resource = None

                for resource in resources["_embedded"]["resources"]:
                    if "urlPattern" in resource:
                        if resource.get("official", False):
                            official_resource = resource
                            break
                        elif fallback_resource is None:
                            fallback_resource = resource

                best_resource = official_resource or fallback_resource
                if best_resource:
                    return best_resource["urlPattern"]

        except requests.exceptions.RequestException as e:
            log.warning(f"Failed to query identifiers.org for prefix {prefix}: {e}")
        except (KeyError, json.JSONDecodeError) as e:
            log.warning(f"Invalid response from identifiers.org for prefix {prefix}: {e}")

        return None

    def resolve_prefix(self, prefix: str) -> Optional[str]:
        if self._is_cached(prefix):
            return self._cache[prefix]["url_pattern"]

        url_pattern = self._query_identifiers_org(prefix)

        if url_pattern:
            self._cache_result(prefix, url_pattern)
            log.info(f"Resolved DRS prefix '{prefix}' to URL pattern: {url_pattern}")
        else:
            log.warning(f"Could not resolve DRS prefix '{prefix}' via identifiers.org")

        return url_pattern


def parse_compact_identifier(drs_uri: str) -> Tuple[str, str]:
    if not drs_uri.startswith("drs://"):
        raise ValueError(f"Not a valid DRS URI: {drs_uri}")

    rest_of_uri = drs_uri[len("drs://") :]

    colon_idx = rest_of_uri.find(":")
    if colon_idx == -1:
        raise ValueError(f"Invalid compact identifier format (missing colon): {drs_uri}")

    prefix = rest_of_uri[:colon_idx]
    accession = rest_of_uri[colon_idx + 1 :]

    if not all(c.islower() or c.isdigit() or c in "._" for c in prefix):
        raise ValueError(
            f"Invalid prefix format '{prefix}': must contain only lowercase letters, numbers, dots, and underscores"
        )

    if not prefix or not accession:
        raise ValueError(f"Empty prefix or accession in compact identifier: {drs_uri}")

    return prefix, accession


def resolve_compact_identifier_to_url(drs_uri: str, resolver: Optional[CompactIdentifierResolver] = None) -> str:
    prefix, accession = parse_compact_identifier(drs_uri)

    if resolver is None:
        resolver = CompactIdentifierResolver()

    url_pattern = resolver.resolve_prefix(prefix)
    if not url_pattern:
        raise ValueError(f"Could not resolve prefix '{prefix}' via identifiers.org")

    encoded_accession = quote(accession, safe="")
    resolved_url = url_pattern.replace("{$id}", encoded_accession)

    if not resolved_url.startswith(("http://", "https://")):
        raise ValueError(f"Resolved URL is not HTTP(S): {resolved_url}")

    return resolved_url


def fetch_drs_to_file(
    drs_uri: str,
    target_path: StrPath,
    user_context: Optional[FileSourcesUserContext],
    force_http=False,
    retry_options: Optional[RetryOptions] = None,
    headers: Optional[dict] = None,
    fetch_url_allowlist: Optional[list[IpAllowedListEntryT]] = None,
):
    """Fetch contents of drs:// URI to a target path."""
    if not drs_uri.startswith("drs://"):
        raise ValueError(f"Unknown scheme for drs_uri {drs_uri}")

    rest_of_drs_uri = drs_uri[len("drs://") :]

    if "/" not in rest_of_drs_uri and ":" in rest_of_drs_uri:
        try:
            get_url = resolve_compact_identifier_to_url(drs_uri)
            log.info(f"Resolved compact identifier DRS URI {drs_uri} to {get_url}")
        except ValueError as e:
            raise ValueError(f"Failed to resolve compact identifier DRS URI {drs_uri}: {str(e)}")
    elif "/" in rest_of_drs_uri:
        netspec, object_id = rest_of_drs_uri.split("/", 1)
        scheme = "https"
        if force_http:
            scheme = "http"
        get_url = f"{scheme}://{netspec}/ga4gh/drs/v1/objects/{object_id}"
    else:
        raise ValueError(f"Invalid DRS URI format: {drs_uri}")
    response = retry_and_get(get_url, retry_options or RetryOptions(), headers=headers)
    response.raise_for_status()
    response_object = response.json()
    access_methods = response_object.get("access_methods", [])
    if len(access_methods) == 0:
        raise ValueError(f"No access methods found in DRS response for {drs_uri}")

    downloaded = False
    for access_method in access_methods:
        access_url, access_headers = _get_access_info(get_url, access_method, headers=headers)
        opts = FilesSourceOptions()
        if access_method["type"] == "https":
            extra_props = {
                "http_headers": access_headers or {},
                "fetch_url_allowlist": fetch_url_allowlist or [],
            }
            opts.extra_props = PartialFilesSourceProperties(**extra_props)

        try:
            file_sources = (
                user_context.file_sources
                if user_context
                else ConfiguredFileSources.from_dict(None, load_stock_plugins=True)
            )
            stream_url_to_file(
                access_url,
                target_path=str(target_path),
                file_sources=file_sources,
                user_context=user_context,
                file_source_opts=opts,
            )
            downloaded = True
            break
        except exceptions.RequestParameterInvalidException:
            continue

    if not downloaded:
        unimplemented_access_types = [m["type"] for m in access_methods]
        raise _not_implemented(drs_uri, f"that are fetched via unimplemented types ({unimplemented_access_types})")
