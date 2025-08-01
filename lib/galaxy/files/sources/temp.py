from fs.osfs import OSFS

from . import FilesSourceProperties
from ._pyfilesystem2 import PyFilesystem2FilesSource


class TempFileSourceConfiguration(FilesSourceProperties):
    root_path: str


class TempFilesSource(PyFilesystem2FilesSource):
    """A FilesSource plugin for temporary file systems.

    Used for testing and other temporary file system needs.

    Note: This plugin is not intended for production use.
    """

    plugin_type = "temp"
    required_module = OSFS
    required_package = "fs.osfs"
    configuration_class = TempFileSourceConfiguration
    config: TempFileSourceConfiguration

    def __init__(self, config: TempFileSourceConfiguration):
        super().__init__(config)

    def _open_fs(self):
        if OSFS is None:
            raise self.required_package_exception

        return OSFS(root_path=self.config.root_path)

    def get_scheme(self) -> str:
        return "temp"


__all__ = ("TempFilesSource",)
