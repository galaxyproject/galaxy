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
)

import fs
import fs.errors
from fs.base import FS
from typing_extensions import Unpack

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
)
from galaxy.files import OptionalUserContext
from . import (
    AnyRemoteEntry,
    BaseFilesSource,
    DEFAULT_PAGE_LIMIT,
    FilesSourceOptions,
    FilesSourceProperties,
)

log = logging.getLogger(__name__)

PACKAGE_MESSAGE = "FilesSource plugin is missing required Python PyFilesystem2 plugin package [%s]"


class PyFilesystem2FilesSource(BaseFilesSource):
    required_module: ClassVar[Optional[Type[FS]]]
    required_package: ClassVar[str]
    supports_pagination = True
    supports_search = True

    def __init__(self, **kwd: Unpack[FilesSourceProperties]):
        if self.required_module is None:
            raise Exception(PACKAGE_MESSAGE % self.required_package)
        props = self._parse_common_config_opts(kwd)
        self._props = props

    @abc.abstractmethod
    def _open_fs(self, user_context: OptionalUserContext = None, opts: Optional[FilesSourceOptions] = None):
        """Subclasses must instantiate a PyFilesystem2 handle for this file system."""

    def _list(
        self,
        path="/",
        recursive=False,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
    ) -> List[AnyRemoteEntry]:
        """Return dictionary of 'Directory's and 'File's."""
        try:
            with self._open_fs(user_context=user_context, opts=opts) as h:
                if recursive:
                    res: List[AnyRemoteEntry] = []
                    for p, dirs, files in h.walk(path, namespaces=["details"]):
                        to_dict = functools.partial(self._resource_info_to_dict, p)
                        res.extend(map(to_dict, dirs))
                        res.extend(map(to_dict, files))
                    return res
                else:
                    page = self._to_page(limit, offset)
                    filter = self._query_to_filter(query)
                    res = h.filterdir(path, namespaces=["details"], page=page, files=filter, dirs=filter)
                    to_dict = functools.partial(self._resource_info_to_dict, path)
                    return list(map(to_dict, res))
        except fs.errors.PermissionDenied as e:
            raise AuthenticationRequired(
                f"Permission Denied. Reason: {e}. Please check your credentials in your preferences for {self.label}."
            )
        except fs.errors.FSError as e:
            raise MessageException(f"Problem listing file source path {path}. Reason: {e}") from e

    def _to_page(self, limit: Optional[int] = None, offset: Optional[int] = None) -> Optional[Tuple[int, int]]:
        if limit is None and offset is None:
            return None
        limit = limit or DEFAULT_PAGE_LIMIT
        start = offset or 0
        end = start + limit
        return (start, end)

    def _query_to_filter(self, query: Optional[str]) -> Optional[List[str]]:
        if query is None:
            return None
        return [f"*{query}*"]

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        with open(native_path, "wb") as write_file:
            self._open_fs(user_context=user_context, opts=opts).download(source_path, write_file)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        with open(native_path, "rb") as read_file:
            openfs = self._open_fs(user_context=user_context, opts=opts)
            dirname = fs.path.dirname(target_path)
            if not openfs.isdir(dirname):
                openfs.makedirs(dirname)
            openfs.upload(target_path, read_file)

    def _resource_info_to_dict(self, dir_path, resource_info) -> AnyRemoteEntry:
        name = resource_info.name
        path = os.path.join(dir_path, name)
        uri = self.uri_from_path(path)
        if resource_info.is_dir:
            return {"class": "Directory", "name": name, "uri": uri, "path": path}
        else:
            created = resource_info.created
            return {
                "class": "File",
                "name": name,
                "size": resource_info.size,
                "ctime": self.to_dict_time(created),
                "uri": uri,
                "path": path,
            }

    def _serialization_props(self, user_context: OptionalUserContext = None):
        effective_props = {}
        for key, val in self._props.items():
            effective_props[key] = self._evaluate_prop(val, user_context=user_context)
        return effective_props
