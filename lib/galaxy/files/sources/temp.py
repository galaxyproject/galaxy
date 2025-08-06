from typing import Union

from fs.osfs import OSFS

from galaxy.files.models import (
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
)
from galaxy.util.config_templates import TemplateExpansion
from ._pyfilesystem2 import PyFilesystem2FilesSource


class TempFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    root_path: Union[str, TemplateExpansion]


class TempFileSourceConfiguration(BaseFileSourceConfiguration):
    root_path: str


class TempFilesSource(PyFilesystem2FilesSource[TempFileSourceTemplateConfiguration, TempFileSourceConfiguration]):
    """A FilesSource plugin for temporary file systems.

    Used for testing and other temporary file system needs.

    Note: This plugin is not intended for production use.
    """

    plugin_type = "temp"
    required_module = OSFS
    required_package = "fs.osfs"

    template_config_class = TempFileSourceTemplateConfiguration
    resolved_config_class = TempFileSourceConfiguration

    def _open_fs(self):
        if OSFS is None:
            raise self.required_package_exception

        return OSFS(root_path=self.config.root_path)

    def get_scheme(self) -> str:
        return "temp"


__all__ = ("TempFilesSource",)
