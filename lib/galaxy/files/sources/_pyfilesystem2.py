import abc
import functools
import logging
import os
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
)

import fs
from fs.base import FS
from typing_extensions import ClassVar

from ..sources import BaseFilesSource

log = logging.getLogger(__name__)

PACKAGE_MESSAGE = "FilesSource plugin is missing required Python PyFilesystem2 plugin package [%s]"


class PyFilesystem2FilesSource(BaseFilesSource):
    required_module: ClassVar[Optional[Type[FS]]]
    required_package: ClassVar[str]

    def __init__(self, **kwd):
        if self.required_module is None:
            raise Exception(PACKAGE_MESSAGE % self.required_package)
        props = self._parse_common_config_opts(kwd)
        self._props = props

    @abc.abstractmethod
    def _open_fs(self, user_context=None):
        """Subclasses must instantiate a PyFilesystem2 handle for this file system."""

    def _list(self, path="/", recursive=False, user_context=None):
        """Return dictionary of 'Directory's and 'File's."""

        with self._open_fs(user_context=user_context) as h:
            if recursive:
                res: List[Dict[str, Any]] = []
                for p, dirs, files in h.walk(path):
                    to_dict = functools.partial(self._resource_info_to_dict, p)
                    res.extend(map(to_dict, dirs))
                    res.extend(map(to_dict, files))
                return res
            else:
                res = h.scandir(path, namespaces=["details"])
                to_dict = functools.partial(self._resource_info_to_dict, path)
                return list(map(to_dict, res))

    def _realize_to(self, source_path, native_path, user_context=None):
        with open(native_path, "wb") as write_file:
            self._open_fs(user_context=user_context).download(source_path, write_file)

    def _write_from(self, target_path, native_path, user_context=None):
        with open(native_path, "rb") as read_file:
            openfs = self._open_fs(user_context=user_context)
            dirname = fs.path.dirname(target_path)
            if not openfs.isdir(dirname):
                openfs.makedirs(dirname)
            openfs.upload(target_path, read_file)

    def _resource_info_to_dict(self, dir_path, resource_info):
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

    def _serialization_props(self, user_context=None):
        effective_props = {}
        for key, val in self._props.items():
            effective_props[key] = self._evaluate_prop(val, user_context=user_context)
        return effective_props
