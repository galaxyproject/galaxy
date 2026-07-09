import os
import posixpath
from galaxy.files.models import (
    FilesSourceRuntimeContext,
)
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)
from galaxy.util.config_templates import TemplateExpansion

try:
    from irods.session import iRODSSession
    from mangofs import IRODSFileSystem
except ImportError:
    iRODSSession = None
    IRODSFileSystem = None


class IrodsFsspecFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    host: str | TemplateExpansion
    port: int | TemplateExpansion = 1247
    username: str | TemplateExpansion
    password: str | TemplateExpansion
    zone: str | TemplateExpansion
    root: str | TemplateExpansion | None = None
    timeout: int | TemplateExpansion = 30
    refresh_time: int | TemplateExpansion = 300
    client_server_negotiation: str | TemplateExpansion | None = None
    client_server_policy: str | TemplateExpansion | None = None
    encryption_algorithm: str | TemplateExpansion | None = None
    encryption_key_size: int | TemplateExpansion | None = None
    encryption_num_hash_rounds: int | TemplateExpansion | None = None
    encryption_salt_size: int | TemplateExpansion | None = None
    ssl_verify_server: str | TemplateExpansion | None = None
    ssl_ca_certificate_file: str | TemplateExpansion | None = None
    resource: str | TemplateExpansion | None = None


class IrodsFsspecFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    host: str
    port: int = 1247
    username: str
    password: str
    zone: str
    root: str | None = None
    timeout: int = 30
    refresh_time: int = 300
    client_server_negotiation: str | None = None
    client_server_policy: str | None = None
    encryption_algorithm: str | None = None
    encryption_key_size: int | None = None
    encryption_num_hash_rounds: int | None = None
    encryption_salt_size: int | None = None
    ssl_verify_server: str | None = None
    ssl_ca_certificate_file: str | None = None
    resource: str | None = None


class IrodsFsspecFilesSource(
    FsspecFilesSource[IrodsFsspecFileSourceTemplateConfiguration, IrodsFsspecFileSourceConfiguration]
):
    plugin_type = "irods"
    required_module = IRODSFileSystem
    required_package = "mangofs"

    template_config_class = IrodsFsspecFileSourceTemplateConfiguration
    resolved_config_class = IrodsFsspecFileSourceConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[IrodsFsspecFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ):
        if IRODSFileSystem is None or iRODSSession is None:
            raise self.required_package_exception

        session = self._open_session(context.config)
        return IRODSFileSystem(session=session, **cache_options)

    def _open_session(self, config: IrodsFsspecFileSourceConfiguration):
        session_kwargs = {
            "host": config.host,
            "port": config.port,
            "user": config.username,
            "password": config.password,
            "zone": config.zone,
            "refresh_time": config.refresh_time,
            "client_server_negotiation": config.client_server_negotiation,
            "client_server_policy": config.client_server_policy,
            "encryption_algorithm": config.encryption_algorithm,
            "encryption_key_size": config.encryption_key_size,
            "encryption_num_hash_rounds": config.encryption_num_hash_rounds,
            "encryption_salt_size": config.encryption_salt_size,
            "ssl_verify_server": config.ssl_verify_server,
            "ssl_ca_certificate_file": config.ssl_ca_certificate_file,
        }
        if (ssl_context := getattr(config, "ssl_context", None)) is not None:
            session_kwargs["ssl_context"] = ssl_context

        session = iRODSSession(**session_kwargs)
        session.connection_timeout = config.timeout
        if config.resource:
            session.default_resource = config.resource
        return session

    def _to_filesystem_path(self, path: str, config: IrodsFsspecFileSourceConfiguration) -> str:
        root = self._normalized_root(config)
        path = path or "/"
        if path.startswith("irods://"):
            return path
        if path == "/":
            return root
        return posixpath.join(root, path.lstrip("/"))

    def _adapt_entry_path(self, filesystem_path: str, config: IrodsFsspecFileSourceConfiguration) -> str:
        root = self._normalized_root(config)
        filesystem_path = filesystem_path or "/"
        if filesystem_path == root:
            return "/"
        root_prefix = root.rstrip("/") + "/"
        if filesystem_path.startswith(root_prefix):
            return "/" + filesystem_path[len(root_prefix) :]
        return filesystem_path if filesystem_path.startswith("/") else f"/{filesystem_path}"

    @staticmethod
    def _normalized_root(config: IrodsFsspecFileSourceConfiguration) -> str:
        if not config.root:
            return "/"
        root = os.path.normpath(config.root)
        return root if root.startswith("/") else f"/{root}"


__all__ = ("IrodsFsspecFilesSource",)
