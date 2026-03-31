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

    def _to_filesystem_path(self, path: str, config: AzureFlatFileSourceConfiguration) -> str:
        """Convert an entry path to the Azure filesystem path format."""
        if path.startswith("az://"):
            return path.replace("az://", "", 1)
        container = config.container_name
        if not container:
            return path.strip("/")
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{container}{path}"

    def _adapt_entry_path(self, filesystem_path: str, config: AzureFlatFileSourceConfiguration) -> str:
        """Remove the Azure container name from the filesystem path."""
        if container_name := config.container_name:
            prefix = f"{container_name}/"
            if filesystem_path.startswith(prefix):
                return filesystem_path.replace(prefix, "", 1)
        return filesystem_path

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
        return super()._list(
            context=context,
            path=path,
            recursive=recursive,
            limit=limit,
            offset=offset,
            query=query,
            sort_by=sort_by,
        )

    def score_url_match(self, url: str):
        result = 0
        if container_name := self.template_config.container_name:
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
