import html
import json
import posixpath
import re
import tarfile
import urllib.request
from typing import (
    Annotated,
    Optional,
    Union,
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
    stream_to_open_named_file,
)
from galaxy.util.config_templates import TemplateExpansion
from . import BaseFilesSource

DEFAULT_STUDY_FILES = [
    "data_clinical_patient.txt",
    "data_clinical_sample.txt",
    "data_mutations.txt",
    "data_cna.txt",
]
STUDY_METADATA_NAME = "study.json"
HTML_TAG_RE = re.compile(r"<[^>]+>")


class CBioPortalFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    api_url: Union[str, TemplateExpansion]
    datahub_url: Union[str, TemplateExpansion]
    study_files: list[str] = Field(default_factory=lambda: list(DEFAULT_STUDY_FILES))


class CBioPortalFileSourceConfiguration(BaseFileSourceConfiguration):
    api_url: Annotated[
        str,
        Field(
            title="cBioPortal API URL",
            description="The cBioPortal API endpoint used to list and fetch study metadata.",
        ),
    ]
    datahub_url: Annotated[
        str,
        Field(
            title="cBioPortal DataHub URL",
            description="The base URL used to download public study archives.",
        ),
    ]
    study_files: list[str] = Field(default_factory=lambda: list(DEFAULT_STUDY_FILES))


