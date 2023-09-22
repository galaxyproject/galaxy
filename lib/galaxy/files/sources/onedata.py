try:
    from fs.onedatafs import OnedataFS
except ImportError:
    OnedataFS = None

from typing import (
    Optional,
    Union,
)

from . import (
    FilesSourceOptions,
    FilesSourceProperties,
)
from ._pyfilesystem2 import PyFilesystem2FilesSource


class OneDataFilesSource(PyFilesystem2FilesSource):
    plugin_type = "onedata"
    required_module = OnedataFS
    required_package = "fs-onedatafs"

    def _open_fs(self, user_context=None, opts: Optional[FilesSourceOptions] = None):
        props = self._serialization_props(user_context)
        extra_props: Union[FilesSourceProperties, dict] = opts.extra_props or {} if opts else {}
        handle = OnedataFS(**{**props, **extra_props})
        return handle


__all__ = ("OneDataFilesSource",)
