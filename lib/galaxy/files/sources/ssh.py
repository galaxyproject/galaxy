try:
    from fs.sshfs.sshfs import SSHFS
except ImportError:
    SSHFS = None

from typing import (
    Optional,
    Union,
)

from fsspec.implementations.sftp import SFTPFileSystem

from galaxy.files.models import FilesSourceRuntimeContext
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)
from galaxy.util.config_templates import TemplateExpansion


class SshFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    host: Union[str, TemplateExpansion]
    user: Optional[Union[str, TemplateExpansion]] = None
    passwd: Optional[Union[str, TemplateExpansion]] = None
    pkey: Optional[Union[str, TemplateExpansion]] = None
    timeout: Union[int, TemplateExpansion] = 10
    port: Union[int, TemplateExpansion] = 22
    compress: Union[bool, TemplateExpansion] = False
    config_path: Union[str, TemplateExpansion] = "~/.ssh/config"
    path: Union[str, TemplateExpansion]


class SshFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    host: str
    user: Optional[str] = None
    passwd: Optional[str] = None
    pkey: Optional[str] = None
    timeout: int = 10
    port: int = 22
    compress: bool = False
    config_path: str = "~/.ssh/config"
    path: str


class SshFilesSource(FsspecFilesSource[SshFileSourceTemplateConfiguration, SshFileSourceConfiguration]):
    plugin_type = "ssh"
    required_module = SFTPFileSystem
    required_package = "fsspec"

    template_config_class = SshFileSourceTemplateConfiguration
    resolved_config_class = SshFileSourceConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[SshFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ):
        config = context.config
        fs = SFTPFileSystem(
            host=config.host,
            username=config.user,
            password=config.passwd,
            pkey=config.pkey,
            port=config.port,
            timeout=config.timeout,
            compress=config.compress,
            config_path=config.config_path,
            **cache_options,
        )
        return fs

    def _to_filesystem_path(self, path: str) -> str:
        return f"{self.template_config.path}/{path}"


__all__ = ("SshFilesSource",)
