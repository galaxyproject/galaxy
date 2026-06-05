"""Galaxy FileSource implementation for OSF."""

from typing import Union, Optional
from abc import ABC

from galaxy import exceptions as galaxy_exceptions
from galaxy.util import requests
from galaxy.files.models import (
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
)
from galaxy.util.config_templates import TemplateExpansion

from urllib.parse import urljoin

OSF_DEFAULT_URL = "https://api.osf.io/v2/"
TOP_LEVEL_CATEGORIES = ("Projects", "Registrations", "Files")


class OSFFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    type: str = "osf"
    url: Union[str, TemplateExpansion] = OSF_DEFAULT_URL
    token: Union[str, TemplateExpansion]


class OSFFileSourceConfiguration(BaseFileSourceConfiguration):
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


def parse_path(path: str) -> tuple[Optional[str], Optional[str], list[str]]:
    """Split a virtual OSF path into (category, record_title, remaining_parts).

    "/"                            -> (None, None, [])
    "/Projects"                    -> ("Projects", None, [])
    "/Projects/My Research"        -> ("Projects", "My Research", [])
    "/Projects/My Research/x/a.csv"-> ("Projects", "My Research", ["x", "a.csv"])
    """
    if not isinstance(path, str) or not path.startswith("/"):
        raise InvalidPath(f"Path must be absolute (start with '/'): {path!r}")
    parts = [segment for segment in path.split("/") if segment]
    if not parts:
        return (None, None, [])
    category = parts[0]
    if category not in TOP_LEVEL_CATEGORIES:
        raise InvalidPath(f"Unknown category {category!r}; expected {TOP_LEVEL_CATEGORIES}.")
    record_title = parts[1] if len(parts) > 1 else None
    return (category, record_title, parts[2:])


class _OSFClient:
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

    def list_projects(self, only_latest: bool = True) -> list[dict]:
        nodes = self._request("GET", "users/me/nodes/").get("data", [])
        if only_latest:
            nodes = [n for n in nodes if not _has_parent(n)]
        return nodes

    def list_registrations(self) -> list[dict]:
        return self._request("GET", "users/me/registrations/").get("data", [])

    # still to do (raise so unfinished paths fail loudly)
    def list_files_top_level(self) -> list[dict]:
        raise NotImplementedError("design step 9: /Files listing.")

    def get_node_by_title(self, title: str, parent_guid: Optional[str] = None) -> Optional[dict]:
        raise NotImplementedError("title -> GUID resolution.")

    def list_storage_files(self, node_guid: str, storage: str, path: str = "") -> list[dict]:
        raise NotImplementedError("WaterButler listing.")

    def get_download_url(self, node_guid: str, storage: str, path: str) -> str:
        raise NotImplementedError("needed for _realize_to.")

    def upload_file(self, node_guid, storage, folder_path, filename, file_obj) -> dict:
        raise NotImplementedError("needed for _write_from.")

    def resolve_guid(self, path_segment: str, parent_guid: Optional[str] = None) -> str:
        raise NotImplementedError("walk one path level title -> GUID.")


def _has_parent(node: dict) -> bool:
    return node.get("relationships", {}).get("parent", {}).get("data") is not None


def _node_title(node: dict) -> str:
    return node.get("attributes", {}).get("title", node.get("id", "untitled"))


class OSFFilesSource(RDMFilesource):
    # TODO(design): target base is RDMFilesSource (-> BaseFilesSource). Switch
    plugin_type = "osf"
    supports_pagination = True  # spec'd in design, not implemented yet
    supports_search = True
    supports_sorting = True

    template_config_class = OSFFileSourceTemplateConfiguration
    resolved_config_class = OSFFileSourceConfiguration

    def get_scheme(self) -> str:
        return "osf"

    def get_prefix(self) -> Optional[str]:
        return None  # mirror elabftw.get_prefix() once config is wired in

    def score_url_match(self, url: str) -> int:
        scheme = f"{self.get_scheme()}://"
        return len(scheme) if url.startswith(scheme) else 0

    def to_relative_path(self, url: str) -> str:
        scheme = f"{self.get_scheme()}://"
        if url.startswith(scheme):
            remainder = url[len(scheme):]
            return "/" + remainder.split("/", 1)[1] if "/" in remainder else "/"
        return url

    def user_has_access(self, user_context) -> bool:
        return user_context is not None  # true only when a token is configured

    def _list(self, path="/", recursive=False, user_context=None, opts=None,
              limit=None, offset=None, query=None, sort_by=None) -> tuple[list[dict], int]:
        category, record_title, remaining = parse_path(path)
        if category is None:  # "/"
            entries = [self._directory_entry(n, f"/{n}") for n in TOP_LEVEL_CATEGORIES]
            return entries, len(entries)
        if category == "Projects" and record_title is None:
            return self._list_projects(self._build_client(user_context))
        if category == "Registrations" and record_title is None:
            client = self._build_client(user_context)
            entries = [self._directory_entry(_node_title(n), f"/Registrations/{_node_title(n)}")
                       for n in client.list_registrations()]
            return entries, len(entries)
        raise NotImplementedError(f"Listing not implemented yet for: {path!r}")

    def _list_projects(self, client: "_OSFClient") -> tuple[list[dict], int]:
        entries = [self._directory_entry(_node_title(n), f"/Projects/{_node_title(n)}")
                   for n in client.list_projects(only_latest=True)]
        return entries, len(entries)

    def _realize_to(self, source_path, native_path, user_context=None, opts=None):
        raise NotImplementedError("download: design step 7.")

    def _write_from(self, target_path, native_path, user_context=None, opts=None) -> str:
        raise NotImplementedError("upload: design step 8.")

    # helpers
    def _build_client(self, user_context) -> "_OSFClient":
        # TODO(verify): how the resolved url/token are exposed (see elabftw.py).
        config = self._resolved_config()
        return _OSFClient(config.url, config.token)

    def _resolved_config(self) -> "OSFFileSourceConfiguration":
        raise NotImplementedError("hook up resolved config accessor (see elabftw.py).")

    def _directory_entry(self, name: str, path: str) -> dict:
        # RemoteDirectory is a TypedDict -> a plain dict works at runtime.
        return {"class": "Directory", "name": name,
                "uri": f"{self.get_scheme()}://{path}", "path": path}

    def _file_entry(self, name: str, path: str, size: int = 0) -> dict:
        return {"class": "File", "name": name,
                "uri": f"{self.get_scheme()}://{path}", "path": path, "size": size}
