import abc
import functools
import logging
import os
from typing import (
    ClassVar,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
)

from fsspec import AbstractFileSystem
from typing_extensions import (
    cast,
    NotRequired,
    Unpack,
)

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
)
from galaxy.files import OptionalUserContext
from . import (
    AnyRemoteEntry,
    BaseFilesSource,
    FilesSourceOptions,
    FilesSourceProperties,
)

log = logging.getLogger(__name__)

PACKAGE_MESSAGE = "FilesSource plugin is missing required Python fsspec plugin package [%s]"

T = TypeVar("T")

MAX_ITEMS_PER_LISTING = 1000


class FsspecFilesSourceProperties(FilesSourceProperties, total=False):
    listings_expiry_time: NotRequired[Optional[int]]


class FsspecFilesSource(BaseFilesSource):
    required_module: ClassVar[Optional[Type[AbstractFileSystem]]]
    required_package: ClassVar[str]
    supports_pagination = True
    supports_search = True
    supports_sorting = False

    def __init__(self, **kwd: Unpack[FsspecFilesSourceProperties]):
        self.ensure_required_dependency()
        props = cast(FsspecFilesSourceProperties, self._parse_common_config_opts(kwd))
        props = self._initialize_listings_expiry(props)
        self._props = props

    def ensure_required_dependency(self):
        if self.required_module is None:
            raise Exception(PACKAGE_MESSAGE % self.required_package)
        return self.required_module

    def _initialize_listings_expiry(self, props: FsspecFilesSourceProperties) -> FsspecFilesSourceProperties:
        file_sources_config = self._file_sources_config
        if (
            props.get("listings_expiry_time") is None
            and file_sources_config
            and file_sources_config.listings_expiry_time
        ):
            props["listings_expiry_time"] = file_sources_config.listings_expiry_time
        return props

    def get_prop(self, prop_name: str, expected_type: Type[T], user_context: OptionalUserContext = None) -> Optional[T]:
        """Get a property value, evaluating it if necessary."""
        value = self._props.get(prop_name)
        if self._is_templated(value) and user_context is not None:
            value = self._evaluate_prop(value, user_context=user_context)

        if isinstance(value, expected_type):
            return value
        return None

    @abc.abstractmethod
    def _open_fs(
        self, user_context: OptionalUserContext = None, opts: Optional[FilesSourceOptions] = None
    ) -> AbstractFileSystem:
        """Subclasses must instantiate an fsspec AbstractFileSystem handle for this file system."""

    def _list(
        self,
        path="/",
        recursive=False,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> Tuple[List[AnyRemoteEntry], int]:
        """Return the list of 'Directory's and 'File's under the given path.

        If `recursive` is True, it will recursively list all files and directories under the given path with a maximum limit of `MAX_ITEMS_PER_LISTING`.
        If `query` is provided, it will filter the results based on the query using glob patterns.
        Pagination is supported with `limit` and `offset` but please note it is not applied until after the full listing is retrieved from the filesystem.
        """
        try:
            fs = self._open_fs(user_context=user_context, opts=opts)

            # TODO: this is potentially inefficient for large directories.
            # We should consider dropping this option. Limiting the number of items returned for now.
            count = 0
            if recursive:
                res: List[AnyRemoteEntry] = []
                for p, dirs, files in fs.walk(path, detail=True):
                    to_dict = functools.partial(self._file_info_to_dict, str(p))
                    res.extend(map(to_dict, dirs if isinstance(dirs, dict) else []))
                    res.extend(map(to_dict, files.values() if isinstance(files, dict) else files))
                    count += len(dirs) + len(files)
                    if count >= MAX_ITEMS_PER_LISTING:
                        self.on_listing_exceeded()
                        break
                return res, len(res)

            entries_list = []
            if query:
                # Use glob for server-side filtering
                glob_pattern = self._build_glob_pattern(path, query)
                matched_paths = fs.glob(glob_pattern, detail=True)

                # Convert glob results to entries
                if isinstance(matched_paths, dict):
                    for file_path, info in matched_paths.items():
                        entries_list.append(self._file_info_to_dict(str(file_path), info))
                elif isinstance(matched_paths, list):
                    for item in matched_paths:
                        if isinstance(item, str):
                            # Get details for this path
                            try:
                                info = fs.info(item)
                                entries_list.append(self._file_info_to_dict(item, info))
                            except (FileNotFoundError, PermissionError):
                                continue
                        elif isinstance(item, dict):
                            file_path = item.get("name", item.get("path", ""))
                            if isinstance(file_path, str):
                                entries_list.append(self._file_info_to_dict(file_path, item))

            else:
                # No query - list directory contents
                entries = fs.ls(path, detail=True)
                for entry in entries:
                    entry_path = entry.get("name", entry.get("path", ""))
                    entries_list.append(self._file_info_to_dict(entry_path, entry))

            total_count = len(entries_list)

            # Apply pagination after getting total count
            # This is not ideal but necessary due to how fsspec handles listings.
            if offset is not None and limit is not None:
                entries_list = entries_list[offset : offset + limit]
            elif limit is not None:
                entries_list = entries_list[:limit]

            return entries_list, total_count

        except PermissionError as e:
            raise AuthenticationRequired(
                f"Permission Denied. Reason: {e}. Please check your credentials in your preferences for {self.label}."
            )
        except Exception as e:
            raise MessageException(f"Problem listing file source path {path}. Reason: {e}") from e

    def on_listing_exceeded(self):
        log.warning(
            "Listing for file source %s with root %s exceeded maximum items (%d).",
            self.label,
            self.get_uri_root(),
            MAX_ITEMS_PER_LISTING,
        )

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
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        """Download a file from the fsspec filesystem to a local path."""
        fs = self._open_fs(user_context=user_context, opts=opts)
        fs.get_file(source_path, native_path)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        """Upload a file from a local path to the fsspec filesystem."""
        if opts is not None and opts.writeable is False:
            raise MessageException("Cannot write to this destination because it is configured as read-only.")
        fs = self._open_fs(user_context=user_context, opts=opts)
        fs.put_file(native_path, target_path)

    def _file_info_to_dict(self, file_path: str, info: dict) -> AnyRemoteEntry:
        """Convert fsspec file info to Galaxy's remote entry format."""
        name = os.path.basename(file_path) if file_path != "/" else "/"
        uri = self.uri_from_path(file_path)

        if info.get("type") == "directory":
            return {"class": "Directory", "name": name, "uri": uri, "path": file_path}
        else:
            size = int(info.get("size") or 0)
            mtime = info.get("mtime") or info.get("modified") or info.get("LastModified") or None
            ctime = self.to_dict_time(mtime) or ""
            return {
                "class": "File",
                "name": name,
                "size": size,
                "ctime": ctime,
                "uri": uri,
                "path": file_path,
            }

    def _serialization_props(self, user_context: OptionalUserContext = None):
        """Get effective properties for serialization."""
        effective_props = {}
        for key, val in self._props.items():
            effective_props[key] = self._evaluate_prop(val, user_context=user_context)
        return effective_props
