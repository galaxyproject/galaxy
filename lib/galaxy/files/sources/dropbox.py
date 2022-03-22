try:
    from dropboxfs.dropboxfs import DropboxFS
except ImportError:
    DropboxFS = None

from ._pyfilesystem2 import PyFilesystem2FilesSource


class DropboxFilesSource(PyFilesystem2FilesSource):
    plugin_type = "dropbox"
    required_module = DropboxFS
    required_package = "fs.dropboxfs"

    def _open_fs(self, user_context):
        props = self._serialization_props(user_context)
        handle = DropboxFS(**props)
        return handle


__all__ = ("DropboxFilesSource",)
