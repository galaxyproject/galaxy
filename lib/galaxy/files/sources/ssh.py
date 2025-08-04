try:
    from fs.sshfs.sshfs import SSHFS
except ImportError:
    SSHFS = None

from typing import Optional

from . import FilesSourceProperties
from ._pyfilesystem2 import PyFilesystem2FilesSource


class SshFileSourceConfiguration(FilesSourceProperties):
    host: str
    user: Optional[str] = None
    passwd: Optional[str] = None
    pkey: Optional[str] = None
    timeout: int = 10
    port: int = 22
    compress: bool = False
    config_path: str = "~/.ssh/config"
    path: str


class SshFilesSource(PyFilesystem2FilesSource):
    plugin_type = "ssh"
    required_module = SSHFS
    required_package = "fs.sshfs"
    configuration_class = SshFileSourceConfiguration
    config: SshFileSourceConfiguration

    def __init__(self, config: SshFileSourceConfiguration):
        super().__init__(config)

    def _open_fs(self):
        if SSHFS is None:
            raise self.required_package_exception

        handle = SSHFS(
            host=self.config.host,
            user=self.config.user,
            passwd=self.config.passwd,
            pkey=self.config.pkey,
            port=self.config.port,
            timeout=self.config.timeout,
            compress=self.config.compress,
            config_path=self.config.config_path,
        )
        if self.config.path:
            return handle.opendir(self.config.path)
        return handle


__all__ = ("SshFilesSource",)
