from collections.abc import Iterator
from contextlib import contextmanager

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
    ObjectNotFound,
    RequestParameterInvalidException,
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
    MAX_ITEMS_LIMIT,
)
from galaxy.util.config_templates import TemplateExpansion

try:
    from arcfs.fs import GitLabARCFileSystem
except ImportError:
    GitLabARCFileSystem = None

# arcfs separates the GitLab project path from the path inside the repository with this marker, e.g.
# ``group/project:-:assays/data.csv``. Galaxy paths keep the marker, because the project boundary
# cannot be recovered from a plain path without asking GitLab, but add a "/" after it so that the
# usual assumptions about "/"-separated paths hold: an entry's name is its last segment, and a
# project's path is a prefix of the paths of the entries inside it.
ROOT_MARKER = ":-:"
# GitLab silently caps ``per_page`` at 100, while arcfs derives the page number from the requested
# limit, so larger pages have to be assembled from several requests instead of asked for directly.
GITLAB_MAX_PER_PAGE = 100


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

    Exports do not land on the project's default branch: arcfs commits the file as a Git LFS pointer
    on a ``run_results-*`` branch and opens a merge request for it, so an exported file only shows up
    in a listing once a project maintainer has merged that request. That branch is named from a hash
    of the access token rather than from the export, so everything written with one token shares a
    branch and the merge request that the first export opened.

    Known limitations, all of them properties of the backend rather than choices made here:

    - Entries carry no size, timestamp or hash. GitLab's repository tree API does not return them,
      and asking per file would cost a request each.
    - Search reads at most ``MAX_ITEMS_LIMIT`` entries and filters them by name, so on a server with
      more ARCs than that, a match beyond the cap is not found. GitLab can search projects server
      side, but arcfs does not expose that yet.
    - The root listing is ordered by last activity, so a push between two page requests reorders it,
      and a listing assembled from several pages can repeat one project and miss another.
    - The fsspec cache options are accepted for consistency with the other fsspec sources, but arcfs
      replaces fsspec's expiring cache with a plain dict and ignores them.
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
            # Without this, fsspec caches one instance per (base_url, token) for the whole process:
            # closing it at the end of one request would tear down the aiohttp session that other
            # requests are still reading from, and arcfs' own listing cache would never expire.
            skip_instance_cache=True,
            **cache_options,
        )

    @contextmanager
    def _filesystem(
        self, context: FilesSourceRuntimeContext[ARCFileSourceConfiguration], description: str
    ) -> Iterator[tuple["GitLabARCFileSystem", ARCFileSourceConfiguration]]:
        """Open a filesystem for one operation and translate arcfs failures into Galaxy exceptions.

        ``_open_fs`` builds a fresh instance per operation, so closing it here cannot affect anything
        else in flight. ``description`` completes the "Problem ..." message of unexpected failures,
        including the one raised when the package is missing.
        """
        fs = None
        try:
            fs = self._open_fs(context, self._get_cache_options(context.config))
            yield fs, context.config
        except MessageException:
            raise  # already an actionable Galaxy exception, don't wrap it again
        except PermissionError as e:
            if e.filename is not None:
                # Refused by the local filesystem, so the user's ARC credentials are not the problem.
                raise MessageException(f"Problem {description}. Reason: {e.strerror or e}") from e
            # arcfs does not raise this for authentication today, but a future version might.
            raise AuthenticationRequired(self._credentials_message(e))
        except FileNotFoundError as e:
            if e.filename is not None:
                # A local path that Galaxy staged, not anything in the ARC. Saying the ARC is missing
                # would be wrong, and would put a server-side path in front of the user.
                raise MessageException(f"Problem {description}. Reason: {e.strerror or e}") from e
            # arcfs raises this bare for an ARC without any commit yet, where it carries the numeric
            # project id, and for one that was removed or is invisible to these credentials.
            raise ObjectNotFound(
                f"Could not find {e} in {self.label}. The ARC may be empty, may have been removed, "
                "or may not be visible with your credentials."
            ) from e
        except Exception as e:
            # GitLab answers 401/403 for a missing, invalid, expired or insufficiently scoped token.
            # aiohttp reports those as ClientResponseError, which is not an OSError, so it arrives
            # here. Matching on the status keeps this module importable without aiohttp, which the
            # standalone galaxy-files package does not depend on.
            status = getattr(e, "status", None)
            if status in (401, 403):
                raise AuthenticationRequired(self._credentials_message(f"{status} {getattr(e, 'message', e)}"))
            raise MessageException(f"Problem {description}. Reason: {e}") from e
        finally:
            if fs is not None:
                fs.close()

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
        """List the ARCs of a DataHUB, or the entries inside one.

        Listings are built from arcfs' ``list_page``, which paginates against GitLab and reports the
        total number of entries that Galaxy needs for its pagination controls. ``fs.ls()`` reports no
        total, and makes arcfs fetch and keep the whole project catalogue in one call, so it is only
        used for recursion inside a project.
        """
        if recursive:
            if self._is_source_root(path):
                # fsspec would rewrite "/" to arcfs' root marker, which arcfs resolves as a project
                # with an empty path, calling GitLab's project *list* endpoint and failing obscurely.
                raise RequestParameterInvalidException(
                    "Listing all ARCs recursively is not supported. Please list a single ARC instead."
                )
            with self._filesystem(context, f"listing file source path {path}") as (fs, config):
                entries, total = self._list_recursive(fs, self._to_filesystem_path(path, config), config)
                return self._apply_pagination(entries, limit, offset), total

        with self._filesystem(context, f"listing file source path {path}") as (fs, config):
            fs_path = self._to_filesystem_path(path, config)

            if query:
                # The generic implementation globs, which needs ``_info``; arcfs implements no
                # ``_info``, so globbing fails with a bare NotImplementedError.
                entries, total = self._collect_window(fs, fs_path, config, 0, MAX_ITEMS_LIMIT)
                if total > len(entries):
                    self._on_listing_exceeded()
                matched = self._filter_by_name(entries, query)
                return self._apply_pagination(matched, limit, offset), len(matched)

            if limit is None:
                entries, total = self._collect_window(fs, fs_path, config, 0, MAX_ITEMS_LIMIT)
                if total > len(entries):
                    self._on_listing_exceeded()
                return self._apply_pagination(entries, limit, offset), total

            start = offset or 0
            if limit <= GITLAB_MAX_PER_PAGE and start % limit == 0:
                # arcfs maps this straight onto one GitLab page. Any other window would make it fetch
                # the whole listing instead, so those go through the window collector below.
                infos, total = fs.list_page(fs_path, True, offset=start, limit=limit)
                return [self._info_to_entry(info, config) for info in infos], total

            return self._collect_window(fs, fs_path, config, start, limit)

    def _collect_window(
        self,
        fs: "GitLabARCFileSystem",
        fs_path: str,
        config: ARCFileSourceConfiguration,
        start: int,
        count: int,
    ) -> tuple[list[AnyRemoteEntry], int]:
        """Return up to ``count`` entries from ``start``, read as whole aligned pages.

        arcfs serves a window from one GitLab page only when the offset is a multiple of the limit,
        and otherwise fetches the entire listing and slices it. Asking for whole pages keeps every
        request on the cheap path, and reading only the pages that cover the window means a far page
        does not cost a walk from the beginning.
        """
        page_size = GITLAB_MAX_PER_PAGE
        page_start = (start // page_size) * page_size
        entries: list[AnyRemoteEntry] = []
        total = 0
        position = page_start
        while position < start + count:
            infos, total = fs.list_page(fs_path, True, offset=position, limit=page_size)
            entries.extend(self._info_to_entry(info, config) for info in infos)
            position += page_size
            if len(infos) < page_size:
                break
        window = entries[start - page_start : start - page_start + count]
        if not entries:
            # The window starts past the end, so ``page_start`` says nothing about how many entries
            # exist. Claiming it as the total would keep a pager offering pages that are all empty.
            return window, total
        return window, max(total, page_start + len(entries))

    def _adapt_entry_path(self, filesystem_path: str, config: ARCFileSourceConfiguration) -> str:
        """Insert a "/" after the marker, turning ``group/repo:-:file`` into ``group/repo:-:/file``."""
        project, marker, inside = filesystem_path.partition(ROOT_MARKER)
        if not marker:
            return filesystem_path
        return f"{project}{marker}/{inside.lstrip('/')}"

    def _to_filesystem_path(self, path: str, config: ARCFileSourceConfiguration) -> str:
        """Drop the "/" that ``_adapt_entry_path`` inserted, back to the path arcfs expects.

        Paths recorded before that separator was introduced simply pass through unchanged.
        """
        project, marker, inside = path.partition(ROOT_MARKER)
        if not marker:
            return path
        return f"{project}{marker}{inside.lstrip('/')}"

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[ARCFileSourceConfiguration],
    ):
        with self._filesystem(context, f"reading file source path {source_path}") as (fs, config):
            fs.get_file(self._to_filesystem_path(source_path, config), native_path)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[ARCFileSourceConfiguration],
    ):
        with self._filesystem(context, f"writing to file source path {target_path}") as (fs, config):
            fs.put_file(native_path, self._to_filesystem_path(target_path, config))

    def _info_to_entry(self, info: dict, config: ARCFileSourceConfiguration) -> AnyRemoteEntry:
        entry = super()._info_to_entry(info, config)
        entry.name = self._display_name(entry.path)
        return entry

    def _credentials_message(self, reason: object) -> str:
        return (
            f"Permission Denied. Reason: {reason}. "
            f"Please check your credentials in your preferences for {self.label}."
        )

    @staticmethod
    def _is_source_root(path: str) -> bool:
        return not path.strip("/")

    @staticmethod
    def _filter_by_name(entries: list[AnyRemoteEntry], query: str) -> list[AnyRemoteEntry]:
        needle = query.casefold()
        return [entry for entry in entries if needle in entry.name.casefold()]

    @staticmethod
    def _display_name(path: str) -> str:
        """Return the name to show for an arcfs path, hiding the ``:-:`` marker.

        Projects (paths ending with the marker) keep their full ``group/project`` path so that
        equally named projects in different groups stay distinguishable; entries inside a project
        show only their last path component.
        """
        project, marker, inside = path.partition(ROOT_MARKER)
        if not marker:
            return path.rstrip("/").rsplit("/", 1)[-1] or path
        inside = inside.strip("/")
        if not inside:
            return project
        return inside.rsplit("/", 1)[-1]


__all__ = ("ARCFilesSource",)
