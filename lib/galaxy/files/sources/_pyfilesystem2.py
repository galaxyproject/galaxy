import abc
import functools
import logging
import os
from typing import (
    ClassVar,
    Optional,
)

import fs
import fs.errors
from fs.base import FS

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
)
from galaxy.files import OptionalUserContext
from . import (
    AnyRemoteEntry,
    BaseFilesSource,
    DEFAULT_PAGE_LIMIT,
    FileSourceConfiguration,
    FilesSourceOptions,
    RemoteDirectory,
    RemoteFile,
)

log = logging.getLogger(__name__)

PACKAGE_MESSAGE = "FilesSource plugin is missing required Python PyFilesystem2 plugin package [%s]"


class PyFilesystem2FilesSource(BaseFilesSource):
    required_module: ClassVar[Optional[type[FS]]]
    required_package: ClassVar[str]
    supports_pagination = True
    supports_search = True
    allow_key_error_on_empty_directories = False  # work around a bug in webdav

    def __init__(self, config: FileSourceConfiguration):
        if self.required_module is None:
            raise self.required_package_exception
        super().__init__(config)

    @property
    def required_package_exception(self) -> Exception:
        return Exception(PACKAGE_MESSAGE % self.required_package)

    @abc.abstractmethod
    def _open_fs(self) -> FS:
        """Subclasses must instantiate a PyFilesystem2 handle for this file system.

        All the required properties should be already set in the config.
        """

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
    ) -> tuple[list[AnyRemoteEntry], int]:
        """Return dictionary of 'Directory's and 'File's."""
        try:
            self.update_config_from_options(opts, user_context)
            with self._open_fs() as h:
                if recursive:
                    recursive_result: list[AnyRemoteEntry] = []
                    try:
                        for p, dirs, files in h.walk(path, namespaces=["details"]):
                            to_dict = functools.partial(self._resource_info_to_dict, p)
                            recursive_result.extend(map(to_dict, dirs))
                            recursive_result.extend(map(to_dict, files))
                    except KeyError:
                        if not self.allow_key_error_on_empty_directories:
                            raise
                    return recursive_result, len(recursive_result)
                else:
                    page = self._to_page(limit, offset)
                    filter = self._query_to_filter(query)
                    count = self._get_total_matches_count(h, path, filter)
                    result = h.filterdir(path, namespaces=["details"], page=page, files=filter, dirs=filter)
                    to_dict = functools.partial(self._resource_info_to_dict, path)
                    return list(map(to_dict, result)), count
        except fs.errors.PermissionDenied as e:
            raise AuthenticationRequired(
                f"Permission Denied. Reason: {e}. Please check your credentials in your preferences for {self.label}."
            )
        except fs.errors.FSError as e:
            raise MessageException(f"Problem listing file source path {path}. Reason: {e}") from e

    def _get_total_matches_count(self, fs: FS, path: str, filter: Optional[list[str]] = None) -> int:
        return sum(1 for _ in fs.filterdir(path, namespaces=["basic"], files=filter, dirs=filter))

    def _to_page(self, limit: Optional[int] = None, offset: Optional[int] = None) -> Optional[tuple[int, int]]:
        if limit is None and offset is None:
            return None
        limit = limit or DEFAULT_PAGE_LIMIT
        start = offset or 0
        end = start + limit
        return (start, end)

    def _query_to_filter(self, query: Optional[str]) -> Optional[list[str]]:
        if not query:
            return None
        return [f"*{query}*"]

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        self.update_config_from_options(opts, user_context)
        with open(native_path, "wb") as write_file:
            self._open_fs().download(source_path, write_file)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        self.update_config_from_options(opts, user_context)
        with open(native_path, "rb") as read_file:
            openfs = self._open_fs()
            dirname = fs.path.dirname(target_path)
            if not openfs.isdir(dirname):
                openfs.makedirs(dirname)
            openfs.upload(target_path, read_file)

    def _resource_info_to_dict(self, dir_path, resource_info) -> AnyRemoteEntry:
        name = str(resource_info.name)
        path = os.path.join(dir_path, name)
        uri = self.uri_from_path(path)
        if resource_info.is_dir:
            return RemoteDirectory(name=name, uri=uri, path=path)
        else:
            created = resource_info.created
            return RemoteFile(
                name=name,
                size=resource_info.size,
                ctime=self.to_dict_time(created),
                uri=uri,
                path=path,
            )
