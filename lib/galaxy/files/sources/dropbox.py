try:
    from fs.dropboxfs import DropboxFS
except ImportError:
    DropboxFS = None

from typing import (
    Optional,
    Union,
)

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
)
from . import (
    FilesSourceOptions,
    FilesSourceProperties,
)
from ._pyfilesystem2 import PyFilesystem2FilesSource


class DropboxFilesSource(PyFilesystem2FilesSource):
    plugin_type = "dropbox"
    required_module = DropboxFS
    required_package = "fs.dropboxfs"

    def _open_fs(self, user_context=None, opts: Optional[FilesSourceOptions] = None):
        props = self._serialization_props(user_context)
        extra_props: Union[FilesSourceProperties, dict] = opts.extra_props or {} if opts else {}
        # accessToken has been renamed to access_token in fs.dropboxfs 1.0
        if "accessToken" in props:
            props["access_token"] = props.pop("accessToken")
        if "oauth2_access_token" in props:
            props["access_token"] = props.pop("oauth2_access_token")

        try:
            handle = DropboxFS(**{**props, **extra_props})
            return handle
        except Exception as e:
            # This plugin might raise dropbox.dropbox_client.BadInputException
            # which is not a subclass of fs.errors.FSError
            if "OAuth2" in str(e):
                raise AuthenticationRequired(
                    f"Permission Denied. Reason: {e}. Please check your credentials in your preferences for {self.label}."
                )
            raise MessageException(f"Error connecting to Dropbox. Reason: {e}")


__all__ = ("DropboxFilesSource",)
