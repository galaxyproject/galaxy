try:
    from fs_basespace import BASESPACEFS
except ImportError:
    BASESPACEFS = None

from ._pyfilesystem2 import PyFilesystem2FilesSource


class BaseSpaceFilesSource(PyFilesystem2FilesSource):
    plugin_type = "basespace"
    required_module = BASESPACEFS
    required_package = "fs-basespace"

    def _open_fs(self, user_context, **kwargs):
        props = self._serialization_props(user_context)
        extra_props = kwargs.get("extra_props") or {}
        handle = BASESPACEFS(**{**props, **extra_props})
        return handle


__all__ = ("BaseSpaceFilesSource",)
