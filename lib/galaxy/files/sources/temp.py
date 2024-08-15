from typing import Optional

from fs.osfs import OSFS

from . import FilesSourceOptions
from ._pyfilesystem2 import PyFilesystem2FilesSource


class TempFilesSource(PyFilesystem2FilesSource):
    """A FilesSource plugin for temporary file systems.

    Used for testing and other temporary file system needs.

    Note: This plugin is not intended for production use.
    """

    plugin_type = "temp"
    required_module = OSFS

    def _open_fs(self, user_context=None, opts: Optional[FilesSourceOptions] = None):
        props = self._serialization_props(user_context)
        extra_props = opts.extra_props or {} if opts else {}
        # We use OSFS here because using TempFS or MemoryFS would wipe out the files
        # every time we instantiate a new handle, which happens on every request.
        handle = OSFS(**{**props, **extra_props})
        return handle

    def get_scheme(self) -> str:
        return "temp"


__all__ = ("TempFilesSource",)
