import logging
from typing import (
    Union,
)

from galaxy.files.models import FilesSourceRuntimeContext
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)
from galaxy.util.config_templates import TemplateExpansion

try:
    from msgraphfs import MSGDriveFS
except ImportError:
    MSGDriveFS = None


REQUIRED_PACKAGE = "msgraphfs"

log = logging.getLogger(__name__)


class OneDriveFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    tenant_id: Union[str, TemplateExpansion]
    client_id: Union[str, TemplateExpansion]
    client_secret: Union[str, TemplateExpansion]
    drive_id: Union[str, TemplateExpansion]


class OneDriveFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    tenant_id: str
    client_id: str
    client_secret: str
    drive_id: str


class OneDriveFilesSource(FsspecFilesSource[OneDriveFileSourceTemplateConfiguration, OneDriveFileSourceConfiguration]):
    plugin_type = "onedrive"
    required_module = MSGDriveFS
    required_package = REQUIRED_PACKAGE

    template_config_class = OneDriveFileSourceTemplateConfiguration
    resolved_config_class = OneDriveFileSourceConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[OneDriveFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ):
        if MSGDriveFS is None:
            raise self.required_package_exception

        config = context.config
        return MSGDriveFS(
            tenant_id=config.tenant_id,
            client_id=config.client_id,
            client_secret=config.client_secret,
            drive_id=config.drive_id,
            **cache_options,
        )

    def _adapt_entry_path(self, filesystem_path: str, config: OneDriveFileSourceConfiguration) -> str:
        if filesystem_path == "/":
            return filesystem_path
        if filesystem_path.startswith("/"):
            return filesystem_path
        return f"/{filesystem_path}"


__all__ = ("OneDriveFilesSource",)
