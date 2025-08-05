try:
    from webdavfs.webdavfs import WebDAVFS
except ImportError:
    WebDAVFS = None

import tempfile
from typing import (
    Annotated,
    ClassVar,
    Optional,
)

from pydantic import (
    Field,
    field_validator,
)

from . import FilesSourceProperties
from ._pyfilesystem2 import PyFilesystem2FilesSource


class WebDavFileSourceConfiguration(FilesSourceProperties):
    # Override url field to make it required for WebDAV - we keep a default but validate it's provided
    url: Annotated[
        str,
        Field(
            None,
            title="WebDAV URL",
            description="The URL of the WebDAV server. This is required for WebDAV file sources.",
        ),
    ] = None  # type: ignore[assignment]
    root: Optional[str] = None
    login: Optional[str] = None
    password: Optional[str] = None
    temp_path: Optional[str] = None
    use_temp_files: bool = True  # Default to True to avoid memory issues with large files.

    @field_validator("url")
    @classmethod
    def validate_url_required(cls, v):
        if v is None or v == "":
            raise ValueError("url is required for WebDAV file source")
        return v


class WebDavFilesSource(PyFilesystem2FilesSource):
    plugin_type = "webdav"
    required_module = WebDAVFS
    required_package = "fs.webdavfs"
    allow_key_error_on_empty_directories = True
    config_class: ClassVar[type[WebDavFileSourceConfiguration]] = WebDavFileSourceConfiguration
    config: WebDavFileSourceConfiguration

    def __init__(self, config: WebDavFileSourceConfiguration):
        super().__init__(config)

    def _open_fs(self):
        if WebDAVFS is None:
            raise self.required_package_exception

        file_sources_config = self._file_sources_config
        use_temp_files = self.config.use_temp_files
        if file_sources_config and file_sources_config.webdav_use_temp_files is not None:
            use_temp_files = file_sources_config.webdav_use_temp_files

        if use_temp_files:
            temp_path = self.config.temp_path
            if temp_path is None and file_sources_config and file_sources_config.tmp_dir:
                temp_path = file_sources_config.tmp_dir
            if temp_path is None:
                temp_path = tempfile.mkdtemp(prefix="webdav_")
            self.config.temp_path = temp_path
        self.config.use_temp_files = use_temp_files

        handle = WebDAVFS(
            url=self.config.url,
            root=self.config.root,
            login=self.config.login,
            password=self.config.password,
            temp_path=self.config.temp_path,
            use_temp_files=self.config.use_temp_files,
        )
        return handle


__all__ = ("WebDavFilesSource",)
