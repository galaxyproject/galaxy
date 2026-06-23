try:
    from dropboxdrivefs import DropboxDriveFileSystem
except ImportError:
    DropboxDriveFileSystem = None


import posixpath
from typing import (
    Annotated,
    Optional,
    Union,
)

from pydantic import (
    AliasChoices,
    Field,
)

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
)
from galaxy.files.models import (
    FilesSourceRuntimeContext,
)
from galaxy.util.config_templates import TemplateExpansion
from ._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)

AccessTokenField = Field(
    ...,
    title="Access Token",
    description="The access token for Dropbox. You can generate one from your Dropbox app settings.",
    validation_alias=AliasChoices("oauth2_access_token", "accessToken", "access_token"),
)


class DropboxFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    access_token: Annotated[Union[str, TemplateExpansion], AccessTokenField]


class DropboxFilesSourceConfiguration(FsspecBaseFileSourceConfiguration):
    access_token: Annotated[str, AccessTokenField]


class DropboxFilesSource(FsspecFilesSource[DropboxFileSourceTemplateConfiguration, DropboxFilesSourceConfiguration]):
    plugin_type = "dropbox"
    required_module = DropboxDriveFileSystem
    required_package = "dropboxdrivefs"

    template_config_class = DropboxFileSourceTemplateConfiguration
    resolved_config_class = DropboxFilesSourceConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[DropboxFilesSourceConfiguration],
        _cache_options: CacheOptionsDictType,
    ):
        if DropboxDriveFileSystem is None:
            raise self.required_package_exception

        try:
            return DropboxDriveFileSystem(token=context.config.access_token)
        except Exception as e:
            if "OAuth2" in str(e):
                raise AuthenticationRequired(
                    f"Permission Denied. Reason: {e}. Please check your credentials in your preferences for {self.label}."
                )
            raise MessageException(f"Error connecting to Dropbox. Reason: {e}")

    def _to_filesystem_path(self, path: str, config: DropboxFilesSourceConfiguration) -> str:
        if path in ("", "/"):
            return ""
        return f"/{path.lstrip('/')}"

    def _adapt_entry_path(self, filesystem_path: str, config: DropboxFilesSourceConfiguration) -> str:
        if not filesystem_path or filesystem_path == "/":
            return "/"
        return filesystem_path if filesystem_path.startswith("/") else f"/{filesystem_path}"

    def _extract_timestamp(self, info: dict) -> Optional[str]:
        return info.get("server_modified") or info.get("client_modified") or super()._extract_timestamp(info)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[DropboxFilesSourceConfiguration],
    ):
        cache_options = self._get_cache_options(context.config)
        fs = self._open_fs(context, cache_options)
        target_path = self._to_filesystem_path(target_path, context.config)
        dirname = posixpath.dirname(target_path)
        if dirname and dirname != "/":
            self._ensure_directory(fs, dirname)
        fs.put_file(native_path, target_path)

    def _ensure_directory(self, fs, dirname: str):
        current = ""
        for part in dirname.strip("/").split("/"):
            current = f"{current}/{part}"
            if not self._is_directory(fs, current):
                fs.mkdir(current)

    def _is_directory(self, fs, path: str) -> bool:
        try:
            return fs.info(path).get("type") == "directory"
        except Exception:
            return False


__all__ = ("DropboxFilesSource",)
