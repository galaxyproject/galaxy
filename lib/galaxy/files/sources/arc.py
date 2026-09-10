import sys
from collections.abc import Iterator
from contextlib import contextmanager

from aiohttp import ClientResponseError

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
# ``arcfs-fsspec`` requires a newer interpreter than Galaxy itself does.
MINIMUM_PYTHON_VERSION = (3, 11)


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
    in a listing once a project maintainer has merged that request.
    """

    plugin_type = "arc"
    required_module = GitLabARCFileSystem
    required_package = "arcfs-fsspec"

    template_config_class = ARCFileSourceTemplateConfiguration
    resolved_config_class = ARCFileSourceConfiguration

    @property
    def required_package_exception(self) -> Exception:
        # The conditional requirement carries a ``python_version >= "3.11"`` marker, so on an older
        # interpreter the package is skipped at install time and cannot be installed by hand either.
        # Say so, instead of sending the admin to a ``pip install`` that fails on Requires-Python.
        if sys.version_info < MINIMUM_PYTHON_VERSION:
            required = ".".join(str(part) for part in MINIMUM_PYTHON_VERSION)
            running = ".".join(str(part) for part in sys.version_info[:3])
            return Exception(
                f"{super().required_package_exception} It requires Python {required} or newer, "
                f"but Galaxy is running on Python {running}."
            )
        return super().required_package_exception

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
        else in flight. ``description`` completes the "Problem ..." message of unexpected failures.
        """
        fs = self._open_fs(context, self._get_cache_options(context.config))
        try:
            yield fs, context.config
        except MessageException:
            raise  # already an actionable Galaxy exception, don't wrap it again
        except PermissionError as e:
            # arcfs 0.1.9 does not raise this for authentication, but a future version might.
            raise AuthenticationRequired(self._credentials_message(e))
        except ClientResponseError as e:
            # GitLab answers 401/403 for a missing, invalid, expired or insufficiently scoped token.
            if e.status in (401, 403):
                raise AuthenticationRequired(self._credentials_message(f"{e.status} {e.message}"))
            raise MessageException(f"Problem {description}. Reason: {e}") from e
        except FileNotFoundError as e:
            # arcfs raises this both for an ARC without any commit yet, where it carries the numeric
            # project id, and for one that was removed or is invisible to these credentials.
            raise ObjectNotFound(
                f"Could not find {e} in {self.label}. The ARC may be empty, may have been removed, "
                "or may not be visible with your credentials."
            ) from e
        except Exception as e:
            raise MessageException(f"Problem {description}. Reason: {e}") from e
        finally:
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
            return super()._list(context, path, recursive, write_intent, limit, offset, query, sort_by)

        with self._filesystem(context, f"listing file source path {path}") as (fs, config):
            fs_path = self._to_filesystem_path(path, config)

            if query:
                # The generic implementation globs, which needs ``_info``; arcfs implements no
                # ``_info``, so globbing fails with a bare NotImplementedError.
                matched = self._filter_by_name(self._collect_pages(fs, fs_path, config)[0], query)
                return self._apply_pagination(matched, limit, offset), len(matched)

            if limit is None or limit > GITLAB_MAX_PER_PAGE:
                cap = MAX_ITEMS_LIMIT if limit is None else min((offset or 0) + limit, MAX_ITEMS_LIMIT)
                entries, total = self._collect_pages(fs, fs_path, config, cap)
                return self._apply_pagination(entries, limit, offset), total

            infos, total = fs.list_page(fs_path, True, offset=offset or 0, limit=limit)
            return [self._info_to_entry(info, config) for info in infos], total

    def _collect_pages(
        self,
        fs: "GitLabARCFileSystem",
        fs_path: str,
        config: ARCFileSourceConfiguration,
        cap: int = MAX_ITEMS_LIMIT,
    ) -> tuple[list[AnyRemoteEntry], int]:
        """Assemble a listing from consecutive pages, stopping after ``cap`` entries.

        Requesting everything in one call instead would make arcfs retain the entire catalogue, and on
        instances that do not report page totals it falls back to walking every project it can see.
        """
        entries: list[AnyRemoteEntry] = []
        total = 0
        while len(entries) < cap:
            requested = min(GITLAB_MAX_PER_PAGE, cap - len(entries))
            infos, total = fs.list_page(fs_path, True, offset=len(entries), limit=requested)
            entries.extend(self._info_to_entry(info, config) for info in infos)
            if len(infos) < requested:
                return entries, max(total, len(entries))
        self._on_listing_exceeded()
        return entries, max(total, len(entries))

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
