try:
    from fs.googledrivefs import GoogleDriveFS
    from google.oauth2.credentials import Credentials
except ImportError:
    GoogleDriveFS = None

from ._pyfilesystem2 import PyFilesystem2FilesSource


class GoogleDriveFilesSource(PyFilesystem2FilesSource):
    plugin_type = "googledrive"
    required_module = GoogleDriveFS
    required_package = "fs.googledrivefs"

    def _open_fs(self, user_context):
        props = self._serialization_props(user_context)
        credentials = Credentials(**props)
        handle = GoogleDriveFS(credentials)
        return handle


__all__ = ("GoogleDriveFilesSource",)
