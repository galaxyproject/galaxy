import abc
import logging
import os
from typing import (
    ClassVar,
    List,
    Optional,
    Tuple,
    Type,
)

from fsspec import AbstractFileSystem
from typing_extensions import Unpack

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


class FsspecFilesSource(BaseFilesSource):
    required_module: ClassVar[Optional[Type[AbstractFileSystem]]]
    required_package: ClassVar[str]
    supports_pagination = True
    supports_search = True

    def __init__(self, **kwd: Unpack[FilesSourceProperties]):
        if self.required_module is None:
            raise Exception(PACKAGE_MESSAGE % self.required_package)
        props = self._parse_common_config_opts(kwd)
        self._props = props

    @abc.abstractmethod
    def _open_fs(
        self, user_context: OptionalUserContext = None, opts: Optional[FilesSourceOptions] = None
    ) -> AbstractFileSystem:
        """Subclasses must instantiate an fsspec AbstractFileSystem handle for this file system."""

    def _list(
        self,
        path="/",
        recursive=False,  # Ignoring recursive for now
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> Tuple[List[AnyRemoteEntry], int]:
        """Return dictionary of 'Directory's and 'File's."""
        try:
            fs = self._open_fs(user_context=user_context, opts=opts)
            try:
                entries = fs.ls(path, detail=True)
                entries_list = []
                for entry in entries:
                    entry_path = entry.get("name", entry.get("path", ""))
                    entries_list.append(self._file_info_to_dict(entry_path, entry))

                # Apply query filtering if provided
                if query:
                    entries_list = [entry for entry in entries_list if query.lower() in entry["name"].lower()]

                # Apply pagination
                total_count = len(entries_list)
                if limit is not None and offset is not None:
                    start = offset
                    end = offset + limit
                    entries_list = entries_list[start:end]
                elif limit is not None:
                    entries_list = entries_list[:limit]

                return entries_list, total_count
            except (FileNotFoundError, PermissionError):
                return [], 0

        except PermissionError as e:
            raise AuthenticationRequired(
                f"Permission Denied. Reason: {e}. Please check your credentials in your preferences for {self.label}."
            )
        except Exception as e:
            raise MessageException(f"Problem listing file source path {path}. Reason: {e}") from e

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        """Download a file from the fsspec filesystem to a local path."""
        fs = self._open_fs(user_context=user_context, opts=opts)
        fs.get(source_path, native_path)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        """Upload a file from a local path to the fsspec filesystem."""
        fs = self._open_fs(user_context=user_context, opts=opts)

        # Create parent directories if they don't exist
        parent_dir = os.path.dirname(target_path)
        if parent_dir and parent_dir != "/" and not fs.exists(parent_dir):
            fs.makedirs(parent_dir, exist_ok=True)

        fs.put(native_path, target_path)

    def _file_info_to_dict(self, file_path: str, info: dict) -> AnyRemoteEntry:
        """Convert fsspec file info to Galaxy's remote entry format."""
        name = os.path.basename(file_path) if file_path != "/" else "/"
        uri = self.uri_from_path(file_path)

        if info.get("type") == "directory":
            return {"class": "Directory", "name": name, "uri": uri, "path": file_path}
        else:
            size = int(info.get("size", 0))
            # Handle different possible timestamp fields
            mtime = info.get("mtime", info.get("modified", info.get("LastModified")))
            ctime_formatted = self.to_dict_time(mtime)
            ctime = ctime_formatted if ctime_formatted is not None else ""

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
