"""Public, read-only access to versioned HAL deposits and their attached files."""

import re
from contextlib import contextmanager
from urllib.parse import (
    quote,
    unquote,
    urljoin,
    urlsplit,
    urlunsplit,
)

from requests import RequestException

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
RECORD_RE = re.compile(r"([a-z][a-z0-9-]*-[0-9]+)v([1-9][0-9]*)")
FIELDS = "halId_s,version_i,title_s,files_s,fileAnnexes_s"


class HALFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    api_url: str | TemplateExpansion = DEFAULT_API_URL


class HALFileSourceConfiguration(BaseFileSourceConfiguration):
    api_url: str = DEFAULT_API_URL


class HALFilesSource(BaseFilesSource[HALFileSourceTemplateConfiguration, HALFileSourceConfiguration]):
    plugin_type = "hal"
    supports_pagination = True
    supports_search = True
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
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: int | None = None,
        offset: int | None = None,
        query: str | None = None,
        sort_by: str | None = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        if write_intent:
            raise MessageException("HAL file sources are read-only and do not support exporting files.")
        if recursive:
            raise MessageException("Recursive listing is not supported for HAL file sources.")
        if path in ("", "/"):
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
        files = self._record_files(record_id, context.config)
        entries = [
            RemoteFile(name=name, path=file_path, uri=self.uri_from_path(file_path))
            for file_path, (name, _) in files.items()
            if not query or query.casefold() in name.casefold()
        ]
        start = offset or 0
        return entries[start : start + limit if limit is not None else None], len(entries)

    def _realize_to(self, source_path, native_path, context: FilesSourceRuntimeContext[HALFileSourceConfiguration]):
        record_id, filename = self._split_path(source_path)
        if filename is None:
            raise ObjectNotFound(f"HAL path is not a file: {source_path}")
        files = self._record_files(record_id, context.config)
        file_path = f"/{record_id}/{filename}"
        if file_path not in files:
            raise ObjectNotFound(f"File not found in HAL deposit: {source_path}")
        with self._open_url(files[file_path][1]) as response:
            response.raw.decode_content = True
            stream_to_path(response.raw, native_path)

    def _write_from(self, target_path, native_path, context):
        raise MessageException("HAL file sources are read-only and do not support exporting files.")

    def _search(self, config: HALFileSourceConfiguration, **params):
        with self._open_url(config.api_url, params={"wt": "json", "fl": FIELDS, **params}) as response:
            try:
                result = response.json()["response"]
                if not isinstance(result["docs"], list) or not isinstance(result["numFound"], int):
                    raise ValueError("Invalid search results")
                return result
            except (ValueError, KeyError, TypeError) as exc:
                raise MessageException("Invalid response from the HAL search API.") from exc

    def _record_files(self, record_id: str, config: HALFileSourceConfiguration) -> dict[str, tuple[str, str]]:
        match = RECORD_RE.fullmatch(record_id)
        assert match is not None  # checked by _split_path
        hal_id, _ = match.groups()
        # The search index exposes the current version only. Never substitute that version for a saved path.
        result = self._search(config, q=f'halId_s:"{hal_id}"', rows=1)
        if not result["docs"]:
            raise ObjectNotFound(f"HAL deposit not found: {record_id}")
        record = result["docs"][0]
        if self._record_id(record) != record_id:
            raise MessageException(
                "HAL returned a different deposit version than requested. "
                "The search API only exposes the current version; browse the deposit again to select its current files."
            )
        files: dict[str, tuple[str, str]] = {}
        for url in [*record.get("files_s", []), *record.get("fileAnnexes_s", [])]:
            parsed = urlsplit(url)
            host = parsed.hostname or ""
            if parsed.scheme != "https" or not (
                host == "hal.science"
                or host.endswith(".hal.science")
                or host == "hal.inrae.fr"
                or host == "archives-ouvertes.fr"
                or host.endswith(".archives-ouvertes.fr")
            ):
                continue  # Associated datasets hosted by other repositories are outside this source's scope.
            parts = parsed.path.split("/")
            if len(parts) != 4 or parts[1] not in (hal_id, record_id) or parts[2] != "file":
                continue
            name = unquote(parts[3])
            if not name or name in (".", "..") or "/" in name or "\\" in name:
                continue
            # HAL's index returns unversioned URLs; pin them before exposing or downloading the file.
            versioned_url = urlunsplit((parsed.scheme, parsed.netloc, f"/{record_id}/file/{parts[3]}", "", ""))
            file_path = f"/{record_id}/{quote(name, safe='')}"
            if file_path in files and files[file_path][1] != versioned_url:
                raise MessageException(f"HAL returned ambiguous attachments named {name}.")
            files[file_path] = (name, versioned_url)
        return dict(sorted(files.items()))

    @staticmethod
    def _record_id(record) -> str:
        record_id = f"{record.get('halId_s')}v{record.get('version_i')}"
        if not RECORD_RE.fullmatch(record_id):
            raise MessageException("HAL returned an invalid deposit identifier or version.")
        return record_id

    @staticmethod
    def _split_path(path: str) -> tuple[str, str | None]:
        parts = path.removeprefix("/").split("/")
        if not RECORD_RE.fullmatch(parts[0]) or len(parts) > 2 or (len(parts) == 2 and not parts[1]):
            raise ObjectNotFound(f"Invalid HAL path: {path}. Expected /<hal-id>v<version>[/<filename>].")
        return parts[0], parts[1] if len(parts) == 2 else None

    @contextmanager
    def _open_url(self, url: str, params=None):
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
                    with session.get(
                        url,
                        params=params,
                        stream=True,
                        allow_redirects=False,
                        timeout=DEFAULT_SOCKET_TIMEOUT,
                        headers={"User-Agent": "Galaxy HAL file source"},
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
                        if response.headers.get("Content-Type", "").lower().startswith("text/html"):
                            raise MessageException("HAL returned an HTML page instead of the requested data.")
                        yield response
                        return
                raise MessageException("HAL returned too many redirects.")
        except RequestException as exc:
            raise MessageException(f"Unable to fetch HAL resource: {exc}") from exc


__all__ = ("HALFilesSource",)
