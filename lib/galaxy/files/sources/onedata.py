try:
    from fs.onedatafs import OnedataFS
except ImportError:
    OnedataFS = None

from ._pyfilesystem2 import PyFilesystem2FilesSource


class OneDataFilesSource(PyFilesystem2FilesSource):
    plugin_type = "onedata"
    required_module = OnedataFS
    required_package = "fs-onedatafs"

    def _open_fs(self, user_context):
        props = self._serialization_props(user_context)
        handle = OnedataFS(**props)
        return handle


__all__ = ("OneDataFilesSource",)
