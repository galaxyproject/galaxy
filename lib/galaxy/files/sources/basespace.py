try:
    from fs_basespace import BASESPACEFS
except ImportError:
    BASESPACEFS = None

from typing import Union

from typing_extensions import Unpack

from . import (
    FilesSourceOptions,
    FilesSourceProperties,
)
from ._pyfilesystem2 import PyFilesystem2FilesSource


class BaseSpaceFilesSource(PyFilesystem2FilesSource):
    plugin_type = "basespace"
    required_module = BASESPACEFS
    required_package = "fs-basespace"

    def _open_fs(self, user_context=None, **kwargs: Unpack[FilesSourceOptions]):
        props = self._serialization_props(user_context)
        extra_props: Union[FilesSourceProperties, dict] = kwargs.get("extra_props") or {}
        handle = BASESPACEFS(**{**props, **extra_props})
        return handle


__all__ = ("BaseSpaceFilesSource",)
