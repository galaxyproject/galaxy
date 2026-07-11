"""Galaxy FileSource implementation for OSF."""

from abc import ABC
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import urljoin, urlparse

from galaxy import exceptions as galaxy_exceptions
from galaxy.files.models import (
    AnyRemoteEntry,
    FilesSourceRuntimeContext,
    RemoteDirectory,
    RemoteFile,
)
from galaxy.files.sources._defaults import DEFAULT_SCHEME
from galaxy.files.sources._rdm import (
    ContainerAndFileIdentifier,
    RDMFileSourceConfiguration,
    RDMFileSourceTemplateConfiguration,
    RDMFilesSource,
    RDMRepositoryInteractor,
)
from galaxy.util import requests
from galaxy.util.config_templates import TemplateExpansion


OSF_DEFAULT_URL = "https://api.osf.io/v2/"
WATERBUTLER_URL = "https://files.osf.io/v1/"
DEFAULT_STORAGE = "osfstorage"
OSF_MAX_PAGE_SIZE = 100
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 60
CHUNK_SIZE = 64 * 1024


class OSFFileSourceTemplateConfiguration(RDMFileSourceTemplateConfiguration):
    type: str = "osf"
    url: Union[str, TemplateExpansion] = OSF_DEFAULT_URL
    token: Union[str, TemplateExpansion]


class OSFFileSourceConfiguration(RDMFileSourceConfiguration):
    url: str = OSF_DEFAULT_URL
    token: str


class OSFFilesSourceException(ABC, Exception):
    """Abstract base for every exception raised by this plugin."""


class InvalidPath(galaxy_exceptions.MessageException, OSFFilesSourceException):
    """Path is malformed or not absolute."""


class ResourceNotFound(galaxy_exceptions.ObjectNotFound, OSFFilesSourceException):
    """A project, registration, or file does not exist in OSF."""


class DirectoryExpected(galaxy_exceptions.MessageException, OSFFilesSourceException, ValueError):
    """A file path was given where a directory was expected."""


class FileExpected(galaxy_exceptions.MessageException, OSFFilesSourceException, ValueError):
    """A directory path was given where a file was expected."""


class ValidationError(galaxy_exceptions.MessageException, OSFFilesSourceException):
    """OSF returned an unexpected or malformed response."""


class OSFClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/") + "/"
        self.token = token
        self._session: Optional[requests.Session] = None

    def _make_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}

    def _make_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(self._make_headers())
        return session

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        if self._session is None:
            self._session = self._make_session()
        url = urljoin(self.base_url, endpoint.lstrip("/"))
        response = self._session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    def list_projects(
        self,
        page: int = 1,
        page_size: int = OSF_MAX_PAGE_SIZE,
        query: Optional[str] = None,
        write_intent: bool = False,
        sort: Optional[str] = None,
    ) -> dict:
        params: dict[str, Any] = {"page": page, "page[size]": page_size}
        if query:
            params["filter[title]"] = query
        if write_intent:
            params["filter[current_user_permissions]"] = "write"
        if sort:
            params["sort"] = sort
        return self._request(
            "GET", "users/me/nodes/",
            params=params, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )

    def list_registrations(
        self, page: int = 1, page_size: int = OSF_MAX_PAGE_SIZE,
    ) -> dict:
        return self._request(
            "GET", "users/me/registrations/",
            params={"page": page, "page[size]": page_size},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )

    def create_project(self, payload: dict) -> dict:
        return self._request(
            "POST", "nodes/",
            json=payload, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )

    # WaterButler
    def waterbutler_url(self, container_id: str, wb_path: str = "/") -> str:
        if not wb_path.startswith("/"):
            wb_path = "/" + wb_path
        return urljoin(
            WATERBUTLER_URL,
            f"resources/{container_id}/providers/{DEFAULT_STORAGE}{wb_path}",
        )

    def list_storage(self, container_id: str, wb_path: str = "/") -> list[dict]:
        if self._session is None:
            self._session = self._make_session()
        url = self.waterbutler_url(container_id, wb_path)
        response = self._session.get(
            url, params={"meta": ""}, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
        response.raise_for_status()
        return response.json().get("data", [])

    def upload(
        self, container_id: str, folder_wb_path: str, filename: str, local_path: str,
    ) -> dict:
        if self._session is None:
            self._session = self._make_session()
        url = self.waterbutler_url(container_id, folder_wb_path)
        params = {"kind": "file", "name": filename}
        with open(local_path, "rb") as f:
            response = self._session.put(
                url, params=params, data=f,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )
        response.raise_for_status()
        return response.json()

    def download(self, container_id: str, wb_path: str, local_path: str) -> None:
        if self._session is None:
            self._session = self._make_session()
        url = self.waterbutler_url(container_id, wb_path)
        try:
            with self._session.get(
                url, stream=True, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            ) as response:
                response.raise_for_status()
                with open(local_path, "wb") as out:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            out.write(chunk)
        except Exception:
            Path(local_path).unlink(missing_ok=True)
            raise


def has_parent(node: dict) -> bool:
    return node.get("relationships", {}).get("parent", {}).get("data") is not None


def node_title(node: dict) -> str:
    return node.get("attributes", {}).get("title", node.get("id", "untitled"))


def galaxy_pagination_to_osf(
    limit: Optional[int], offset: Optional[int],
) -> tuple[int, int]:
    """Translate Galaxy's (limit, offset) into OSF's (page, page[size]).

    OSF caps page[size] at OSF_MAX_PAGE_SIZE. When offset is not aligned to
    the page size, this returns the page that *contains* it (the framework
    trims; ``total`` is still accurate).
    """
    page_size = min(limit, OSF_MAX_PAGE_SIZE) if limit else OSF_MAX_PAGE_SIZE
    page = ((offset or 0) // page_size) + 1
    return page, page_size


def galaxy_sort_to_osf(sort_by: Optional[str]) -> Optional[str]:
    if not sort_by:
        return None
    return {
        "name": "title",
        "uri": "id",
        "path": "id",
        "ctime": "-date_modified",
        "size": "size",
    }.get(sort_by, "id")


class OSFRepositoryInteractor(RDMRepositoryInteractor):
    """OSF flavor of the RDM repository contract.

    A "container" is an OSF Project (GUID). Files inside a container are the
    files in its osfstorage, flattened (subfolder paths are encoded in
    ``file_identifier`` so downloads can find them again).
    """

    def to_plugin_uri(self, container_id: str, filename: Optional[str] = None) -> str:
        scheme = self.plugin.get_scheme()
        prefix = self.plugin.get_prefix() or ""
        if filename:
            return f"{scheme}://{prefix}/{container_id}/{filename}"
        return f"{scheme}://{prefix}/{container_id}"

    def get_file_containers(
        self,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
        write_intent: bool,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[RemoteDirectory], int]:
        client = self._client(context)
        page, page_size = galaxy_pagination_to_osf(limit, offset)
        payload = client.list_projects(
            page=page,
            page_size=page_size,
            query=query,
            write_intent=write_intent,
            sort=galaxy_sort_to_osf(sort_by),
        )
        nodes = [n for n in payload.get("data", []) if not has_parent(n)]
        total = int(payload.get("meta", {}).get("total", 0))
        containers = [
            RemoteDirectory(
                name=node_title(node),
                uri=self.to_plugin_uri(node["id"]),
                path=f"/{node['id']}",
            )
            for node in nodes
            ]
        return containers, total

    def get_files_in_container(
        self,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
        container_id: str,
        writeable: bool,
        query: Optional[str] = None,
    ) -> list[RemoteFile]:
        client = self._client(context)
        files = list(self._walk_files(client, container_id, wb_path="/", rel_prefix=""))
        if query:
            files = [f for f in files if query in f.get("name", "")]
        return files

    def create_draft_file_container(
        self,
        title: str,
        public_name: str,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
    ) -> dict[str, Any]:
        payload = {
            "data": {
                "type": "nodes",
                "attributes": {
                    "title": title,
                    "category": "project",
                    "public": False,
                    "description": f"Created by Galaxy on behalf of {public_name}",
                },
            }
        }
        return self._client(context).create_project(payload).get("data", {})

    def upload_file_to_draft_container(
        self,
        container_id: str,
        filename: str,
        file_path: str,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
    ) -> None:
        self._client(context).upload(container_id, "/", filename, file_path)

    def download_file_from_container(
        self,
        container_id: str,
        file_identifier: str,
        file_path: str,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
    ) -> None:
        if not file_identifier:
            raise FileExpected("cannot download without a file identifier")
        client = self._client(context)
        leaf = self._walk_to(client, container_id, file_identifier.split("/"))
        if leaf.get("attributes", {}).get("kind") != "file":
            raise FileExpected(
                f"path {file_identifier!r} resolved to a folder, not a file"
            )
        client.download(container_id, leaf["attributes"]["path"], file_path)

    # private helpers
    def _client(self, context) -> OSFClient:
        return OSFClient(self.repository_url, context.config.token)

    def _walk_to(
        self, client: OSFClient, container_id: str, segments: list,
    ) -> dict:
        """Descend osfstorage segment-by-segment, matching on name.

        osfstorage addresses children by internal WaterButler IDs, not names,
        so we list each level, pick the named child, and descend using its
        ``attributes.path``.
        """
        current_path = "/"
        leaf: Optional[dict] = None
        for segment in segments:
            items = client.list_storage(container_id, current_path)
            match = next(
                (it for it in items if it.get("attributes", {}).get("name") == segment),
                None,
            )
            if match is None:
                raise ResourceNotFound(
                    f"No entry named {segment!r} in osfstorage:{current_path}"
                )
            leaf = match
            current_path = match["attributes"]["path"]
        if leaf is None:
            raise InvalidPath("walk called with empty segments")
        return leaf

    def _walk_files(
        self, client: OSFClient, container_id: str, wb_path: str, rel_prefix: str,
    ):
        for item in client.list_storage(container_id, wb_path):
            attrs = item.get("attributes", {})
            name = attrs.get("name", "untitled")
            kind = attrs.get("kind")
            rel_path = name if not rel_prefix else f"{rel_prefix}/{name}"
            if kind == "folder":
                yield from self._walk_files(
                    client, container_id, attrs["path"], rel_path,
                )
            elif kind == "file":
                yield RemoteFile(**{
                    "name": name,
                    "uri": self.to_plugin_uri(container_id, rel_path),
                    "path": f"/{container_id}/{rel_path}",
                    "size": attrs.get("size", 0),
                    "ctime": attrs.get("modified_utc") or attrs.get("created_utc"),
                })


class OSFFilesSource(RDMFilesSource):
    plugin_type = "osf"
    supports_pagination = True
    supports_search = True
    supports_sorting = True

    template_config_class = OSFFileSourceTemplateConfiguration
    resolved_config_class = OSFFileSourceConfiguration

    def get_scheme(self) -> str:
        return (
            self.scheme
            if self.scheme and self.scheme != DEFAULT_SCHEME
            else "osf"
        )

    def get_prefix(self) -> Optional[str]:
        return self.id

    def score_url_match(self, url: str) -> int:
        parsed = urlparse(url)
        return sum(
            int(check)
            for check in (
                parsed.scheme == self.get_scheme(),
                parsed.netloc == self.get_prefix(),
            )
        )

    def to_relative_path(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path or "/"
        if not path.startswith("/"):
            path = f"/{path}"
        return path

    def user_has_access(self, user_context) -> bool:
        return user_context is not None  # true only when a token is configured

    # RDM contract
    def get_repository_interactor(self, repository_url: str) -> OSFRepositoryInteractor:
        return OSFRepositoryInteractor(repository_url=repository_url, plugin=self)

    def parse_path(
        self, source_path: str, container_id_only: bool = False,
    ) -> ContainerAndFileIdentifier:
        """Split a plugin path into (container_id, file_identifier).

        "/"                          -> ("", "")
        "/abc12"                     -> ("abc12", "")
        "/abc12/data.csv"            -> ("abc12", "data.csv")
        "/abc12/folder/sub/a.csv"    -> ("abc12", "folder/sub/a.csv")
        """
        path_obj = Path(source_path)
        if not path_obj.is_absolute():
            raise InvalidPath(
                f"Path must be absolute (start with '/'): {source_path!r}"
            )
        parts = path_obj.parts[1:]
        if not parts:
            return ContainerAndFileIdentifier(container_id="", file_identifier="")
        container_id = parts[0]
        if container_id_only or len(parts) == 1:
            return ContainerAndFileIdentifier(
                container_id=container_id, file_identifier="",
            )
        return ContainerAndFileIdentifier(
            container_id=container_id, file_identifier="/".join(parts[1:]),
        )

    def get_container_id_from_path(self, source_path: str) -> str:
        return self.parse_path(source_path, container_id_only=True).container_id

    # Galaxy contract
    def _list(
        self,
        context: FilesSourceRuntimeContext[OSFFileSourceConfiguration],
        path: str = "/",
        recursive: bool = False,
        write_intent: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        container_id = self.parse_path(path).container_id
        if not container_id:
            return self.repository.get_file_containers(
                context, write_intent, limit, offset, query, sort_by,
            )
        files = self.repository.get_files_in_container(
            context, container_id, writeable=write_intent, query=query,
        )
        return files, len(files)

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[OSFFileSourceConfiguration],
    ) -> None:
        identifier = self.parse_path(source_path)
        self.repository.download_file_from_container(
            identifier.container_id, identifier.file_identifier, native_path, context,
        )

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[OSFFileSourceConfiguration],
    ) -> str:
        identifier = self.parse_path(target_path)
        self.repository.upload_file_to_draft_container(
            identifier.container_id, identifier.file_identifier, native_path, context,
        )
        return target_path


__all__ = ("OSFFilesSource",)
