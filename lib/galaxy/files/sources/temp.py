import os
from typing import (
    Annotated,
    Optional,
    Union,
)

from fsspec.implementations.local import LocalFileSystem
from pydantic import Field

from galaxy.files.models import (
    AnyRemoteEntry,
    FilesSourceRuntimeContext,
    StrictModel,
)
from galaxy.util.config_templates import TemplateExpansion
from ._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)


class TempFileSourceCommonProperties(StrictModel):
    auto_mkdir: Annotated[
        bool, Field(description="Whether to automatically create directories when writing files.")
    ] = True


class TempFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration, TempFileSourceCommonProperties):
    root_path: Union[str, TemplateExpansion]


class TempFileSourceConfiguration(FsspecBaseFileSourceConfiguration, TempFileSourceCommonProperties):
    root_path: str


class TempFilesSource(FsspecFilesSource[TempFileSourceTemplateConfiguration, TempFileSourceConfiguration]):
    """A FilesSource plugin for temporary file systems.

    Since fsspec does not have temporary file system implementation, this plugin
    uses a local file system with a specified root path (ideally a temporary directory)
    to simulate a temporary file system. Files created in this source are not
    guaranteed to be deleted automatically, so users should manage cleanup as needed.

    **Note: This plugin is not intended for production use. It is primarily for testing and development purposes.**
    """

    plugin_type = "temp"
    required_module = LocalFileSystem
    required_package = "fsspec"

    template_config_class = TempFileSourceTemplateConfiguration
    resolved_config_class = TempFileSourceConfiguration

    def __init__(self, template_config: TempFileSourceTemplateConfiguration):
        super().__init__(template_config)
        self._root_path = self.template_config.root_path

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[TempFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ):
        self._root_path = context.config.root_path
        return LocalFileSystem(
            auto_mkdir=context.config.auto_mkdir,
            **cache_options,
        )

    def _to_temp_path(self, path: str) -> str:
        """Convert a virtual temp path to an actual filesystem path.

        i.e. /a/b/c -> /{root_path}/a/b/c
        """
        relative_path = path.lstrip("/")
        if not relative_path:
            return self._root_path
        return os.path.join(self._root_path, relative_path)

    def _from_temp_path(self, native_path: str) -> str:
        """Convert an actual filesystem path back to virtual temp path.

        i.e. /{root_path}/a/b/c -> /a/b/c
        """
        # Remove the root path prefix
        if native_path.startswith(self._root_path):
            virtual_path = native_path[len(self._root_path) :]
            # Ensure the path starts with a single forward slash
            if not virtual_path.startswith("/"):
                virtual_path = f"/{virtual_path}"
            elif virtual_path.startswith("//"):
                # Remove extra leading slash if present
                virtual_path = virtual_path[1:]
            return virtual_path
        return native_path

    def _list(
        self,
        context: FilesSourceRuntimeContext[TempFileSourceConfiguration],
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        native_path = self._to_temp_path(path)
        entries, total = super()._list(
            context=context,
            path=native_path,
            recursive=recursive,
            write_intent=write_intent,
            limit=limit,
            offset=offset,
            query=query,
            sort_by=sort_by,
        )
        return entries, total

    def _adapt_entry_path(self, filesystem_path: str) -> str:
        """Convert filesystem path to virtual temp path."""
        return self._from_temp_path(filesystem_path)

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[TempFileSourceConfiguration],
    ):
        temp_path = self._to_temp_path(source_path)
        return super()._realize_to(temp_path, native_path, context)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[TempFileSourceConfiguration],
    ):
        temp_path = self._to_temp_path(target_path)
        return super()._write_from(temp_path, native_path, context)

    def get_scheme(self) -> str:
        return "temp"


__all__ = ("TempFilesSource",)
