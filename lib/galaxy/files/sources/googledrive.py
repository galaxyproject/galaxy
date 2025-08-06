try:
    from fs.googledrivefs.googledrivefs import GoogleDriveFS
    from google.oauth2.credentials import Credentials
except ImportError:
    GoogleDriveFS = None


from typing import (
    Annotated,
    Union,
)

from pydantic import (
    AliasChoices,
    Field,
)

from galaxy.files.models import (
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
)
from galaxy.util.config_templates import TemplateExpansion
from ._pyfilesystem2 import PyFilesystem2FilesSource

AccessTokenField = Field(
    ...,
    validation_alias=AliasChoices("oauth2_access_token", "accessToken", "access_token"),
)


class GoogleDriveFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    access_token: Annotated[Union[str, TemplateExpansion], AccessTokenField]


class GoogleDriveFilesSourceConfiguration(BaseFileSourceConfiguration):
    access_token: Annotated[str, AccessTokenField]


class GoogleDriveFilesSource(
    PyFilesystem2FilesSource[GoogleDriveFileSourceTemplateConfiguration, GoogleDriveFilesSourceConfiguration]
):
    plugin_type = "googledrive"
    required_module = GoogleDriveFS
    required_package = "fs.googledrivefs"

    template_config_class = GoogleDriveFileSourceTemplateConfiguration
    resolved_config_class = GoogleDriveFilesSourceConfiguration

    def _open_fs(self):
        if GoogleDriveFS is None:
            raise self.required_package_exception
        credentials = Credentials(token=self.config.access_token)
        handle = GoogleDriveFS(credentials)
        return handle


__all__ = ("GoogleDriveFilesSource",)
