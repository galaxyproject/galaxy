import json
try:
    from fs.googledrivefs import GoogleDriveFS
    from google.oauth2.credentials import Credentials
except ImportError:
    GoogleDriveFS = None

from ._pyfilesystem2 import PyFilesystem2FilesSource


class GoogleDriveFilesSource(PyFilesystem2FilesSource):
    plugin_type = 'googledrive'
    required_module = GoogleDriveFS
    required_package = "fs.googledrivefs"

    def _open_fs(self, user_context):
        props = self._serialization_props(user_context)
        authorized_user_info = json.loads(props.get('credentials') or {})
        credentials = Credentials(authorized_user_info['access_token'],
                                  refresh_token=authorized_user_info['refresh_token'],
                                  token_uri="https://www.googleapis.com/oauth2/v4/token",
                                  client_id=authorized_user_info['client_id'],
                                  client_secret=authorized_user_info['client_secret'])
        handle = GoogleDriveFS(credentials)
        return handle


__all__ = ('GoogleDriveFilesSource',)
