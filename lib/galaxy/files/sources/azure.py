from typing_extensions import Literal

try:
    from fs.azblob.blob_fs import BlobFS
    from fs.azblob.blob_fs_v2 import BlobFSV2
except ImportError:
    BlobFS = None
    BlobFSV2 = None

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

AzureNamespaceType = Literal["hierarchical", "flat"]


class AzureFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    account_name: Union[str, TemplateExpansion]
    container_name: Union[str, TemplateExpansion]
    account_key: Union[str, TemplateExpansion]
    namespace_type: Optional[AzureNamespaceType] = "hierarchical"


class AzureFileSourceConfiguration(BaseFileSourceConfiguration):
    account_name: str
    container_name: str
    account_key: str
    namespace_type: Optional[AzureNamespaceType] = "hierarchical"


class AzureFileSource(PyFilesystem2FilesSource[AzureFileSourceTemplateConfiguration, AzureFileSourceConfiguration]):
    plugin_type = "azure"
    required_module = BlobFS
    required_package = "fs-azureblob"

    template_config_class = AzureFileSourceTemplateConfiguration
    resolved_config_class = AzureFileSourceConfiguration

    def _open_fs(self, context: FilesSourceRuntimeContext[AzureFileSourceConfiguration]):
        config = context.config
        if BlobFS is None or BlobFSV2 is None:
            raise self.required_package_exception

        if config.namespace_type == "flat":
            return BlobFS(
                account_name=config.account_name,
                container=config.container_name,
                account_key=config.account_key,
            )
        else:
            return BlobFSV2(
                account_name=config.account_name,
                container=config.container_name,
                account_key=config.account_key,
            )


__all__ = ("AzureFileSource",)
