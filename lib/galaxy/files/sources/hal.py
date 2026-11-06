"""Public, read-only access to versioned HAL deposits and their attached files."""

import logging
import re
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import TypedDict
from urllib.parse import (
    quote,
    unquote,
    urljoin,
    urlsplit,
)

from requests import (
    RequestException,
    Response,
)
from urllib3.exceptions import HTTPError

from galaxy.exceptions import (
    MessageException,
    ObjectNotFound,
)
from galaxy.files.models import (
    AnyRemoteEntry,
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
    FilesSourceRuntimeContext,
    RemoteDirectory,
    RemoteFile,
)
from galaxy.files.sources import (
    BaseFilesSource,
    DEFAULT_PAGE_LIMIT,
)
from galaxy.files.uris import validate_non_local
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    requests,
    stream_to_path,
)
from galaxy.util.config_templates import TemplateExpansion

DEFAULT_API_URL = "https://api.hal.science/search/"
# Redirects versioned file URLs to the portal that hosts the deposit.
HAL_URL = "https://hal.science"
RECORD_RE = re.compile(r"([a-z][a-z0-9-]*[-_][0-9]+)v([1-9][0-9]*)")
FIELDS = "halId_s,version_i,title_s,files_s,fileAnnexes_s"
SIZE_LOOKUP_TIMEOUT = 5
MAX_SIZE_LOOKUP_WORKERS = 4

log = logging.getLogger(__name__)


class HALRecord(TypedDict, total=False):
    halId_s: str
    version_i: int
    title_s: list[str]
    files_s: list[str]
    fileAnnexes_s: list[str]


class HALSearchResult(TypedDict):
    docs: list[HALRecord]
    numFound: int


class HALFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    api_url: str | TemplateExpansion = DEFAULT_API_URL


class HALFileSourceConfiguration(BaseFileSourceConfiguration):
    api_url: str = DEFAULT_API_URL


