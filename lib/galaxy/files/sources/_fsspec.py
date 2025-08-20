import abc
import functools
import logging
import os
from typing import (
    Annotated,
    Any,
    ClassVar,
    Optional,
    TypeVar,
)

from fsspec import AbstractFileSystem
from pydantic import Field
from typing_extensions import cast

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
)
from galaxy.files.models import (
    AnyRemoteEntry,
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
    FilesSourceRuntimeContext,
    RemoteDirectory,
    RemoteFile,
    StrictModel,
)
from galaxy.files.sources import BaseFilesSource

log = logging.getLogger(__name__)

PACKAGE_MESSAGE = "FilesSource plugin is missing required Python fsspec plugin package [%s]"


# Maximum number of items to return in a single listing.
# This is a safeguard to prevent excessive memory usage and performance issues
# since is a huge number of items is not practical for browsing in most use cases.
MAX_ITEMS_LIMIT = 1000


class FsspecCommonCacheOptions(StrictModel):
    """Common cache options for fsspec-based file sources.

    These options are not user-configurable so they don't need TemplateExpansion.
    """

    use_listings_cache: Annotated[
        bool,
        Field(
            description="If False, the cache never returns items, but always reports KeyError, and setting items has no effect.",
        ),
    ] = True

    listings_expiry_time: Annotated[
        Optional[int],
        Field(description="Time in seconds that a listing is considered valid. If None, listings do not expire."),
    ] = None

    max_paths: Annotated[
        Optional[int],
        Field(
            description="The number of most recent listings that are considered valid; 'recent' refers to when the entry was set.",
        ),
    ] = None


CacheOptionsDictType = dict[str, Any]


class FsspecBaseFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration, FsspecCommonCacheOptions):
    """Base template configuration for fsspec-based file sources.

    Fsspec-based file sources template configurations should inherit from this class to define their template configurations.
    """


class FsspecBaseFileSourceConfiguration(BaseFileSourceConfiguration, FsspecCommonCacheOptions):
    """Base resolved configuration for fsspec-based file sources.

    Fsspec-based file sources configurations should inherit from this class to define their resolved configurations.
    """


FsspecTemplateConfigType = TypeVar("FsspecTemplateConfigType", bound=FsspecBaseFileSourceTemplateConfiguration)
FsspecResolvedConfigurationType = TypeVar("FsspecResolvedConfigurationType", bound=FsspecBaseFileSourceConfiguration)


