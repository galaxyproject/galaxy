import logging
from typing import (
    Optional,
    Union,
)

from galaxy.files.models import (
    AnyRemoteEntry,
    FilesSourceRuntimeContext,
    RemoteDirectory,
)
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)
from galaxy.util.config_templates import TemplateExpansion

try:
    from adlfs import AzureBlobFileSystem
except ImportError:
    AzureBlobFileSystem = None


REQUIRED_PACKAGE = "adlfs"
FS_PLUGIN_TYPE = "azureflat"

log = logging.getLogger(__name__)


class AzureFlatFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    account_name: Union[str, TemplateExpansion]
    container_name: Union[str, TemplateExpansion, None] = None
    account_key: Union[str, TemplateExpansion]


class AzureFlatFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    account_name: str
    container_name: Optional[str] = None
    account_key: str


class AzureFlatFilesSource(
    FsspecFilesSource[AzureFlatFileSourceTemplateConfiguration, AzureFlatFileSourceConfiguration]
):
    plugin_type = FS_PLUGIN_TYPE
    required_module = AzureBlobFileSystem
    required_package = REQUIRED_PACKAGE
    template_config_class = AzureFlatFileSourceTemplateConfiguration
    resolved_config_class = AzureFlatFileSourceConfiguration

    def _open_fs(
        self, context: FilesSourceRuntimeContext[AzureFlatFileSourceConfiguration], cache_options: CacheOptionsDictType
    ):
        if AzureBlobFileSystem is None:
            raise self.required_package_exception
        else:
            config = context.config
            fs = AzureBlobFileSystem(account_name=config.account_name, credential=config.account_key, **cache_options)
            return fs

    def _to_container_path(self, path: str, config: AzureFlatFileSourceConfiguration) -> str:
        result = ""
        if path.startswith("az://"):
            result = path.replace("az://", "", 1)
        else:
            container = config.container_name
            if not container:
                result = path.strip("/")
            else:
                result = self._container_path(container, path)
        return result

    def _adapt_entry_path(self, filesystem_path: str) -> str:
        result = filesystem_path
        container_name = self.template_config.container_name
        if container_name:
            prefix = f"{container_name}/"
            if filesystem_path.startswith(prefix):
                result = filesystem_path.replace(prefix, "", 1)
            else:
                result = filesystem_path
        else:
            result = filesystem_path
        return result

    def _list(
        self,
        context: FilesSourceRuntimeContext[AzureFlatFileSourceConfiguration],
        path: str = "/",
        recursive: bool = False,
        write_intent: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        if context.config.container_name is None and path == "/":
            fs = self._open_fs(context, {})
            containers = fs.ls("", detail=True)
            entries: list[AnyRemoteEntry] = []
            for entry in containers:
                name = entry["name"]
                uri = f"az://{name}"
                entries.append(
                    RemoteDirectory(
                        name=name,
                        uri=uri,
                        path=f"/{name}",
                    )
                )
            return entries, len(entries)
        container_path = self._to_container_path(path, context.config)
        entries, count = super()._list(
            context=context,
            path=container_path,
            recursive=recursive,
            limit=limit,
            offset=offset,
            query=query,
            sort_by=sort_by,
        )
        return entries, count

    def _realize_to(
        self, source_path: str, native_path: str, context: FilesSourceRuntimeContext[AzureFlatFileSourceConfiguration]
    ):
        container_path = self._to_container_path(source_path, context.config)
        super()._realize_to(source_path=container_path, native_path=native_path, context=context)

    def _write_from(
        self, target_path: str, native_path: str, context: FilesSourceRuntimeContext[AzureFlatFileSourceConfiguration]
    ):
        container_path = self._to_container_path(target_path, context.config)
        super()._write_from(target_path=container_path, native_path=native_path, context=context)

    def _container_path(self, container_name: str, path: str) -> str:
        adjusted_path = path
        if path.startswith("az://"):
            adjusted_path = path.replace("az://", "", 1)
        else:
            if not path.startswith("/"):
                adjusted_path = f"/{path}"
            else:
                adjusted_path = path
        return f"{container_name}{adjusted_path}"

    def score_url_match(self, url: str):
        container_name = self.template_config.container_name
        result = 0
        if container_name:
            prefix = f"az://{container_name}"
            if url.startswith(f"{prefix}/") or url == prefix:
                result = len(prefix)
            else:
                result = super().score_url_match(url)
        else:
            if url.startswith("az://"):
                result = len("az://")
            else:
                result = super().score_url_match(url)
        return result


__all__ = ("AzureFlatFilesSource",)
