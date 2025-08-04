try:
    from fs.googledrivefs.googledrivefs import GoogleDriveFS
    from google.oauth2.credentials import Credentials
except ImportError:
    GoogleDriveFS = None


from typing import (
    Annotated,
    ClassVar,
)

from pydantic import (
    AliasChoices,
    Field,
)

from . import FilesSourceProperties
from ._pyfilesystem2 import PyFilesystem2FilesSource


class GoogleDriveFilesSourceConfiguration(FilesSourceProperties):
    access_token: Annotated[
        str,
        Field(
            ...,
            validation_alias=AliasChoices("oauth2_access_token", "accessToken", "access_token"),
        ),
    ]


class GoogleDriveFilesSource(PyFilesystem2FilesSource):
    plugin_type = "googledrive"
    required_module = GoogleDriveFS
    required_package = "fs.googledrivefs"
    config_class: ClassVar[type[GoogleDriveFilesSourceConfiguration]] = GoogleDriveFilesSourceConfiguration
    config: GoogleDriveFilesSourceConfiguration

    def __init__(self, config: GoogleDriveFilesSourceConfiguration):
        super().__init__(config)

    def _open_fs(self):
        if GoogleDriveFS is None:
            raise self.required_package_exception
        credentials = Credentials(token=self.config.access_token)
        handle = GoogleDriveFS(credentials)
        return handle


__all__ = ("GoogleDriveFilesSource",)
