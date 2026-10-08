from typing import (
    Any,
    Literal,
)

from fsspec import AbstractFileSystem

from galaxy.exceptions import MessageException
from galaxy.files.models import (
    AnyRemoteEntry,
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
    from nomad_fsspec import NomadFileSystem
except ImportError:
    NomadFileSystem = None  # type: ignore[assignment, misc, unused-ignore]

DEFAULT_NOMAD_URL = "https://nomad-lab.eu/prod/v1"


class NomadFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    base_url: str | TemplateExpansion = DEFAULT_NOMAD_URL
    writable: Literal[False] = False


class NomadFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    base_url: str = DEFAULT_NOMAD_URL
    writable: Literal[False] = False


class NomadFilesSource(FsspecFilesSource[NomadFileSourceTemplateConfiguration, NomadFileSourceConfiguration]):
    """Browse the public datasets of NOMAD and import their raw files."""

    plugin_type = "nomad"
    required_module = NomadFileSystem
    required_package = "nomad-fsspec"

    template_config_class = NomadFileSourceTemplateConfiguration
    resolved_config_class = NomadFileSourceConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[NomadFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ) -> AbstractFileSystem:
        if NomadFileSystem is None:
            raise self.required_package_exception
        return NomadFileSystem(base_url=context.config.base_url, **cache_options)

    def _info_to_entry(self, info: dict[str, Any], config: NomadFileSourceConfiguration) -> AnyRemoteEntry:
        entry = super()._info_to_entry(info, config)
        if display_name := info.get("display_name"):
            entry.name = display_name
        return entry

    def _list_with_query(
        self, fs: AbstractFileSystem, path: str, query: str, config: NomadFileSourceConfiguration
    ) -> list[AnyRemoteEntry]:
        # paths are NOMAD ids, so search the names users see instead of globbing paths
        needle = query.casefold()
        return [entry for entry in self._list_directory(fs, path, config) if needle in entry.name.casefold()]

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[NomadFileSourceConfiguration],
    ) -> str | None:
        raise MessageException("NOMAD file sources are read-only.")


__all__ = ("NomadFilesSource",)
