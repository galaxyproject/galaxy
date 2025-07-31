try:
    from fs_basespace import BASESPACEFS
except ImportError:
    BASESPACEFS = None

from typing import Optional

from . import FilesSourceProperties
from ._pyfilesystem2 import PyFilesystem2FilesSource


class BaseSpaceFileSourceConfiguration(FilesSourceProperties):
    dir_path: Optional[str] = "/"
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    access_token: Optional[str] = None
    basespace_server: Optional[str] = None


class BaseSpaceFilesSource(PyFilesystem2FilesSource):
    plugin_type = "basespace"
    required_module = BASESPACEFS
    required_package = "fs-basespace"
    config_class: BaseSpaceFileSourceConfiguration
    config: BaseSpaceFileSourceConfiguration

    def __init__(self, config: BaseSpaceFileSourceConfiguration):
        super().__init__(config)

    def _open_fs(self):
        if BASESPACEFS is None:
            raise self.required_package_exception

        return BASESPACEFS(
            dir_path=self.config.dir_path,
            client_id=self.config.client_id,
            client_secret=self.config.client_secret,
            access_token=self.config.access_token,
            basespace_server=self.config.basespace_server,
        )


__all__ = ("BaseSpaceFilesSource",)
