from __future__ import annotations

from typing import (
    Optional,
    Union,
)

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
)
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
    from arcfs.fs import GitLabARCFileSystem
except ImportError:
    GitLabARCFileSystem = None


REQUIRED_PACKAGE = "arcfs-fsspec"
FS_PLUGIN_TYPE = "arc"


class ARCTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    base_url: Union[str, TemplateExpansion]
    token: Union[str, TemplateExpansion, None] = None


class ARCResolvedConfiguration(FsspecBaseFileSourceConfiguration):
    base_url: str
    token: Optional[str] = None


class ARCFilesSource(FsspecFilesSource[ARCTemplateConfiguration, ARCResolvedConfiguration]):
    plugin_type = FS_PLUGIN_TYPE
    required_module = GitLabARCFileSystem
    required_package = REQUIRED_PACKAGE
    template_config_class = ARCTemplateConfiguration
    resolved_config_class = ARCResolvedConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[ARCResolvedConfiguration],
        cache_options: CacheOptionsDictType,
    ):
        if GitLabARCFileSystem is None:
            raise self.required_package_exception

        config = context.config
        return GitLabARCFileSystem(
            base_url=config.base_url,
            token=config.token,
            asynchronous=False,
            **cache_options,
        )

    def _list(
        self,
        context: FilesSourceRuntimeContext[ARCResolvedConfiguration],
        path: str = "/",
        recursive: bool = False,
        write_intent: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        """
        Use ARCfs paginated filesystem listing when offset/limit are specified.

        If recursive listing, query-based listing, or sorting is requested, fall
        back to generic fsspec implementation.

        For the paginated ARC path, the plugin only calls filesystem methods. If
        real backend pagination is not possible, the fallback is handled inside
        the ARCfs filesystem class rather than here.
        """
        try:
            if recursive or query or sort_by or (limit is None and offset is None):
                return super()._list(
                    context=context,
                    path=path,
                    recursive=recursive,
                    write_intent=write_intent,
                    limit=limit,
                    offset=offset,
                    query=query,
                    sort_by=sort_by,
                )

            cache_options = self._get_cache_options(context.config)
            fs = self._open_fs(context, cache_options)
            fs_path = self._to_filesystem_path(path, context.config)

            try:
                infos, total_count = fs.list_page(
                    fs_path,
                    True,
                    offset=offset or 0,
                    limit=limit or 50,
                )
                entries = [self._info_to_entry(info, context.config) for info in infos]
                return entries, total_count
            finally:
                fs.close()

        except PermissionError as e:
            # Unauthenticated access without a token is possible, but an invalid token will raise PermissionError.
            raise AuthenticationRequired(
                f"Permission Denied. Reason: {e}. Please check your credentials in your preferences for {self.label}."
            )
        except Exception as e:
            raise MessageException(f"Problem listing file source path {path}. Reason: {e}") from e


__all__ = ("ARCFilesSource",)
