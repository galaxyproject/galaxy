try:
    from fs_gcsfs import GCSFS
    from google.cloud.storage import Client
    from google.oauth2 import service_account
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
    FilesSourceRuntimeContext,
)
from galaxy.util.config_templates import TemplateExpansion
from ._pyfilesystem2 import PyFilesystem2FilesSource


class GoogleCloudStorageFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    bucket_name: Union[str, TemplateExpansion]
    root_path: Union[str, TemplateExpansion, None] = None
    project: Union[str, TemplateExpansion, None] = None
    anonymous: Union[bool, TemplateExpansion, None] = True
    service_account_json: Union[str, TemplateExpansion, None] = None
    token: Union[str, TemplateExpansion, None] = None
    token_uri: Union[str, TemplateExpansion, None] = None
    client_id: Union[str, TemplateExpansion, None] = None
    client_secret: Union[str, TemplateExpansion, None] = None
    refresh_token: Union[str, TemplateExpansion, None] = None


class GoogleCloudStorageFileSourceConfiguration(BaseFileSourceConfiguration):
    bucket_name: str
    root_path: Optional[str] = None
    project: Optional[str] = None
    anonymous: Optional[bool] = True
    service_account_json: Optional[str] = None
    token: Optional[str] = None
    token_uri: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token: Optional[str] = None


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

    def _open_fs(self, context: FilesSourceRuntimeContext[GoogleCloudStorageFileSourceConfiguration]):
        if GCSFS is None:
            raise self.required_package_exception

        config = context.config
        if config.anonymous:
            client = Client.create_anonymous_client()
        elif config.service_account_json:
            credentials = service_account.Credentials.from_service_account_file(config.service_account_json)
            client = Client(project=config.project, credentials=credentials)
        elif config.token:
            client = Client(
                project=config.project,
                credentials=Credentials(
                    token=config.token,
                    token_uri=config.token_uri,
                    client_id=config.client_id,
                    client_secret=config.client_secret,
                    refresh_token=config.refresh_token,
                ),
            )

        handle = GCSFS(bucket_name=config.bucket_name, root_path=config.root_path or "", retry=0, client=client)
        return handle


__all__ = ("GoogleCloudStorageFilesSource",)