class FsspecFilesSource(BaseFilesSource[FsspecTemplateConfigType, FsspecResolvedConfigurationType]):
    required_module: ClassVar[Optional[type[AbstractFileSystem]]]
    required_package: ClassVar[str]
    supports_pagination = True
    supports_search = True
    supports_sorting = False

    def __init__(self, template_config: FsspecTemplateConfigType):
        self.ensure_required_dependency()
        super().__init__(template_config)
        self._initialize_listings_expiry()

    @property
    def required_package_exception(self) -> Exception:
        return Exception(PACKAGE_MESSAGE % self.required_package)

    def ensure_required_dependency(self):
        if self.required_module is None:
            raise self.required_package_exception

    def _initialize_listings_expiry(self):
        """Fallback to general config listings expiry time if not explicitly set in the template config."""
        self.template_config.listings_expiry_time = (
            self.template_config.listings_expiry_time or self.template_config.file_sources_config.listings_expiry_time
        )

    @abc.abstractmethod
    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[FsspecResolvedConfigurationType],
        cache_options: CacheOptionsDictType,
    ) -> AbstractFileSystem:
        """Subclasses must instantiate an fsspec AbstractFileSystem handle for this file system."""

    def _list(
        self,
        context: FilesSourceRuntimeContext[FsspecResolvedConfigurationType],
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        """Return the list of 'Directory's and 'File's under the given path.

        If `recursive` is True, it will recursively list all files and directories under the given path with a maximum limit of `MAX_ITEMS_PER_LISTING`.
        If `query` is provided, it will filter the results based on the query using glob patterns.
        Pagination is supported with `limit` and `offset` but please note it is not applied until after the full listing is retrieved from the filesystem.
        """
        try:
            cache_options = self._get_cache_options(context.config)
            fs = self._open_fs(context, cache_options)

            if recursive:
                return self._list_recursive(fs, path)

            if query:
                entries_list = self._list_with_query(fs, path, query)
            else:
                entries_list = self._list_directory(fs, path)

            total_count = len(entries_list)

            # We apply pagination after getting all entries.
            # This is not ideal but necessary due to how fsspec handles listings.
            # At least we reduce the traffic to the client produced by a large listing ¯\_(ツ)_/¯
            paginated_entries = self._apply_pagination(entries_list, limit, offset)

            return paginated_entries, total_count

        except PermissionError as e:
            raise AuthenticationRequired(
                f"Permission Denied. Reason: {e}. Please check your credentials in your preferences for {self.label}."
            )
        except Exception as e:
            raise MessageException(f"Problem listing file source path {path}. Reason: {e}") from e

    def _build_glob_pattern(self, path: str, query: str) -> str:
        """Build a glob pattern for server-side filtering."""
        # Escape special glob characters in the query except * and ?
        escaped_query = query.replace("[", r"\[").replace("]", r"\]").replace("{", r"\{").replace("}", r"\}")
        path_prefix = path.rstrip("/") if path != "/" else ""
        return f"{path_prefix}/*{escaped_query}*"

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[FsspecResolvedConfigurationType],
    ):
        """Download a file from the fsspec filesystem to a local path."""
        cache_options = self._get_cache_options(context.config)
        fs = self._open_fs(context, cache_options)
        fs.get_file(source_path, native_path)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[FsspecResolvedConfigurationType],
    ):
        """Upload a file from a local path to the fsspec filesystem."""
        cache_options = self._get_cache_options(context.config)
        fs = self._open_fs(context, cache_options)
        fs.put_file(native_path, target_path)

    def _adapt_entry_path(self, filesystem_path: str) -> str:
        """Adapt the filesystem path to the desired entry path.

        Subclasses can override this to transform paths (e.g., filesystem to virtual paths).
        By default, returns the filesystem path unchanged.
        """
        return filesystem_path

    def _extract_timestamp(self, info: dict) -> Optional[str]:
        """Extract and format timestamp from fsspec file info."""
        # Handle timestamp fields more robustly - check for None explicitly
        mtime = info.get("mtime")
        if mtime is None:
            mtime = info.get("modified")
        if mtime is None:
            mtime = info.get("LastModified")

        ctime_result = self.to_dict_time(mtime)
        return ctime_result

    def _info_to_entry(self, info: dict) -> AnyRemoteEntry:
        """Convert fsspec file info to Galaxy's remote entry format."""
        filesystem_path = info["name"]
        entry_path = self._adapt_entry_path(filesystem_path)
        name = os.path.basename(entry_path)
        uri = self.uri_from_path(entry_path)

        if info.get("type") == "directory":
            return RemoteDirectory(name=name, uri=uri, path=entry_path)
        else:
            size = int(info.get("size", 0))
            ctime = self._extract_timestamp(info)
            return RemoteFile(name=name, size=size, ctime=ctime, uri=uri, path=entry_path)

    def _list_recursive(self, fs: AbstractFileSystem, path: str) -> tuple[list[AnyRemoteEntry], int]:
        """Handle recursive directory listing with item limit."""
        # TODO: this is potentially inefficient for large directories.
        # We should consider dropping this option.
        # Limiting the number of items returned for now.
        res: list[AnyRemoteEntry] = []
        count = 0
        for _, dirs, files in fs.walk(path, detail=True):
            # We are using detail=True to get file info as dicts,
            # so we can safely cast the result.
            dirs = cast(dict[str, dict], dirs)
            files = cast(dict[str, dict], files)
            to_entry = functools.partial(self._info_to_entry)
            res.extend(map(to_entry, dirs.values()))
            res.extend(map(to_entry, files.values()))
            count += len(dirs) + len(files)
            if count >= MAX_ITEMS_LIMIT:
                self._on_listing_exceeded()
                break
        return res, len(res)

    def _on_listing_exceeded(self):
        log.warning(
            "Listing for file source %s with root %s exceeded maximum items (%d).",
            self.label,
            self.get_uri_root(),
            MAX_ITEMS_LIMIT,
        )

    def _list_with_query(self, fs: AbstractFileSystem, path: str, query: str) -> list[AnyRemoteEntry]:
        """Handle directory listing with query filtering using glob patterns."""
        entries_list = []
        glob_pattern = self._build_glob_pattern(path, query)
        # Using detail=True returns a dict with file paths as keys and their info as
        # values so we can safely cast the result.
        matched_paths = cast(dict[str, dict], fs.glob(glob_pattern, detail=True))
        for entry_path, info in matched_paths.items():
            if entry_path:  # Only process entries with valid paths
                entries_list.append(self._info_to_entry(info))
        return entries_list

    def _list_directory(self, fs: AbstractFileSystem, path: str) -> list[AnyRemoteEntry]:
        """Handle standard directory listing without query filtering."""
        entries_list = []
        entries: list[dict] = fs.ls(path, detail=True)
        for entry in entries:
            entry_path = entry.get("name", entry.get("path", ""))
            if entry_path:  # Only process entries with valid paths
                entries_list.append(self._info_to_entry(entry))
        return entries_list

    def _apply_pagination(
        self, entries_list: list[AnyRemoteEntry], limit: Optional[int], offset: Optional[int]
    ) -> list[AnyRemoteEntry]:
        """Apply pagination to the entries list."""
        if offset is not None and limit is not None:
            return entries_list[offset : offset + limit]
        elif limit is not None:
            return entries_list[:limit]
        return entries_list

    def _get_cache_options(self, config: FsspecResolvedConfigurationType) -> dict[str, Any]:
        return config.model_dump(
            include=set(FsspecCommonCacheOptions.model_fields.keys()),
        )
