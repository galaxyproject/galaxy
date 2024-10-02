import time
from typing import (
    List,
    Optional,
    Tuple,
)

from galaxy import exceptions
from galaxy.files import (
    ConfiguredFileSources,
    FileSourcesUserContext,
)
from galaxy.files.sources import FilesSourceOptions
from galaxy.files.sources.http import HTTPFilesSourceProperties
from galaxy.files.uris import stream_url_to_file
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    requests,
)
from galaxy.util.config_parsers import IpAllowedListEntryT
from galaxy.util.path import StrPath


def _not_implemented(drs_uri: str, desc: str) -> NotImplementedError:
    missing_client_func = f"Galaxy client cannot currently fetch URIs {desc}."
    header = f"Missing client functionaltiy required to fetch DRS URI {drs_uri}."
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


def _get_access_info(obj_url: str, access_method: dict, headers=None) -> Tuple[str, dict]:
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


def fetch_drs_to_file(
    drs_uri: str,
    target_path: StrPath,
    user_context: Optional[FileSourcesUserContext],
    force_http=False,
    retry_options: Optional[RetryOptions] = None,
    headers: Optional[dict] = None,
    fetch_url_allowlist: Optional[List[IpAllowedListEntryT]] = None,
):
    """Fetch contents of drs:// URI to a target path."""
    if not drs_uri.startswith("drs://"):
        raise ValueError(f"Unknown scheme for drs_uri {drs_uri}")
    rest_of_drs_uri = drs_uri[len("drs://") :]
    if "/" not in rest_of_drs_uri:
        # DRS URI uses compact identifiers, not yet implemented.
        # https://ga4gh.github.io/data-repository-service-schemas/preview/release/drs-1.2.0/docs/more-background-on-compact-identifiers.html
        raise _not_implemented(drs_uri, "that use compact identifiers")
    netspec, object_id = rest_of_drs_uri.split("/", 1)
    scheme = "https"
    if force_http:
        scheme = "http"
    get_url = f"{scheme}://{netspec}/ga4gh/drs/v1/objects/{object_id}"
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
            extra_props: HTTPFilesSourceProperties = {
                "http_headers": access_headers or {},
                "fetch_url_allowlist": fetch_url_allowlist or [],
            }
            opts.extra_props = extra_props
        else:
            opts.extra_props = {}
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
        raise _not_implemented(drs_uri, f"that is fetched via unimplemented types ({unimplemented_access_types})")
