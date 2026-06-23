try:
    from fs_basespace import BASESPACEFS
except ImportError:
    BASESPACEFS = None

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


class BaseSpaceFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    dir_path: Union[str, TemplateExpansion, None] = "/"
    client_id: Union[str, TemplateExpansion, None] = None
    client_secret: Union[str, TemplateExpansion, None] = None
    access_token: Union[str, TemplateExpansion, None] = None
    basespace_server: Union[str, TemplateExpansion, None] = None


class BaseSpaceFileSourceConfiguration(BaseFileSourceConfiguration):
    dir_path: Optional[str] = "/"
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    access_token: Optional[str] = None
    basespace_server: Optional[str] = None


class BaseSpaceFilesSource(
    PyFilesystem2FilesSource[BaseSpaceFileSourceTemplateConfiguration, BaseSpaceFileSourceConfiguration]
):
    plugin_type = "basespace"
    required_module = BASESPACEFS
    required_package = "fs-basespace"

    template_config_class = BaseSpaceFileSourceTemplateConfiguration
    resolved_config_class = BaseSpaceFileSourceConfiguration

    def _open_fs(self, context: FilesSourceRuntimeContext[BaseSpaceFileSourceConfiguration]):
        if BASESPACEFS is None:
            raise self.required_package_exception

        config = context.config
        return BASESPACEFS(
            dir_path=config.dir_path,
            client_id=config.client_id,
            client_secret=config.client_secret,
            access_token=config.access_token,
            basespace_server=config.basespace_server,
        )


__all__ = ("BaseSpaceFilesSource",)
