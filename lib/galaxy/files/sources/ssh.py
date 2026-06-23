from io import StringIO
from typing import (
    Optional,
    TYPE_CHECKING,
    Union,
)

try:
    from fsspec.implementations.sftp import SFTPFileSystem
    from paramiko.ecdsakey import ECDSAKey
    from paramiko.ed25519key import Ed25519Key
    from paramiko.rsakey import RSAKey
except ImportError:
    SFTPFileSystem = None
    if TYPE_CHECKING:
        from paramiko.ecdsakey import ECDSAKey
        from paramiko.ed25519key import Ed25519Key
        from paramiko.rsakey import RSAKey

from galaxy.exceptions import AuthenticationFailed
from galaxy.files.models import FilesSourceRuntimeContext
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)
from galaxy.util.config_templates import TemplateExpansion


def _parse_private_key(private_key: str, password: Optional[str]):
    # Paramiko cannot autodetect the key type, so try the supported key classes.
    for pkey_class in (RSAKey, ECDSAKey, Ed25519Key):
        try:
            with StringIO(private_key) as pkey_file:
                return pkey_class.from_private_key(pkey_file, password=password)
        except Exception:
            continue

    return None


class SshFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    host: Union[str, TemplateExpansion]
    user: Optional[Union[str, TemplateExpansion]] = None
    passwd: Optional[Union[str, TemplateExpansion]] = None
    pkey: Optional[Union[str, TemplateExpansion]] = None
    timeout: Union[int, TemplateExpansion] = 10
    port: Union[int, TemplateExpansion] = 22
    compress: Union[bool, TemplateExpansion] = False
    path: Union[str, TemplateExpansion]


class SshFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    host: str
    user: Optional[str] = None
    passwd: Optional[str] = None
    pkey: Optional[str] = None
    timeout: int = 10
    port: int = 22
    compress: bool = False
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
        cache_options: CacheOptionsDictType,  # Ignored because fsspec's SFTPFileSystem does not support caching options.
    ):
        if SFTPFileSystem is None:
            raise self.required_package_exception

        config = context.config
        pkey = None
        password = config.passwd
        if config.pkey:
            pkey = _parse_private_key(config.pkey, config.passwd)
            if pkey is None:
                raise AuthenticationFailed("Invalid or unsupported SSH private key provided.")
            password = None

        fs = SFTPFileSystem(
            host=config.host,
            username=config.user,
            password=password,
            pkey=pkey,
            port=config.port,
            timeout=config.timeout,
            compress=config.compress,
        )
        return fs

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
