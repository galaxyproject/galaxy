import json
import posixpath
from contextlib import contextmanager
from typing import (
    Annotated,
    Any,
)
from urllib.parse import (
    quote,
    urlencode,
)

from pydantic import Field

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
from galaxy.files.sources._defaults import DEFAULT_SCHEME
from galaxy.files.uris import validate_non_local
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    requests,
    stream_to_path,
)
from galaxy.util.config_templates import TemplateExpansion
from . import BaseFilesSource

DEFAULT_API_URL = "https://www.ebi.ac.uk/biostudies/api/v1"
DEFAULT_FILES_URL = "https://www.ebi.ac.uk/biostudies/files"
DEFAULT_COLLECTION = "BioAIRepo"


class BioAIRepoFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    api_url: str | TemplateExpansion = DEFAULT_API_URL
    files_url: str | TemplateExpansion = DEFAULT_FILES_URL
    collection: str | TemplateExpansion = DEFAULT_COLLECTION


class BioAIRepoFileSourceConfiguration(BaseFileSourceConfiguration):
    api_url: Annotated[
        str,
        Field(title="BioStudies API URL", description="The EMBL-EBI BioStudies REST API base URL."),
    ] = DEFAULT_API_URL
    files_url: Annotated[
        str,
        Field(title="BioStudies files URL", description="The BioStudies public file download base URL."),
    ] = DEFAULT_FILES_URL
    collection: Annotated[
        str,
        Field(title="BioStudies collection", description="The BioStudies collection exposed by this source."),
    ] = DEFAULT_COLLECTION


