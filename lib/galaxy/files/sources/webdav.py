try:
    from webdavfs.webdavfs import WebDAVFS
except ImportError:
    WebDAVFS = None

import tempfile
from typing import (
    Optional,
    Union,
)

from . import (
    FilesSourceOptions,
    FilesSourceProperties,
)
from ._pyfilesystem2 import PyFilesystem2FilesSource


class WebDavFilesSource(PyFilesystem2FilesSource):
    plugin_type = "webdav"
    required_module = WebDAVFS
    required_package = "fs.webdavfs"

    def _open_fs(self, user_context=None, opts: Optional[FilesSourceOptions] = None):
        props = self._serialization_props(user_context)
        use_temp_files = props.pop("use_temp_files", None)
        if use_temp_files is None:
            # Default to True to avoid memory issues with large files.
            props["use_temp_files"] = True
            props["temp_path"] = props.get("temp_path", tempfile.TemporaryDirectory(prefix="webdav_"))
        extra_props: Union[FilesSourceProperties, dict] = opts.extra_props or {} if opts else {}
        handle = WebDAVFS(**{**props, **extra_props})
        return handle


__all__ = ("WebDavFilesSource",)
