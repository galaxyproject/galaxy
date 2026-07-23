"""
Galaxy FilesSource implementation for OSF.

This module implements a FilesSource that interacts with the Open Science Framework (OSF) [1]. OSF is a free,
open-source platform for managing and sharing research projects, data and preprints. The central OSF concept is the
*node* [2]. This FilesSource works with two kinds of nodes: *projects* (mutable containers for research activity) and
*registrations* (immutable, timestamped snapshots of a project). A project can also contain child nodes called
*components*, which are themselves projects and can be nested arbitrarily. Files attached to a node live in one of
several storage providers; this implementation currently targets ``osfstorage``, OSF's default provider [3].

The FilesSource exposes three top-level categories under the plugin root: Projects lists the user's own projects (or
public projects when browsing anonymously), Registrations lists public registrations, and Files runs a search against
OSF's public file index [4]. Descending into a project or registration reveals its ``osfstorage`` contents and its
child components; components appear as subfolders and can be entered like any other folder. With a personal access
token [5] the user gains access to their private projects and can create new draft projects to upload Galaxy datasets
into.

Galaxy URIs take the form ``osf://osf/category/container_id/file_path``, where:

- ``category`` is one of ``projects``, ``registrations`` or ``files``
- ``container_id`` is the OSF node GUID (a short alphanumeric identifier, e.g. ``q2anz``)
- ``file_path`` is the slash-separated path to the file within the node's ``osfstorage``

The implementation is layered: ``OSFClient`` wraps the OSF REST API v2 [4] and the WaterButler API [6] using
``requests``; ``OSFRepositoryInteractor`` translates Galaxy's RDM interactor contract into OSF calls; and
``OSFFilesSource`` implements Galaxy's FilesSource contract on top of the interactor.

References:

- [1] https://osf.io/
- [2] https://help.osf.io/collection/75-projects-and-components
- [3] https://help.osf.io/article/387-files
- [4] https://developer.osf.io/
- [5] https://help.osf.io/article/390-profile-and-account#Create-a-Personal-Access-Token-8Z7ta
- [6] https://waterbutler.readthedocs.io/
"""

from abc import ABC
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import urljoin, urlparse

