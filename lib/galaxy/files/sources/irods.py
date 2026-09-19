import os
from fnmatch import fnmatch

import fs
import fs.errors

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
)
from galaxy.files.models import (
    AnyRemoteEntry,
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
    FilesSourceRuntimeContext,
)
from galaxy.util.config_templates import TemplateExpansion
from ._pyfilesystem2 import PyFilesystem2FilesSource

try:
    from fs_irods import iRODSFS
    from irods.session import iRODSSession
except ImportError:
    iRODSFS = None
    iRODSSession = None


class IrodsFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
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


class IrodsFileSourceConfiguration(BaseFileSourceConfiguration):
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


class IrodsFilesSource(PyFilesystem2FilesSource[IrodsFileSourceTemplateConfiguration, IrodsFileSourceConfiguration]):
    plugin_type = "irods"
    required_module = iRODSFS
    required_package = "fs-irods"

    template_config_class = IrodsFileSourceTemplateConfiguration
    resolved_config_class = IrodsFileSourceConfiguration

    def _iter_directory_entries(self, fs_handle, parent_path: str, normalized_query: str | None = None):
        for raw_name in fs_handle.listdir(parent_path):
            name = os.path.basename(str(raw_name).rstrip("/"))
            if not name:
                continue
            if normalized_query and not fnmatch(name.lower(), f"*{normalized_query}*"):
                continue
            entry_path = fs.path.join(parent_path, name)
            info = fs_handle.getinfo(entry_path, namespaces=["details"])
            yield entry_path, info

    def _list_non_recursive(
        self,
        fs_handle,
        path: str,
        limit: int | None = None,
        offset: int | None = None,
        query: str | None = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        normalized_query = query.lower() if query else None
        entries = []
        for _, info in self._iter_directory_entries(fs_handle, path, normalized_query):
            entries.append(self._resource_info_to_dict(path, info))
        count = len(entries)
        if (page := self._to_page(limit, offset)) is not None:
            entries = entries[page[0] : page[1]]
        return entries, count

    def _list(
        self,
        context: FilesSourceRuntimeContext[IrodsFileSourceConfiguration],
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: int | None = None,
        offset: int | None = None,
        query: str | None = None,
        sort_by: str | None = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        try:
            with self._open_fs(context) as fs_handle:
                if recursive:
                    raise MessageException("Recursive listing is not supported for iRODS file sources.")
                return self._list_non_recursive(fs_handle, path, limit, offset, query)
        except fs.errors.PermissionDenied as e:
            raise AuthenticationRequired(
                f"Permission Denied. Reason: {e}. Please check your credentials in your preferences for {self.label}."
            ) from e
        except fs.errors.FSError as e:
            raise MessageException(f"Problem listing file source path {path}. Reason: {e}") from e

    def _open_fs(self, context: FilesSourceRuntimeContext[IrodsFileSourceConfiguration]):
        if iRODSFS is None or iRODSSession is None:
            raise self.required_package_exception

        config = context.config
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

        return iRODSFS(session=session, root=config.root)


__all__ = ("IrodsFilesSource",)
