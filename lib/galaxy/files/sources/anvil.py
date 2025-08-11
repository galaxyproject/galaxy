try:
    from anvilfs.anvilfs import AnVILFS
except ImportError:
    AnVILFS = None
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


class AnVILFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    namespace: Union[str, TemplateExpansion]
    workspace: Union[str, TemplateExpansion]
    api_url: Union[str, TemplateExpansion, None] = None
    on_anvil: Union[bool, TemplateExpansion, None] = False
    drs_url: Union[str, TemplateExpansion, None] = None


class AnVILFileSourceConfiguration(BaseFileSourceConfiguration):
    namespace: str
    workspace: str
    api_url: Optional[str] = None
    on_anvil: Optional[bool] = False
    drs_url: Optional[str] = None


class AnVILFilesSource(PyFilesystem2FilesSource[AnVILFileSourceTemplateConfiguration, AnVILFileSourceConfiguration]):
    plugin_type = "anvil"
    required_module = AnVILFS
    required_package = "fs.anvilfs"

    template_config_class = AnVILFileSourceTemplateConfiguration
    resolved_config_class = AnVILFileSourceConfiguration

    def _open_fs(self, context: FilesSourceRuntimeContext[AnVILFileSourceConfiguration]):
        if AnVILFS is None:
            raise self.required_package_exception

        config = context.config
        handle = AnVILFS(
            namespace=config.namespace,
            workspace=config.workspace,
            api_url=config.api_url,
            on_anvil=config.on_anvil,
            drs_url=config.drs_url,
        )
        return handle


__all__ = ("AnVILFilesSource",)
