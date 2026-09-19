try:
    from fs_basespace import BASESPACEFS
except ImportError:
    BASESPACEFS = None


from galaxy.files.models import (
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
    FilesSourceRuntimeContext,
)
from galaxy.util.config_templates import TemplateExpansion
from ._pyfilesystem2 import PyFilesystem2FilesSource


class BaseSpaceFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    dir_path: str | TemplateExpansion | None = "/"
    client_id: str | TemplateExpansion | None = None
    client_secret: str | TemplateExpansion | None = None
    access_token: str | TemplateExpansion | None = None
    basespace_server: str | TemplateExpansion | None = None


class BaseSpaceFileSourceConfiguration(BaseFileSourceConfiguration):
    dir_path: str | None = "/"
    client_id: str | None = None
    client_secret: str | None = None
    access_token: str | None = None
    basespace_server: str | None = None


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
