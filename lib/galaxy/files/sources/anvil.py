try:
    from anvilfs.anvilfs import AnVILFS
except ImportError:
    AnVILFS = None
from typing import (
    ClassVar,
    Optional,
)

from . import FilesSourceProperties
from ._pyfilesystem2 import PyFilesystem2FilesSource


class AnVILFileSourceConfiguration(FilesSourceProperties):
    namespace: str
    workspace: str
    api_url: Optional[str] = None
    on_anvil: Optional[bool] = False
    drs_url: Optional[str] = None


class AnVILFilesSource(PyFilesystem2FilesSource):
    plugin_type = "anvil"
    required_module = AnVILFS
    required_package = "fs.anvilfs"
    config_class: ClassVar[type[AnVILFileSourceConfiguration]] = AnVILFileSourceConfiguration
    config: AnVILFileSourceConfiguration

    def __init__(self, config: AnVILFileSourceConfiguration):
        super().__init__(config)

    def _open_fs(self):
        if AnVILFS is None:
            raise self.required_package_exception

        handle = AnVILFS(
            namespace=self.config.namespace,
            workspace=self.config.workspace,
            api_url=self.config.api_url,
            on_anvil=self.config.on_anvil,
            drs_url=self.config.drs_url,
        )
        return handle


__all__ = ("AnVILFilesSource",)