from galaxy import exceptions as galaxy_exceptions
from galaxy.files.models import (
    AnyRemoteEntry,
    Entry,
    EntryData,
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
DEFAULT_STORAGE = "osfstorage"
OSF_MAX_PAGE_SIZE = 100
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 60
CHUNK_SIZE = 64 * 1024

CATEGORY_FOLDERS = {
    "projects": "Projects",
    "registrations": "Registrations",
    "files": "Files",
}


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
        self.waterbutler_base_url = self.base_url.replace("api.osf.io/v2", "files.osf.io/v1")
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
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
        endpoint = "nodes/"
        params: dict[str, Any] = {"page": page, "page[size]": page_size}
        if query:
            params["filter[title]"] = query
        if write_intent:
            endpoint = "users/me/nodes/"
            params["filter[current_user_permissions]"] = "write"
        if sort:
            params["sort"] = sort
        return self._request(
            "GET", endpoint,
            params=params, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )

    def list_registrations(
        self,
        page: int = 1,
        page_size: int = OSF_MAX_PAGE_SIZE,
        query: Optional[str] = None,
        sort: Optional[str] = None,
    ) -> dict:
        params: dict[str, Any] = {"page": page, "page[size]": page_size}
        if query:
            params["filter[title]"] = query
        if sort:
            params["sort"] = sort
        return self._request(
            "GET", "registrations/",
            params=params, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )

    def list_files(
        self,
        page: int = 1,
        page_size: int = OSF_MAX_PAGE_SIZE,
        query: Optional[str] = None,
    ) -> dict:
        params: dict[str, Any] = {"page": page, "page[size]": page_size}
        if query:
            params["q"] = query
        return self._request(
            "GET", "search/files/",
            params=params, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )

    def list_children(
        self,
        node_id: str,
        page: int = 1,
        page_size: int = OSF_MAX_PAGE_SIZE,
    ) -> list[dict]:
        payload = self._request(
            "GET", f"nodes/{node_id}/children/",
            params={"page": page, "page[size]": page_size},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
        return payload.get("data", [])

    def create_project(self, title: str, description: str) -> dict:
        payload = {
            "data": {
                "type": "nodes",
                "attributes": {
                    "title": title,
                    "category": "project",
                    "public": False,
                    "description": description,
                },
            }
        }
        return self._request(
            "POST", "nodes/",
            json=payload, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        ).get("data", {})

    # WaterButler
    def waterbutler_url(self, container_id: str, wb_path: str = "/") -> str:
        if not wb_path.startswith("/"):
            wb_path = "/" + wb_path
        return urljoin(
            self.waterbutler_base_url,
            f"resources/{container_id}/providers/{DEFAULT_STORAGE}{wb_path}",
        )

    def list_storage(self, container_id: str, wb_path: str = "/") -> list[dict]:
        url = self.waterbutler_url(container_id, wb_path)
        response = self._session.get(
            url, params={"meta": ""}, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
        response.raise_for_status()
        return response.json().get("data", [])

    def upload(
        self, container_id: str, folder_wb_path: str, filename: str, local_path: str,
    ) -> dict:
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

    def to_plugin_uri(
        self,
        container_id: str,
        filename: Optional[str] = None,
        category: str = "projects",
    ) -> str:
        scheme = self.plugin.get_scheme()
        prefix = self.plugin.get_prefix() or ""
        base = f"{scheme}://{prefix}/{category}/{container_id}"
        if filename:
            return f"{base}/{filename}"
        return base

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
        total = int(payload["links"]["meta"]["total"])
        containers = [
            RemoteDirectory(
                name=node_title(node),
                uri=self.to_plugin_uri(node["id"]),
                path=f"/projects/{node['id']}",
            )
            for node in nodes
            ]
        return containers, total

    def get_registration_containers(
        self,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[RemoteDirectory], int]:
        client = self._client(context)
        page, page_size = galaxy_pagination_to_osf(limit, offset)
        payload = client.list_registrations(
            page=page,
            page_size=page_size,
            query=query,
            sort=galaxy_sort_to_osf(sort_by),
        )
        nodes = payload.get("data", [])
        total = int(payload["links"]["meta"]["total"])
        containers = [
            RemoteDirectory(
                name=node_title(node),
                uri=self.to_plugin_uri(node["id"], category="registrations"),
                path=f"/registrations/{node['id']}",
            )
            for node in nodes
        ]
        return containers, total

    def get_files_search_results(
        self,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
        query: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> tuple[list[RemoteFile], int]:
        client = self._client(context)
        page, page_size = galaxy_pagination_to_osf(limit, offset)
        payload = client.list_files(
            page=page, page_size=page_size, query=query,
        )
        hits = payload.get("data", [])
        total = int(payload["links"]["meta"]["total"])
        files: list[RemoteFile] = []
        for hit in hits:
            attrs = hit.get("attributes", {})
            name = attrs.get("name", "untitled")
            node_data = hit.get("relationships", {}).get("node", {}).get("data") or {}
            parent_pid = node_data.get("id", "")
            rel_path = attrs.get("materialized_path", name).lstrip("/")
            if parent_pid:
                uri = self.to_plugin_uri(parent_pid, rel_path)
                path = f"/projects/{parent_pid}/{rel_path}"
            else:
                uri = f"{self.plugin.get_scheme()}://{self.plugin.get_prefix()}/files/{name}"
                path = f"/files/{name}"
            files.append(RemoteFile(
                name=name,
                uri=uri,
                path=path,
                size=attrs.get("size", 0),
                ctime=attrs.get("date_modified") or attrs.get("date_created"),
            ))
        return files, total

    def list_folder(
        self,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
        container_id: str,
        subpath: str = "",
        category: str = "projects",
        query: Optional[str] = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        """List one level of a container's osfstorage.

        Returns folders as ``RemoteDirectory`` and files as ``RemoteFile``.
        Does not recurse: descending into a subfolder is a separate call,
        triggered by the user navigating into it. This preserves the actual
        OSF folder hierarchy (REQ-1.6).

        When at the container root (no subpath) and the container is a project
        or registration, child components are included as ``RemoteDirectory``
        entries so the user can navigate into them like folders.
        """
        client = self._client(context)
        if subpath:
            leaf = self._walk_to(client, container_id, subpath.split("/"))
            if leaf.get("attributes", {}).get("kind") != "folder":
                raise DirectoryExpected(
                    f"path {subpath!r} is not a folder"
                )
            wb_path = leaf["attributes"]["path"]
        else:
            wb_path = "/"
        entries: list[AnyRemoteEntry] = []
        if not subpath and category in ("projects", "registrations"):
            try:
                for child in client.list_children(container_id):
                    entries.append(RemoteDirectory(
                        name=node_title(child),
                        uri=self.to_plugin_uri(child["id"], category=category),
                        path=f"/{category}/{child['id']}",
                    ))
            except Exception:
                pass
        for item in client.list_storage(container_id, wb_path):
            attrs = item.get("attributes", {})
            name = attrs.get("name", "untitled")
            kind = attrs.get("kind")
            rel_path = f"{subpath}/{name}" if subpath else name
            if kind == "folder":
                entries.append(RemoteDirectory(
                    name=name,
                    uri=self.to_plugin_uri(container_id, rel_path, category=category),
                    path=f"/{category}/{container_id}/{rel_path}",
                ))
            elif kind == "file":
                entries.append(RemoteFile(
                    name=name,
                    uri=self.to_plugin_uri(container_id, rel_path, category=category),
                    path=f"/{category}/{container_id}/{rel_path}",
                    size=attrs.get("size", 0),
                    ctime=attrs.get("modified_utc") or attrs.get("created_utc"),
                ))
        if query:
            entries = [e for e in entries if query in e.name]
        return entries, len(entries)

    def get_files_in_container(
        self,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
        container_id: str,
        writeable: bool,
        query: Optional[str] = None,
        category: str = "projects",
    ) -> list[RemoteFile]:
        client = self._client(context)
        files = list(self._walk_files(client, container_id, wb_path="/", rel_prefix="", category=category))
        if query:
            files = [f for f in files if query in f.get("name", "")]
        return files

    def create_draft_file_container(
        self,
        title: str,
        public_name: str,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
    ) -> dict[str, Any]:
        return self._client(context).create_project(
            title=title,
            description=f"Created by Galaxy on behalf of {public_name}",
        )

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
        self,
        client: OSFClient,
        container_id: str,
        wb_path: str,
        rel_prefix: str,
        category: str = "projects",
    ):
        for item in client.list_storage(container_id, wb_path):
            attrs = item.get("attributes", {})
            name = attrs.get("name", "untitled")
            kind = attrs.get("kind")
            rel_path = name if not rel_prefix else f"{rel_prefix}/{name}"
            if kind == "folder":
                yield from self._walk_files(
                    client, container_id, attrs["path"], rel_path, category=category,
                )
            elif kind == "file":
                yield RemoteFile(**{
                    "name": name,
                    "uri": self.to_plugin_uri(container_id, rel_path, category=category),
                    "path": f"/{category}/{container_id}/{rel_path}",
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

    # RDM contract
    def get_repository_interactor(self, repository_url: str) -> OSFRepositoryInteractor:
        return OSFRepositoryInteractor(repository_url=repository_url, plugin=self)

    def parse_path(
        self, source_path: str, container_id_only: bool = False,
    ) -> ContainerAndFileIdentifier:
        """Split a plugin path into (container_id, file_identifier).

        Paths follow /<category>/<container_id>/<optional-subpath>, where
        <category> is one of "projects", "registrations", or "files". The
        leading category segment is stripped; callers that only care about
        the container do not need to know which category the container came
        from. Paths that omit the category (older URIs) are still accepted.

        "/"                                    -> ("", "")
        "/projects"                            -> ("", "")
        "/projects/abc12"                      -> ("abc12", "")
        "/projects/abc12/data.csv"             -> ("abc12", "data.csv")
        "/projects/abc12/folder/sub/a.csv"     -> ("abc12", "folder/sub/a.csv")
        """
        path_obj = Path(source_path)
        if not path_obj.is_absolute():
            raise InvalidPath(
                f"Path must be absolute (start with '/'): {source_path!r}"
            )
        parts = path_obj.parts[1:]
        if not parts:
            return ContainerAndFileIdentifier(container_id="", file_identifier="")
        if parts[0] in CATEGORY_FOLDERS:
            parts = parts[1:]
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
        parts = [p for p in path.strip("/").split("/") if p]

        # Root: return the three fake category folders.
        if not parts:
            entries: list[AnyRemoteEntry] = [
                RemoteDirectory(
                    name=label,
                    uri=f"{self.get_scheme()}://{self.get_prefix()}/{key}",
                    path=f"/{key}",
                )
                for key, label in CATEGORY_FOLDERS.items()
            ]
            return entries, len(entries)

        # /<category>: list items in that category.
        if len(parts) == 1 and parts[0] in CATEGORY_FOLDERS:
            category = parts[0]
            if category == "projects":
                return self.repository.get_file_containers(
                    context, write_intent, limit, offset, query, sort_by,
                )
            if category == "registrations":
                return self.repository.get_registration_containers(
                    context, limit, offset, query, sort_by,
                )
            if category == "files":
                return self.repository.get_files_search_results(
                    context, query, limit, offset,
                )

        # /<category>/<container_id>/<optional-subpath>: list one level of
        # that container's osfstorage. Old-shape paths (no category) are
        # treated as projects.
        if parts[0] in CATEGORY_FOLDERS:
            category = parts[0]
            container_id = parts[1] if len(parts) > 1 else ""
            subpath = "/".join(parts[2:])
        else:
            category = "projects"
            container_id = parts[0]
            subpath = "/".join(parts[1:])
        return self.repository.list_folder(
            context, container_id, subpath=subpath, category=category, query=query,
        )

    def _create_entry(
        self,
        entry_data: EntryData,
        context: FilesSourceRuntimeContext[OSFFileSourceConfiguration],
    ) -> Entry:
        public_name = self.get_public_name(context)
        record = self.repository.create_draft_file_container(
            entry_data.name, public_name, context,
        )
        record_id = record.get("id")
        if not record_id:
            raise ValidationError("OSF did not return an id for the new project.")
        title = record.get("attributes", {}).get("title") or entry_data.name
        external_link = record.get("links", {}).get("html", "")
        uri = self.repository.to_plugin_uri(str(record_id), category="projects")
        return Entry(
            name=title,
            uri=uri,
            external_link=external_link,
        )

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
