try:
    from fs.ftpfs import FTPFS
except ImportError:
    FTPFS = None  # type: ignore[misc,assignment]

from ._pyfilesystem2 import PyFilesystem2FilesSource


class FtpFilesSource(PyFilesystem2FilesSource):
    plugin_type = "ftp"
    required_module = FTPFS
    required_package = "fs.ftpfs"

    def _open_fs(self, user_context):
        props = self._serialization_props(user_context)
        handle = FTPFS(**props)
        return handle


__all__ = ("FtpFilesSource",)