class HALFilesSource(BaseFilesSource[HALFileSourceTemplateConfiguration, HALFileSourceConfiguration]):
    plugin_type = "hal"
    supports_pagination = True
    supports_search = True
    supports_recursive = True
    template_config_class = HALFileSourceTemplateConfiguration
    resolved_config_class = HALFileSourceConfiguration

    def __init__(self, template_config: HALFileSourceTemplateConfiguration):
        template_config = self._apply_defaults_to_template(
            dict(id="hal", label="HAL", doc="Public HAL publications and supplementary files", writable=False),
            template_config,
        )
        if template_config.writable:
            raise ValueError("HAL file sources are read-only.")
        super().__init__(template_config)

    def _list(
        self,
        context: FilesSourceRuntimeContext[HALFileSourceConfiguration],
        path: str = "/",
        recursive: bool = False,
        write_intent: bool = False,
        limit: int | None = None,
        offset: int | None = None,
        query: str | None = None,
        sort_by: str | None = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        if write_intent:
            raise MessageException("HAL file sources are read-only and do not support exporting files.")
        if path in ("", "/"):
            if recursive:
                raise MessageException(
                    "Recursive listing is not supported at the HAL root; select individual deposits."
                )
            result = self._search(
                context.config,
                q=(query or "").strip() or "*:*",
                fq="fileType_s:(file OR annex)",
                rows=limit if limit is not None else DEFAULT_PAGE_LIMIT,
                start=offset or 0,
                sort="score desc,docid asc",
            )
            entries: list[AnyRemoteEntry] = []
            for record in result["docs"]:
                record_id = self._record_id(record)
                titles = record.get("title_s") or []
                title = titles[0] if titles else record_id
                record_path = f"/{record_id}"
                entries.append(
                    RemoteDirectory(
                        name=f"{title} ({record_id})", path=record_path, uri=self.uri_from_path(record_path)
                    )
                )
            return entries, result["numFound"]

        record_id, filename = self._split_path(path)
        if filename is not None:
            raise ObjectNotFound(f"HAL path is not a directory: {path}")
        record = self._current_record(record_id, context.config)
        if self._record_id(record) != record_id:
            raise MessageException(
                f"HAL search only exposes the current version of {record_id}; "
                f"browse {self._record_id(record)} to list its current files."
            )
        files = self._record_files(record, record_id)
        entries = [
            RemoteFile(name=name, path=file_path, uri=self.uri_from_path(file_path))
            for file_path, (name, _) in files.items()
            if recursive or not query or query.casefold() in name.casefold()
        ]
        if recursive:
            # Deposits are flat: return every attachment without pagination or metadata requests.
            return entries, len(entries)
        start = offset or 0
        page = entries[start : start + limit if limit is not None else None]
        if page and limit is not None:
            # Only probe a requested page, with bounded concurrency so a large record remains responsive.
            with ThreadPoolExecutor(max_workers=MAX_SIZE_LOOKUP_WORKERS) as executor:
                metadata = executor.map(
                    self._file_metadata, [entry.name for entry in page], [files[entry.path][1] for entry in page]
                )
                for entry, (size, ctime) in zip(page, metadata):
                    if isinstance(entry, RemoteFile):
                        entry.size = size
                        entry.ctime = ctime
        return page, len(entries)

    def _file_metadata(self, name: str, url: str) -> tuple[int, datetime | None]:
        """Best-effort size and modification time; never download a body to calculate a file's size."""
        try:
            with self._open_url(url, method="HEAD", timeout=SIZE_LOOKUP_TIMEOUT, allow_html=_is_html(name)) as response:
                if response.status_code != 200:
                    return 0, None
                size = 0
                length = response.headers.get("Content-Length", "")
                # Content-Length describes the encoded representation if the server ignores identity.
                if response.headers.get("Content-Encoding", "identity") == "identity" and re.fullmatch(
                    r"[0-9]+", length
                ):
                    size = int(length)
                return size, _parse_http_date(response.headers.get("Last-Modified"))
        except MessageException:
            log.debug("Could not retrieve HAL file metadata for %s", url, exc_info=True)
            return 0, None

    def _realize_to(
        self, source_path: str, native_path: str, context: FilesSourceRuntimeContext[HALFileSourceConfiguration]
    ) -> None:
        record_id, filename = self._split_path(source_path)
        if filename is None:
            raise ObjectNotFound(f"HAL path is not a file: {source_path}")
        record = self._current_record(record_id, context.config)
        if self._record_id(record) == record_id:
            file_path = f"/{record_id}/{filename}"
            files = self._record_files(record, record_id)
            if file_path not in files:
                raise ObjectNotFound(f"File not found in HAL deposit: {source_path}")
            name, url = files[file_path]
        else:
            # The index only holds the current version, but HAL keeps serving the files of every version.
            attachment_name = self._attachment_name(filename)
            if attachment_name is None:
                raise ObjectNotFound(f"Invalid HAL file name: {source_path}")
            name = attachment_name
            url = f"{HAL_URL}/{record_id}/file/{quote(name, safe='')}"
        with self._open_url(url, allow_html=_is_html(name)) as response:
            response.raw.decode_content = True
            stream_to_path(response.raw, native_path)

    def _write_from(
        self, target_path: str, native_path: str, context: FilesSourceRuntimeContext[HALFileSourceConfiguration]
    ) -> None:
        raise MessageException("HAL file sources are read-only and do not support exporting files.")

    def _search(self, config: HALFileSourceConfiguration, **params: str | int) -> HALSearchResult:
        with self._open_url(config.api_url, params={"wt": "json", "fl": FIELDS, **params}) as response:
            try:
                payload = response.json()
                if isinstance(payload, dict) and "error" in payload:
                    log.warning("HAL search API error: %s", payload["error"])
                    raise MessageException(
                        "HAL could not complete the search. Large page offsets may exceed its search timeout; "
                        "narrow your search and try again."
                    )
                result = payload["response"]
                if not isinstance(result["docs"], list) or not isinstance(result["numFound"], int):
                    raise ValueError("Invalid search results")
                return {"docs": result["docs"], "numFound": result["numFound"]}
            except (ValueError, KeyError, TypeError) as exc:
                raise MessageException("Invalid response from the HAL search API.") from exc

    def _current_record(self, record_id: str, config: HALFileSourceConfiguration) -> HALRecord:
        """Look up the indexed deposit, which is always its current version."""
        match = RECORD_RE.fullmatch(record_id)
        assert match is not None  # checked by _split_path
        hal_id, _ = match.groups()
        result = self._search(config, q=f'halId_s:"{hal_id}"', rows=1)
        if not result["docs"]:
            raise ObjectNotFound(f"HAL deposit not found: {record_id}")
        return result["docs"][0]

    def _record_files(self, record: HALRecord, record_id: str) -> dict[str, tuple[str, str]]:
        hal_id = record.get("halId_s")
        files: dict[str, tuple[str, str]] = {}
        for url in [*record.get("files_s", []), *record.get("fileAnnexes_s", [])]:
            parsed = urlsplit(url)
            parts = parsed.path.split("/")
            # HAL portals serve deposits from many hosts, all as /<hal-id>/file/<name>. Associated datasets
            # hosted by other repositories are outside this source's scope.
            if parsed.scheme != "https" or len(parts) != 4 or parts[1] not in (hal_id, record_id) or parts[2] != "file":
                continue
            name = self._attachment_name(parts[3])
            if name is None:
                continue
            # HAL's index returns unversioned URLs; pin them before exposing or downloading the file.
            # Let HAL route the request instead of trusting the indexed attachment host.
            versioned_url = f"{HAL_URL}/{record_id}/file/{quote(name, safe='')}"
            file_path = f"/{record_id}/{quote(name, safe='')}"
            files[file_path] = (name, versioned_url)
        return dict(sorted(files.items()))

    @staticmethod
    def _attachment_name(quoted_name: str) -> str | None:
        name = unquote(quoted_name)
        if not name or name in (".", "..") or "/" in name or "\\" in name:
            return None
        return name

    @staticmethod
    def _record_id(record: HALRecord) -> str:
        record_id = f"{record.get('halId_s')}v{record.get('version_i')}"
        if not RECORD_RE.fullmatch(record_id):
            raise MessageException("HAL returned an invalid deposit identifier or version.")
        return record_id

    @staticmethod
    def _split_path(path: str) -> tuple[str, str | None]:
        parts = path.removeprefix("/").removesuffix("/").split("/")
        if not RECORD_RE.fullmatch(parts[0]) or len(parts) > 2 or (len(parts) == 2 and not parts[1]):
            raise ObjectNotFound(f"Invalid HAL path: {path}. Expected /<hal-id>v<version>[/<filename>].")
        return parts[0], parts[1] if len(parts) == 2 else None

    @contextmanager
    def _open_url(
        self,
        url: str,
        params: dict[str, str | int] | None = None,
        method: str = "GET",
        timeout: float = DEFAULT_SOCKET_TIMEOUT,
        allow_html: bool = False,
    ) -> Iterator[Response]:
        """Validate every redirect before making the next request, including metadata-supplied URLs."""
        allowlist = self._file_sources_config.fetch_url_allowlist or []
        try:
            with requests.Session() as session:
                for _ in range(6):
                    parsed = urlsplit(url)
                    if (
                        parsed.scheme not in ("http", "https")
                        or not parsed.hostname
                        or parsed.username
                        or parsed.password
                    ):
                        raise MessageException("Invalid HAL HTTP URL.")
                    validate_non_local(url, allowlist)
                    headers = {"User-Agent": "Galaxy HAL file source"}
                    if method == "HEAD":
                        headers["Accept-Encoding"] = "identity"
                    with session.request(
                        method,
                        url,
                        params=params,
                        stream=True,
                        allow_redirects=False,
                        timeout=timeout,
                        headers=headers,
                    ) as response:
                        if response.is_redirect:
                            url = urljoin(response.url, response.headers["Location"])
                            params = None
                            continue
                        if response.status_code == 404:
                            raise ObjectNotFound("The requested HAL resource was not found.")
                        if response.status_code in (401, 403):
                            raise MessageException("This HAL file is not publicly accessible; it may be under embargo.")
                        response.raise_for_status()
                        content_type = response.headers.get("Content-Type", "").lower()
                        if not allow_html and content_type.startswith("text/html"):
                            raise MessageException("HAL returned an HTML page instead of the requested data.")
                        yield response
                        return
                raise MessageException("HAL returned too many redirects.")
        except (RequestException, HTTPError) as exc:
            raise MessageException(f"Unable to fetch HAL resource: {exc}") from exc


def _is_html(name: str) -> bool:
    return name.lower().endswith((".html", ".htm"))


def _parse_http_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


__all__ = ("HALFilesSource",)