class CBioPortalFilesSource(
    BaseFilesSource[CBioPortalFileSourceTemplateConfiguration, CBioPortalFileSourceConfiguration]
):
    plugin_type = "cbioportal"
    supports_pagination = True
    supports_search = True

    template_config_class = CBioPortalFileSourceTemplateConfiguration
    resolved_config_class = CBioPortalFileSourceConfiguration

    def __init__(self, template_config: CBioPortalFileSourceTemplateConfiguration):
        defaults = dict(
            id="cbioportal",
            label="cBioPortal",
            doc="Public cBioPortal study data",
            writable=False,
        )
        template_config = self._apply_defaults_to_template(defaults, template_config)
        if template_config.writable:
            raise ValueError("cBioPortal file sources are read-only and cannot be configured as writable.")
        super().__init__(template_config)

    @property
    def _allowlist(self):
        return self._file_sources_config.fetch_url_allowlist

    def get_scheme(self) -> str:
        return self.scheme if self.scheme and self.scheme != DEFAULT_SCHEME else self.plugin_type

    def to_relative_path(self, url: str) -> str:
        legacy_uri_root = f"{DEFAULT_SCHEME}://{self.id}"
        if url.startswith(legacy_uri_root):
            return url[len(legacy_uri_root) :] or "/"
        return super().to_relative_path(url)

    def _list(
        self,
        context: FilesSourceRuntimeContext[CBioPortalFileSourceConfiguration],
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        normalized_path = self._normalize_path(path)
        if write_intent:
            raise MessageException("cBioPortal file sources are read-only and do not support exporting files.")
        if recursive:
            raise MessageException("Recursive listing is not supported for cBioPortal file sources.")

        if normalized_path == "/":
            entries: list[AnyRemoteEntry] = [
                RemoteDirectory(name="Studies", uri=self.uri_from_path("/studies"), path="/studies")
            ]
        elif normalized_path == "/studies":
            entries = self._list_studies(context)
        elif normalized_path.startswith("/studies/"):
            study_id, filename = self._split_study_path(normalized_path)
            if filename:
                raise ObjectNotFound(f"The specified cBioPortal path is not a directory [{path}].")
            entries = self._list_study_files(study_id, context.config)
        else:
            raise ObjectNotFound(f"The specified cBioPortal path does not exist [{path}].")

        if query:
            entries = [entry for entry in entries if query.lower() in entry.name.lower()]
        total_count = len(entries)
        return self._apply_pagination(entries, limit, offset), total_count

    def _list_studies(
        self, context: FilesSourceRuntimeContext[CBioPortalFileSourceConfiguration]
    ) -> list[AnyRemoteEntry]:
        studies = self._get_json(self._api_url(context.config, "studies"))
        if not isinstance(studies, list):
            raise MessageException("Invalid response from cBioPortal studies endpoint.")
        entries: list[AnyRemoteEntry] = []
        for study in studies:
            if not isinstance(study, dict):
                continue
            study_id = study.get("studyId")
            if not isinstance(study_id, str) or not study_id:
                continue
            entries.append(
                RemoteDirectory(
                    name=study_id,
                    uri=self.uri_from_path(f"/studies/{study_id}"),
                    path=f"/studies/{study_id}",
                )
            )
        entries.sort(key=lambda entry: entry.name.lower())
        return entries

    def _list_study_files(self, study_id: str, config: CBioPortalFileSourceConfiguration) -> list[AnyRemoteEntry]:
        filenames = [STUDY_METADATA_NAME, *config.study_files, self._archive_name(study_id)]
        return [
            RemoteFile(
                name=filename,
                uri=self.uri_from_path(f"/studies/{study_id}/{filename}"),
                path=f"/studies/{study_id}/{filename}",
            )
            for filename in filenames
        ]

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[CBioPortalFileSourceConfiguration],
    ):
        path = self._normalize_path(source_path)
        study_id, filename = self._split_study_path(path)
        if not filename:
            raise ObjectNotFound(f"The specified cBioPortal path is not a file [{source_path}].")
        if filename == STUDY_METADATA_NAME:
            self._write_study_metadata(study_id, native_path, context.config)
        elif filename == self._archive_name(study_id):
            self._stream_url_to_file(self._archive_url(context.config, study_id), native_path)
        elif filename in context.config.study_files:
            self._extract_study_file(study_id, filename, native_path, context.config)
        else:
            raise ObjectNotFound(f"The specified cBioPortal file is not available [{filename}].")

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[CBioPortalFileSourceConfiguration],
    ):
        raise MessageException("cBioPortal file sources are read-only and do not support exporting files.")

    def _write_study_metadata(self, study_id: str, native_path: str, config: CBioPortalFileSourceConfiguration) -> None:
        study = self._get_json(self._api_url(config, "studies", study_id))
        with open(native_path, "w") as out:
            json.dump(self._sanitize_metadata_for_galaxy(study), out, indent=2, sort_keys=True)
            out.write("\n")

    def _extract_study_file(
        self,
        study_id: str,
        filename: str,
        native_path: str,
        config: CBioPortalFileSourceConfiguration,
    ) -> None:
        archive_url = self._archive_url(config, study_id)
        with self._urlopen(archive_url) as response:
            with tarfile.open(fileobj=response, mode="r|gz") as archive:
                for member in archive:
                    if not member.isfile():
                        continue
                    if posixpath.basename(member.name) != filename:
                        continue
                    source = archive.extractfile(member)
                    if source is None:
                        break
                    with open(native_path, "wb") as out:
                        while chunk := source.read(1024 * 1024):
                            out.write(chunk)
                    return
        raise ObjectNotFound(f"File [{filename}] was not found in cBioPortal study archive [{study_id}].")

    def _get_json(self, url: str):
        with self._urlopen(url) as response:
            return json.load(response)

    def _stream_url_to_file(self, url: str, native_path: str) -> None:
        with self._urlopen(url) as response:
            f = open(native_path, "wb")  # fd will be .close()ed in stream_to_open_named_file
            stream_to_open_named_file(response, f.fileno(), native_path)

    def _urlopen(self, url: str):
        validate_non_local(url, self._allowlist or [])
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json" if "/api/" in url else "application/octet-stream",
                "User-Agent": "Galaxy cBioPortal file source",
            },
        )
        response = urllib.request.urlopen(request, timeout=DEFAULT_SOCKET_TIMEOUT)
        validate_non_local(response.geturl(), self._allowlist or [])
        return response

    def _api_url(self, config: CBioPortalFileSourceConfiguration, *parts: str) -> str:
        return "/".join([config.api_url.rstrip("/"), *(part.strip("/") for part in parts)])

    def _archive_url(self, config: CBioPortalFileSourceConfiguration, study_id: str) -> str:
        return f"{config.datahub_url.rstrip('/')}/{study_id}.tar.gz"

    def _archive_name(self, study_id: str) -> str:
        return f"{study_id}.tar.gz"

    def _sanitize_metadata_for_galaxy(self, value):
        if isinstance(value, dict):
            return {key: self._sanitize_metadata_for_galaxy(child) for key, child in value.items()}
        if isinstance(value, list):
            return [self._sanitize_metadata_for_galaxy(child) for child in value]
        if isinstance(value, str):
            return html.unescape(HTML_TAG_RE.sub("", value))
        return value

    def _normalize_path(self, path: str) -> str:
        if not path or path == ".":
            return "/"
        if not path.startswith("/"):
            path = f"/{path}"
        return posixpath.normpath(path)

    def _split_study_path(self, path: str) -> tuple[str, Optional[str]]:
        parts = self._normalize_path(path).strip("/").split("/")
        if len(parts) < 2 or parts[0] != "studies" or not parts[1]:
            raise ObjectNotFound(f"Invalid cBioPortal path [{path}]. Expected /studies/<study_id>[/<filename>].")
        if len(parts) == 2:
            return parts[1], None
        if len(parts) == 3 and parts[2]:
            return parts[1], parts[2]
        raise ObjectNotFound(f"Invalid cBioPortal path [{path}]. Expected /studies/<study_id>[/<filename>].")

    def _apply_pagination(
        self, entries: list[AnyRemoteEntry], limit: Optional[int], offset: Optional[int]
    ) -> list[AnyRemoteEntry]:
        if offset is None and limit is None:
            return entries
        start = offset or 0
        end = start + limit if limit is not None else None
        return entries[start:end]


__all__ = ("CBioPortalFilesSource",)