class BioAIRepoFilesSource(
    BaseFilesSource[BioAIRepoFileSourceTemplateConfiguration, BioAIRepoFileSourceConfiguration]
):
    """Browse and import public files from the EMBL-EBI BioAIRepo collection."""

    plugin_type = "bioairepo"
    supports_pagination = True
    supports_search = True
    supports_recursive = True

    template_config_class = BioAIRepoFileSourceTemplateConfiguration
    resolved_config_class = BioAIRepoFileSourceConfiguration

    def __init__(self, template_config: BioAIRepoFileSourceTemplateConfiguration):
        defaults = dict(
            id="bioairepo",
            label="BioAIRepo",
            doc="Public AI-ready biology studies from EMBL-EBI BioStudies",
            writable=False,
        )
        template_config = self._apply_defaults_to_template(defaults, template_config)
        if template_config.writable:
            raise ValueError("BioAIRepo file sources are read-only and cannot be configured as writable.")
        super().__init__(template_config)

    @property
    def _allowlist(self):
        return self._file_sources_config.fetch_url_allowlist

    def get_scheme(self) -> str:
        return self.scheme if self.scheme and self.scheme != DEFAULT_SCHEME else self.plugin_type

    def get_url(self) -> str:
        return "https://www.ebi.ac.uk/biostudies/bioairepo/studies"

    def to_relative_path(self, url: str) -> str:
        legacy_uri_root = f"{DEFAULT_SCHEME}://{self.id}"
        if url.startswith(legacy_uri_root):
            return url[len(legacy_uri_root) :] or "/"
        return super().to_relative_path(url)

    def _list(
        self,
        context: FilesSourceRuntimeContext[BioAIRepoFileSourceConfiguration],
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: int | None = None,
        offset: int | None = None,
        query: str | None = None,
        sort_by: str | None = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        if write_intent:
            raise MessageException("BioAIRepo is read-only and does not support exporting files.")
        normalized_path = self._normalize_path(path)
        if normalized_path == "/":
            if recursive:
                raise MessageException("Select a BioAIRepo study folder to import its files recursively.")
            return self._list_studies(context.config, limit, offset, query)

        accession, relative_directory = self._split_path(normalized_path)
        file_records = self._study_files(accession, context.config)
        entries = self._directory_entries(accession, relative_directory, file_records)
        if recursive:
            # The study metadata contains all file paths, so no additional API calls
            # are needed to walk the directories beneath the selected folder.
            pending = [entry.path for entry in entries if isinstance(entry, RemoteDirectory)]
            while pending:
                directory = pending.pop()
                _, relative_path = self._split_path(directory)
                children = self._directory_entries(accession, relative_path, file_records)
                entries.extend(children)
                pending.extend(entry.path for entry in children if isinstance(entry, RemoteDirectory))
        if query:
            entries = [entry for entry in entries if query.casefold() in entry.name.casefold()]
        total = len(entries)
        return self._paginate(entries, limit, offset), total

    def _list_studies(
        self,
        config: BioAIRepoFileSourceConfiguration,
        limit: int | None,
        offset: int | None,
        query: str | None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        page_size = limit or 25
        start = offset or 0
        page = start // page_size + 1
        params: dict[str, str | int] = {"page": page, "pageSize": page_size}
        if query:
            params["query"] = query
        url = self._api_url(config, config.collection, "search", query=params)
        result = self._get_json(url)
        if not isinstance(result, dict) or not isinstance(result.get("hits"), list):
            raise MessageException("Invalid response from the BioStudies collection search endpoint.")

        entries: list[AnyRemoteEntry] = []
        for study in result["hits"]:
            if not isinstance(study, dict):
                continue
            accession = study.get("accession")
            if not isinstance(accession, str) or not accession:
                continue
            path = f"/{accession}"
            entries.append(RemoteDirectory(name=accession, uri=self.uri_from_path(path), path=path))

        # The API paginates by page. Account for a non-page-aligned Galaxy offset.
        within_page_offset = start % page_size
        if within_page_offset:
            entries = entries[within_page_offset:]
        total = result.get("totalHits", len(entries))
        return entries, total if isinstance(total, int) else len(entries)

    def _study_files(
        self, accession: str, config: BioAIRepoFileSourceConfiguration
    ) -> list[tuple[str, int]]:
        study = self._get_json(self._api_url(config, "studies", accession))
        if not isinstance(study, dict) or not study:
            raise ObjectNotFound(f"BioAIRepo study [{accession}] was not found.")

        files: dict[str, int] = {}

        def visit(value: Any) -> None:
            if isinstance(value, list):
                for child in value:
                    visit(child)
            elif isinstance(value, dict):
                path = value.get("path")
                if value.get("type") == "file" and isinstance(path, str):
                    normalized = self._safe_file_path(path)
                    if normalized:
                        size = value.get("size", 0)
                        files[normalized] = size if isinstance(size, int) and size >= 0 else 0
                for key in ("files", "subsections"):
                    if key in value:
                        visit(value[key])

        visit(study.get("section"))
        return sorted(files.items(), key=lambda item: item[0].casefold())

    def _directory_entries(
        self, accession: str, relative_directory: str, files: list[tuple[str, int]]
    ) -> list[AnyRemoteEntry]:
        prefix = f"{relative_directory.rstrip('/')}/" if relative_directory else ""
        directories: set[str] = set()
        output_files: list[tuple[str, int]] = []
        for file_path, size in files:
            if not file_path.startswith(prefix):
                continue
            remainder = file_path[len(prefix) :]
            if "/" in remainder:
                directories.add(remainder.split("/", 1)[0])
            elif remainder:
                output_files.append((remainder, size))

        entries: list[AnyRemoteEntry] = []
        base = f"/{accession}"
        if relative_directory:
            base = f"{base}/{relative_directory}"
        for name in sorted(directories, key=str.casefold):
            path = f"{base}/{name}"
            entries.append(RemoteDirectory(name=name, uri=self.uri_from_path(path), path=path))
        for name, size in sorted(output_files, key=lambda item: item[0].casefold()):
            path = f"{base}/{name}"
            entries.append(RemoteFile(name=name, size=size, uri=self.uri_from_path(path), path=path))
        return entries

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[BioAIRepoFileSourceConfiguration],
    ):
        accession, file_path = self._split_path(self._normalize_path(source_path))
        if not file_path:
            raise ObjectNotFound(f"The specified BioAIRepo path is not a file [{source_path}].")

        # Confirm that the requested path belongs to the public study before downloading it.
        available_paths = {path for path, _size in self._study_files(accession, context.config)}
        if file_path not in available_paths:
            raise ObjectNotFound(f"BioAIRepo file [{file_path}] was not found in study [{accession}].")
        download_url = "/".join(
            [context.config.files_url.rstrip("/"), quote(accession, safe=""), self._quote_path(file_path)]
        )
        with self._open_url(download_url, accept="application/octet-stream") as response:
            stream_to_path(response, native_path)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[BioAIRepoFileSourceConfiguration],
    ):
        raise MessageException("BioAIRepo is read-only and does not support exporting files.")

    def _get_json(self, url: str) -> Any:
        with self._open_url(url, accept="application/json") as response:
            return json.load(response)

    @contextmanager
    def _open_url(self, url: str, accept: str):
        validate_non_local(url, self._allowlist or [])
        with requests.Session() as session:
            with session.get(
                url,
                headers={"Accept": accept, "User-Agent": "Galaxy BioAIRepo file source"},
                stream=True,
                timeout=DEFAULT_SOCKET_TIMEOUT,
            ) as response:
                if response.status_code == 404:
                    raise ObjectNotFound(f"The BioStudies resource was not found [{url}].")
                response.raise_for_status()
                validate_non_local(response.url, self._allowlist or [])
                response.raw.decode_content = True
                yield response.raw

    def _api_url(
        self, config: BioAIRepoFileSourceConfiguration, *parts: str, query: dict[str, str | int] | None = None
    ) -> str:
        url = "/".join([config.api_url.rstrip("/"), *(quote(part.strip("/"), safe="") for part in parts)])
        return f"{url}?{urlencode(query)}" if query else url

    @staticmethod
    def _normalize_path(path: str) -> str:
        if not path or path == ".":
            return "/"
        if not path.startswith("/"):
            path = f"/{path}"
        return posixpath.normpath(path)

    @staticmethod
    def _safe_file_path(path: str) -> str | None:
        normalized = posixpath.normpath(path.replace("\\", "/")).lstrip("/")
        if not normalized or normalized == "." or normalized == ".." or normalized.startswith("../"):
            return None
        return normalized

    @staticmethod
    def _quote_path(path: str) -> str:
        return "/".join(quote(part, safe="") for part in path.split("/"))

    @staticmethod
    def _split_path(path: str) -> tuple[str, str]:
        parts = path.strip("/").split("/", 1)
        if not parts[0]:
            raise ObjectNotFound(f"Invalid BioAIRepo path [{path}].")
        return parts[0], parts[1] if len(parts) == 2 else ""

    @staticmethod
    def _paginate(entries: list[AnyRemoteEntry], limit: int | None, offset: int | None) -> list[AnyRemoteEntry]:
        start = offset or 0
        end = start + limit if limit is not None else None
        return entries[start:end]


__all__ = ("BioAIRepoFilesSource",)
