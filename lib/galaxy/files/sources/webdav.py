try:
    from webdavfs.webdavfs import WebDAVFS
except ImportError:
    WebDAVFS = None

from typing import Union

from typing_extensions import Unpack

from . import (
    FilesSourceOptions,
    FilesSourceProperties,
)
from ._pyfilesystem2 import PyFilesystem2FilesSource


class WebDavFilesSource(PyFilesystem2FilesSource):
    plugin_type = "webdav"
    required_module = WebDAVFS
    required_package = "fs.webdavfs"

    def _open_fs(self, user_context=None, **kwargs: Unpack[FilesSourceOptions]):
        props = self._serialization_props(user_context)
        extra_props: Union[FilesSourceProperties, dict] = kwargs.get("extra_props") or {}
        handle = WebDAVFS(**{**props, **extra_props})
        return handle


__all__ = ("WebDavFilesSource",)
