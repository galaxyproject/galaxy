try:
    from webdavfs.webdavfs import WebDAVFS
except ImportError:
    WebDAVFS = None

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
        extra_props: Union[FilesSourceProperties, dict] = opts.extra_props or {} if opts else {}
        handle = WebDAVFS(**{**props, **extra_props})
        return handle


__all__ = ("WebDavFilesSource",)
