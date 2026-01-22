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
            keepalive=0,
        )
        return handle

    def _to_filesystem_path(self, path: str, config: SshFileSourceConfiguration) -> str:
        base = config.path.rstrip("/")
        relative = path.lstrip("/")
        if not relative:
            return base or "/"
        return f"{base}/{relative}"

    def _adapt_entry_path(self, filesystem_path: str, config: SshFileSourceConfiguration) -> str:
        base = config.path.rstrip("/")
        if base and filesystem_path.startswith(base):
            virtual_path = filesystem_path[len(base) :]
            if not virtual_path:
                return "/"
            if not virtual_path.startswith("/"):
                virtual_path = f"/{virtual_path}"
            return virtual_path
        return filesystem_path


__all__ = ("SshFilesSource",)
