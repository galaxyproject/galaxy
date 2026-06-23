import os
from typing import (
    Annotated,
    Union,
)

from fsspec.implementations.local import LocalFileSystem
from pydantic import Field

from galaxy.files.models import (
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

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[TempFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ):
        return LocalFileSystem(
            auto_mkdir=context.config.auto_mkdir,
            **cache_options,
        )

    def _to_filesystem_path(self, path: str, config: TempFileSourceConfiguration) -> str:
        """Convert a virtual temp path to an actual filesystem path."""
        relative_path = path.lstrip("/")
        if not relative_path:
            return config.root_path
        return os.path.join(config.root_path, relative_path)

    def _adapt_entry_path(self, filesystem_path: str, config: TempFileSourceConfiguration) -> str:
        """Convert an actual filesystem path back to virtual temp path."""
        root_path = config.root_path
        if filesystem_path.startswith(root_path):
            virtual_path = filesystem_path[len(root_path) :]
            if not virtual_path.startswith("/"):
                virtual_path = f"/{virtual_path}"
            elif virtual_path.startswith("//"):
                virtual_path = virtual_path[1:]
            return virtual_path
        return filesystem_path

    def get_scheme(self) -> str:
        return "temp"


__all__ = ("TempFilesSource",)
