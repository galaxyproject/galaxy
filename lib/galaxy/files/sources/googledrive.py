try:
    from gdrive_fsspec import GoogleDriveFileSystem
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
except ImportError:
    GoogleDriveFileSystem = None


from datetime import datetime
from typing import (
    Annotated,
)

from fsspec import AbstractFileSystem
from pydantic import (
    AliasChoices,
    Field,
)

from galaxy.files.models import FilesSourceRuntimeContext
from galaxy.util.config_templates import TemplateExpansion
from ._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)

GalaxyGoogleDriveFileSystem: type[AbstractFileSystem] | None

if GoogleDriveFileSystem is not None:

    class _GalaxyGoogleDriveFileSystem(GoogleDriveFileSystem):
        def __init__(self, access_token: str, **kwargs):
            self._galaxy_credentials = Credentials(token=access_token)
            super().__init__(token="galaxy", **kwargs)

        def connect(self, method=None):
            if method == "galaxy":
                srv = build("drive", "v3", credentials=self._galaxy_credentials)
                self.srv = srv
                self.files = srv.files()
            else:
                super().connect(method=method)

        def put_file(self, lpath, rpath, *args, **kwargs):
            parent = self._parent(str(rpath))
            if parent not in self.dircache:
                self.dircache[parent] = []
            return super().put_file(lpath, rpath, *args, **kwargs)

    GalaxyGoogleDriveFileSystem = _GalaxyGoogleDriveFileSystem

else:
    GalaxyGoogleDriveFileSystem = None

AccessTokenField = Field(
    ...,
    validation_alias=AliasChoices("oauth2_access_token", "accessToken", "access_token", "token"),
)


class GoogleDriveFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    access_token: Annotated[str | TemplateExpansion, AccessTokenField]


class GoogleDriveFilesSourceConfiguration(FsspecBaseFileSourceConfiguration):
    access_token: Annotated[str, AccessTokenField]


class GoogleDriveFilesSource(
    FsspecFilesSource[GoogleDriveFileSourceTemplateConfiguration, GoogleDriveFilesSourceConfiguration]
):
    plugin_type = "googledrive"
    required_module = GalaxyGoogleDriveFileSystem
    required_package = "gdrive_fsspec"

    template_config_class = GoogleDriveFileSourceTemplateConfiguration
    resolved_config_class = GoogleDriveFilesSourceConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[GoogleDriveFilesSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ):
        if GalaxyGoogleDriveFileSystem is None:
            raise self.required_package_exception
        return GalaxyGoogleDriveFileSystem(access_token=context.config.access_token, **cache_options)

    def _to_filesystem_path(self, path: str, config: GoogleDriveFilesSourceConfiguration) -> str:
        if path in ("", "/"):
            return ""
        return path.lstrip("/")

    def _adapt_entry_path(self, filesystem_path: str, config: GoogleDriveFilesSourceConfiguration) -> str:
        if not filesystem_path or filesystem_path == "/":
            return "/"
        return filesystem_path if filesystem_path.startswith("/") else f"/{filesystem_path}"

    def _extract_timestamp(self, info: dict):
        timestamp = info.get("modifiedTime") or info.get("createdTime") or super()._extract_timestamp(info)
        if isinstance(timestamp, str):
            return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return timestamp


__all__ = ("GoogleDriveFilesSource",)
