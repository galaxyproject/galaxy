try:
    from anvilfs.anvilfs import AnVILFS
except ImportError:
    AnVILFS = None
from typing import (
    Optional,
    Union,
)

from . import (
    FilesSourceOptions,
    FilesSourceProperties,
)
from ._pyfilesystem2 import PyFilesystem2FilesSource


class AnVILFilesSource(PyFilesystem2FilesSource):
    plugin_type = "anvil"
    required_module = AnVILFS
    required_package = "fs.anvilfs"

    def _open_fs(self, user_context=None, opts: Optional[FilesSourceOptions] = None):
        props = self._serialization_props(user_context)
        extra_props: Union[FilesSourceProperties, dict] = opts.extra_props or {} if opts else {}
        handle = AnVILFS(**{**props, **extra_props})
        return handle


__all__ = ("AnVILFilesSource",)
