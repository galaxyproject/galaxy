try:
    from dropboxfs.dropboxfs import DropboxFS
except ImportError:
    DropboxFS = None

from typing import Union

from typing_extensions import Unpack

from . import (
    FilesSourceOptions,
    FilesSourceProperties,
)
from ._pyfilesystem2 import PyFilesystem2FilesSource


class DropboxFilesSource(PyFilesystem2FilesSource):
    plugin_type = "dropbox"
    required_module = DropboxFS
    required_package = "fs.dropboxfs"

    def _open_fs(self, user_context=None, **kwargs: Unpack[FilesSourceOptions]):
        props = self._serialization_props(user_context)
        extra_props: Union[FilesSourceProperties, dict] = kwargs.get("extra_props") or {}
        handle = DropboxFS(**{**props, **extra_props})
        return handle


__all__ = ("DropboxFilesSource",)
