from typing import (
    Optional,
    Union,
)

# file source requires conditional dependency smbclient
try:
    from fsspec.implementations.smb import SMBFileSystem
except ModuleNotFoundError:
    SMBFileSystem = None

from galaxy.files.models import FilesSourceRuntimeContext
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)
from galaxy.util.config_templates import TemplateExpansion


class SmbFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    domain: Optional[Union[str, TemplateExpansion]] = None
    host: Union[str, TemplateExpansion]
    user: Optional[Union[str, TemplateExpansion]] = None
    passwd: Optional[Union[str, TemplateExpansion]] = None
    port: Union[int, TemplateExpansion] = 445
    encrypt: Union[bool, TemplateExpansion] = False
    share_access: Optional[Union[str, TemplateExpansion]] = None

    path: Union[str, TemplateExpansion]


class SmbFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    domain: Optional[str] = None
    host: str
    user: Optional[str] = None
    passwd: Optional[str] = None
    port: int = 445
    encrypt: bool = False
    share_access: Optional[str] = None
    path: str


class SmbFilesSource(FsspecFilesSource[SmbFileSourceTemplateConfiguration, SmbFileSourceConfiguration]):
    plugin_type = "smb"
    required_module = SMBFileSystem
    required_package = "fsspec"

    template_config_class = SmbFileSourceTemplateConfiguration
    resolved_config_class = SmbFileSourceConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[SmbFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ):
        cfg = context.config
        # Build username with optional domain
        username = f"{cfg.domain}\\{cfg.user}" if cfg.domain and cfg.user else cfg.user
        # Determine share access: explicit config overrides, otherwise infer from writable flag
        share_access = cfg.share_access
        if share_access is None:
            # Allow read access for other handles if we only read, otherwise exclusive
            share_access = "r" if getattr(cfg, "writable", False) else ""
        return SMBFileSystem(
            host=cfg.host,
            port=cfg.port,
            username=username,
            password=cfg.passwd,
            encrypt=cfg.encrypt,
            share_access=share_access,
        )

    def _to_filesystem_path(self, path: str) -> str:
        base = self.template_config.path.rstrip("/")
        rel = path.lstrip("/")
        return f"{base}/{rel}" if rel else base or "/"

    def _adapt_entry_path(self, filesystem_path: str) -> str:
        base = self.template_config.path.rstrip("/")
        if base and filesystem_path.startswith(base):
            vp = filesystem_path[len(base) :]
            return vp if vp.startswith("/") else f"/{vp}"
        return filesystem_path


__all__ = ("SmbFilesSource",)
