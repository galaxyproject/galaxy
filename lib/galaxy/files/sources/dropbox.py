try:
    from fs.dropboxfs.dropboxfs import DropboxFS
except ImportError:
    DropboxFS = None  # type: ignore[misc,assignment]


from typing import Annotated

from pydantic import (
    AliasChoices,
    Field,
)

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
)
from . import FilesSourceProperties
from ._pyfilesystem2 import PyFilesystem2FilesSource


class DropboxFilesSourceConfiguration(FilesSourceProperties):
    access_token: Annotated[
        str,
        Field(
            ...,
            title="Access Token",
            description="The access token for Dropbox. You can generate one from your Dropbox app settings.",
            validation_alias=AliasChoices("oauth2_access_token", "accessToken", "access_token"),
        ),
    ]


class DropboxFilesSource(PyFilesystem2FilesSource):
    plugin_type = "dropbox"
    required_module = DropboxFS
    required_package = "fs.dropboxfs"
    config_class: DropboxFilesSourceConfiguration
    config: DropboxFilesSourceConfiguration

    def __init__(self, config: DropboxFilesSourceConfiguration):
        super().__init__(config)

    def _open_fs(self):
        if DropboxFS is None:
            raise self.required_package_exception

        try:
            return DropboxFS(access_token=self.config.access_token)
        except Exception as e:
            # This plugin might raise dropbox.dropbox_client.BadInputException
            # which is not a subclass of fs.errors.FSError
            if "OAuth2" in str(e):
                raise AuthenticationRequired(
                    f"Permission Denied. Reason: {e}. Please check your credentials in your preferences for {self.label}."
                )
            raise MessageException(f"Error connecting to Dropbox. Reason: {e}")


__all__ = ("DropboxFilesSource",)
