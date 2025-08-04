from typing_extensions import Literal

try:
    from fs.azblob.blob_fs import BlobFS
    from fs.azblob.blob_fs_v2 import BlobFSV2
except ImportError:
    BlobFS = None
    BlobFSV2 = None

from typing import (
    ClassVar,
    Optional,
)

from . import FilesSourceProperties
from ._pyfilesystem2 import PyFilesystem2FilesSource


class AzureFileSourceConfiguration(FilesSourceProperties):
    account_name: str
    container_name: str
    account_key: str
    namespace_type: Optional[Literal["hierarchical", "flat"]] = "hierarchical"


class AzureFileSource(PyFilesystem2FilesSource):
    plugin_type = "azure"
    required_module = BlobFS
    required_package = "fs-azureblob"
    config_class: ClassVar[type[AzureFileSourceConfiguration]] = AzureFileSourceConfiguration
    config: AzureFileSourceConfiguration

    def __init__(self, config: AzureFileSourceConfiguration):
        super().__init__(config)

    def _open_fs(self):
        if BlobFS is None or BlobFSV2 is None:
            raise self.required_package_exception

        if self.config.namespace_type == "flat":
            return BlobFS(
                account_name=self.config.account_name,
                container=self.config.container_name,
                account_key=self.config.account_key,
            )
        else:
            return BlobFSV2(
                account_name=self.config.account_name,
                container=self.config.container_name,
                account_key=self.config.account_key,
            )


__all__ = ("AzureFileSource",)
