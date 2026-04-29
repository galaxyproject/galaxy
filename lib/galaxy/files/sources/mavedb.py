from typing import (
    Optional,
    Union,
)

from fsspec import AbstractFileSystem

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
)
from galaxy.files.models import (
    AnyRemoteEntry,
    FilesSourceRuntimeContext,
)
from galaxy.files.sources._defaults import DEFAULT_SCHEME
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)
from galaxy.util.config_templates import TemplateExpansion

try:
    from mavedb_fsspec import MaveDBFileSystem
    from mavedb_fsspec.client import DEFAULT_BASE_URL
except ImportError:
    MaveDBFileSystem = None
    DEFAULT_BASE_URL = "https://api.mavedb.org/api/v1"


class MaveDBFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    base_url: Union[str, TemplateExpansion] = DEFAULT_BASE_URL
    api_key: Union[str, TemplateExpansion, None] = None
    timeout: Union[float, TemplateExpansion] = 30.0


class MaveDBFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    base_url: str = DEFAULT_BASE_URL
    api_key: Optional[str] = None
    timeout: float = 30.0


class MaveDBFilesSource(FsspecFilesSource[MaveDBFileSourceTemplateConfiguration, MaveDBFileSourceConfiguration]):
    plugin_type = "mavedb"
    required_module = MaveDBFileSystem
    required_package = "mavedb-fsspec"

    template_config_class = MaveDBFileSourceTemplateConfiguration
    resolved_config_class = MaveDBFileSourceConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[MaveDBFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ) -> AbstractFileSystem:
        if MaveDBFileSystem is None:
            raise self.required_package_exception

        config = context.config
        return MaveDBFileSystem(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout,
            **cache_options,
        )

    def _list(
        self,
        context: FilesSourceRuntimeContext[MaveDBFileSourceConfiguration],
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        collection = path.strip("/")
        if recursive or collection not in {"score-sets", "my-score-sets"}:
            return super()._list(context, path, recursive, write_intent, limit, offset, query, sort_by)

        try:
            cache_options = self._get_cache_options(context.config)
            fs = self._open_fs(context, cache_options)
            entries, total_count = fs.list_score_sets(
                collection=collection,
                limit=limit,
                offset=offset,
                query=query,
            )
            return [self._info_to_entry(entry, context.config) for entry in entries], total_count
        except PermissionError as e:
            raise AuthenticationRequired(
                f"Permission Denied. Reason: {e}. Please check your credentials in your preferences for {self.label}."
            )
        except Exception as e:
            raise MessageException(f"Problem listing file source path {path}. Reason: {e}") from e

    def _info_to_entry(self, info: dict, config: MaveDBFileSourceConfiguration) -> AnyRemoteEntry:
        entry = super()._info_to_entry(info, config)
        display_name = info.get("display_name")
        if display_name:
            entry.name = display_name
        return entry

    def _write_from(
        self,
        _target_path: str,
        _native_path: str,
        _context: FilesSourceRuntimeContext[MaveDBFileSourceConfiguration],
    ):
        raise MessageException("MaveDB file sources are read-only and do not support exporting files.")

    def get_scheme(self) -> str:
        return self.scheme if self.scheme and self.scheme != DEFAULT_SCHEME else "mavedb"


__all__ = ("MaveDBFilesSource",)
