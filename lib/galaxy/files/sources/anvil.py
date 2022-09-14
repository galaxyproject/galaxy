try:
    from anvilfs.anvilfs import AnVILFS
except ImportError:
    AnVILFS = None
from ._pyfilesystem2 import PyFilesystem2FilesSource


class AnVILFilesSource(PyFilesystem2FilesSource):
    plugin_type = "anvil"
    required_module = AnVILFS
    required_package = "fs.anvilfs"

    def _open_fs(self, user_context):
        props = self._serialization_props(user_context)
        handle = AnVILFS(**props)
        return handle


__all__ = ("AnVILFilesSource",)
