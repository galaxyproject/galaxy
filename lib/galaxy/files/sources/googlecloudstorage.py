try:
    from fs_gcsfs import GCSFS
    from google.cloud.storage import Client
    from google.oauth2.credentials import Credentials
except ImportError:
    GCSFS = None

from typing import (
    Optional,
    Union,
)

from galaxy.files.models import (
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
)
from galaxy.util.config_templates import TemplateExpansion
from ._pyfilesystem2 import PyFilesystem2FilesSource


class GoogleCloudStorageFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    bucket_name: Union[str, TemplateExpansion]
    root_path: Union[str, TemplateExpansion]
    project: Optional[Union[str, TemplateExpansion]] = None
    anonymous: Optional[Union[bool, TemplateExpansion]] = True
    token: Optional[Union[str, TemplateExpansion]] = None


class GoogleCloudStorageFileSourceConfiguration(BaseFileSourceConfiguration):
    bucket_name: str
    root_path: str
    project: Optional[str] = None
    anonymous: Optional[bool] = True
    token: Optional[str] = None


class GoogleCloudStorageFilesSource(
    PyFilesystem2FilesSource[
        GoogleCloudStorageFileSourceTemplateConfiguration, GoogleCloudStorageFileSourceConfiguration
    ]
):
    plugin_type = "googlecloudstorage"
    required_module = GCSFS
    required_package = "fs-gcsfs"

    template_config_class = GoogleCloudStorageFileSourceTemplateConfiguration
    resolved_config_class = GoogleCloudStorageFileSourceConfiguration

    def _open_fs(self):
        if GCSFS is None:
            raise self.required_package_exception

        if self.config.anonymous:
            client = Client.create_anonymous_client()
        elif self.config.token:
            client = Client(project=self.config.project, credentials=Credentials(token=self.config.token))

        handle = GCSFS(bucket_name=self.config.bucket_name, root_path=self.config.root_path, retry=0, client=client)
        return handle


__all__ = ("GoogleCloudStorageFilesSource",)
