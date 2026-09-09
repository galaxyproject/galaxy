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

DEFAULT_PAGE_SIZE = 50


class ARCFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    base_url: str | TemplateExpansion
    token: str | TemplateExpansion | None = None


class ARCFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    base_url: str
    token: str | None = None


class ARCFilesSource(FsspecFilesSource[ARCFileSourceTemplateConfiguration, ARCFileSourceConfiguration]):
    """File source for ARCs (Annotated Research Contexts) hosted on a DataHUB/GitLab instance.

    Backed by the ``arcfs-fsspec`` package, which exposes the GitLab projects accessible with the
    configured credentials as top-level directories and their repository trees below them.
    """

    plugin_type = "arc"
    required_module = GitLabARCFileSystem
    required_package = "arcfs-fsspec"

    template_config_class = ARCFileSourceTemplateConfiguration
    resolved_config_class = ARCFileSourceConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[ARCFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ) -> "GitLabARCFileSystem":
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
        context: FilesSourceRuntimeContext[ARCFileSourceConfiguration],
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: int | None = None,
        offset: int | None = None,
        query: str | None = None,
        sort_by: str | None = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        """Use the ARCfs paginated listing when Galaxy asks for a page of entries.

        The GitLab API paginates server-side and reports the total number of entries, which Galaxy
        needs for its pagination controls and which ``fs.ls()`` cannot provide. Recursive, query-based
        and sorted listings, as well as unpaginated ones, fall back to the generic fsspec implementation.
        """
        if recursive or query or sort_by or (limit is None and offset is None):
            return super()._list(context, path, recursive, write_intent, limit, offset, query, sort_by)

        try:
            cache_options = self._get_cache_options(context.config)
            fs = self._open_fs(context, cache_options)
            fs_path = self._to_filesystem_path(path, context.config)
            try:
                infos, total_count = fs.list_page(
                    fs_path,
                    True,
                    offset=offset or 0,
                    limit=limit or DEFAULT_PAGE_SIZE,
                )
            finally:
                fs.close()
            return [self._info_to_entry(info, context.config) for info in infos], total_count
        except PermissionError as e:
            # Anonymous access to public projects works without a token, but an invalid token raises PermissionError.
            raise AuthenticationRequired(
                f"Permission Denied. Reason: {e}. Please check your credentials in your preferences for {self.label}."
            )
        except Exception as e:
            raise MessageException(f"Problem listing file source path {path}. Reason: {e}") from e


__all__ = ("ARCFilesSource",)
