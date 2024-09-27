try:
    from webdavfs.webdavfs import WebDAVFS
except ImportError:
    WebDAVFS = None

from typing import (
    cast,
    Optional,
    Union,
)

from typing_extensions import NotRequired

from typing_extensions import NotRequired

from . import (
    FilesSourceOptions,
    FilesSourceProperties,
)
from ._pyfilesystem2 import PyFilesystem2FilesSource


class WebDavFilesSourceProperties(FilesSourceProperties, total=False):
    use_temp_files: NotRequired[Optional[bool]]
    temp_path: NotRequired[Optional[str]]


class WebDavFilesSource(PyFilesystem2FilesSource):
    plugin_type = "webdav"
    required_module = WebDAVFS
    required_package = "fs.webdavfs"
    allow_key_error_on_empty_directories = True

    def _open_fs(self, user_context=None, opts: Optional[FilesSourceOptions] = None):
        props = cast(WebDavFilesSourceProperties, self._serialization_props(user_context))
        file_sources_config = self._file_sources_config
        use_temp_files = props.pop("use_temp_files", None)
        if use_temp_files is None and file_sources_config and file_sources_config.webdav_use_temp_files is not None:
            use_temp_files = file_sources_config.webdav_use_temp_files
        if use_temp_files is None:
            # Default to True to avoid memory issues with large files.
            use_temp_files = True

        if use_temp_files:
            temp_path = props.get("temp_path")
            if temp_path is None and file_sources_config and file_sources_config.tmp_dir:
                temp_path = file_sources_config.tmp_dir
            if temp_path is None:
                temp_path = tempfile.mkdtemp(prefix="webdav_")
            props["temp_path"] = temp_path
        props["use_temp_files"] = use_temp_files
        extra_props: Union[FilesSourceProperties, dict] = opts.extra_props or {} if opts else {}
        handle = WebDAVFS(**{**props, **extra_props})
        return handle


__all__ = ("WebDavFilesSource",)
