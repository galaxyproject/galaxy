import functools
import logging
import os
from typing import (
    Any,
    Dict,
    List,
)

try:
    import s3fs
except ImportError:
    s3fs = None

from ..sources import BaseFilesSource

DEFAULT_ENFORCE_SYMLINK_SECURITY = True
DEFAULT_DELETE_ON_REALIZE = False

log = logging.getLogger(__name__)


class S3FsFilesSource(BaseFilesSource):
    plugin_type = "s3fs"

    def __init__(self, **kwd):
        if s3fs is None:
            raise Exception("Package s3fs unavailable but required for this file source plugin.")
        props = self._parse_common_config_opts(kwd)
        self._bucket = props.pop("bucket", "")
        self._endpoint_url = props.pop("endpoint_url", None)
        assert self._endpoint_url or self._bucket
        self._props = props

    def _list(self, path="/", recursive=True, user_context=None):
        fs = self._open_fs(user_context=user_context)
        if recursive:
            res: List[Dict[str, Any]] = []
            bucket_path = self._bucket_path(path)
            for p, dirs, files in fs.walk(bucket_path, detail=True):
                to_dict = functools.partial(self._resource_info_to_dict, p)
                res.extend(map(to_dict, dirs.values()))
                res.extend(map(to_dict, files.values()))
            return res
        else:
            bucket_path = self._bucket_path(path)
            res = fs.ls(bucket_path, detail=True)
            to_dict = functools.partial(self._resource_info_to_dict, path)
            return list(map(to_dict, res))

    def _realize_to(self, source_path, native_path, user_context=None):
        bucket_path = self._bucket_path(source_path)
        self._open_fs(user_context=user_context).download(bucket_path, native_path)

    def _write_from(self, target_path, native_path, user_context=None):
        raise NotImplementedError()

    def _bucket_path(self, path):
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self._bucket}{path}"

    def _open_fs(self, user_context=None):
        if self._endpoint_url:
            self._props.update({"client_kwargs": {"endpoint_url": self._endpoint_url}})
        fs = s3fs.S3FileSystem(**self._props)
        return fs

    def _resource_info_to_dict(self, dir_path, resource_info):
        name = os.path.basename(resource_info["name"])
        path = os.path.join(dir_path, name)
        uri = self.uri_from_path(path)
        if resource_info["type"] == "directory":
            return {"class": "Directory", "name": name, "uri": uri, "path": path}
        else:
            return {
                "class": "File",
                "name": name,
                "size": resource_info["size"],
                # should this be mtime...
                "ctime": self.to_dict_time(resource_info["LastModified"]),
                "uri": uri,
                "path": path,
            }

    def _serialization_props(self, user_context=None):
        effective_props = {}
        for key, val in self._props.items():
            effective_props[key] = self._evaluate_prop(val, user_context=user_context)
        effective_props["bucket"] = self._bucket
        return effective_props


__all__ = ("S3FsFilesSource",)
