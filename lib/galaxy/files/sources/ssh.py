try:
    from fs.sshfs.sshfs import SSHFS
except ImportError:
    SSHFS = None

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


class SshFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    host: Union[str, TemplateExpansion]
    user: Optional[Union[str, TemplateExpansion]] = None
    passwd: Optional[Union[str, TemplateExpansion]] = None
    pkey: Optional[Union[str, TemplateExpansion]] = None
    timeout: Union[int, TemplateExpansion] = 10
    port: Union[int, TemplateExpansion] = 22
    compress: Union[bool, TemplateExpansion] = False
    config_path: Union[str, TemplateExpansion] = "~/.ssh/config"
    path: Union[str, TemplateExpansion]


class SshFileSourceConfiguration(BaseFileSourceConfiguration):
    host: str
    user: Optional[str] = None
    passwd: Optional[str] = None
    pkey: Optional[str] = None
    timeout: int = 10
    port: int = 22
    compress: bool = False
    config_path: str = "~/.ssh/config"
    path: str


class SshFilesSource(PyFilesystem2FilesSource[SshFileSourceTemplateConfiguration, SshFileSourceConfiguration]):
    plugin_type = "ssh"
    required_module = SSHFS
    required_package = "fs.sshfs"

    template_config_class = SshFileSourceTemplateConfiguration
    resolved_config_class = SshFileSourceConfiguration

    def _open_fs(self, context: FilesSourceRuntimeContext[SshFileSourceConfiguration]):
        if SSHFS is None:
            raise self.required_package_exception

        config = context.config
        handle = SSHFS(
            host=config.host,
            user=config.user,
            passwd=config.passwd,
            pkey=config.pkey,
            port=config.port,
            timeout=config.timeout,
            compress=config.compress,
            config_path=config.config_path,
        )
        if config.path:
            return handle.opendir(config.path)
        return handle


__all__ = ("SshFilesSource",)
