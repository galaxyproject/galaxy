import functools
import logging
import os
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
)

from typing_extensions import Unpack

from . import (
    FilesSourceOptions,
    FilesSourceProperties,
)

try:
    import s3fs
except ImportError:
    s3fs = None

from . import BaseFilesSource

DEFAULT_ENFORCE_SYMLINK_SECURITY = True
DEFAULT_DELETE_ON_REALIZE = False

log = logging.getLogger(__name__)


class S3FsFilesSourceProperties(FilesSourceProperties, total=False):
    bucket: str
    endpoint_url: int
    user: str
    passwd: str
    client_kwargs: dict  # internally computed. Should not be specified in config file


class S3FsFilesSource(BaseFilesSource):
    plugin_type = "s3fs"

    def __init__(self, **kwd: Unpack[S3FsFilesSourceProperties]):
        if s3fs is None:
            raise Exception("Package s3fs unavailable but required for this file source plugin.")
        props: S3FsFilesSourceProperties = cast(S3FsFilesSourceProperties, self._parse_common_config_opts(kwd))
        self._bucket = props.pop("bucket", "")
        self._endpoint_url = props.pop("endpoint_url", None)
        self._props = props
        if self._endpoint_url:
            self._props.update({"client_kwargs": {"endpoint_url": self._endpoint_url}})

    def _list(self, path="/", recursive=True, user_context=None, opts: Optional[FilesSourceOptions] = None):
        fs = self._open_fs(user_context=user_context, opts=opts)
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

    def _realize_to(self, source_path, native_path, user_context=None, opts: Optional[FilesSourceOptions] = None):
        bucket_path = self._bucket_path(source_path)
        self._open_fs(user_context=user_context, opts=opts).download(bucket_path, native_path)

    def _write_from(self, target_path, native_path, user_context=None, opts: Optional[FilesSourceOptions] = None):
        raise NotImplementedError()

    def _bucket_path(self, path: str):
        if path.startswith("s3://"):
            return path.replace("s3://", "")
        elif not path.startswith("/"):
            path = f"/{path}"
        return f"{self._bucket}{path}"

    def _open_fs(self, user_context=None, opts: Optional[FilesSourceOptions] = None):
        extra_props = opts.extra_props or {} if opts else {}
        fs = s3fs.S3FileSystem(**{**self._props, **extra_props})
        return fs

    def _resource_info_to_dict(self, dir_path: str, resource_info):
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

    def score_url_match(self, url: str):
        # For security, we need to ensure that a partial match doesn't work. e.g. s3://{bucket}something/myfiles
        if self._bucket and (url.startswith(f"s3://{self._bucket}/") or url == f"s3://{self._bucket}"):
            return len(f"s3://{self._bucket}")
        elif not self._bucket and url.startswith("s3://"):
            return len("s3://")
        else:
            return super().score_url_match(url)


__all__ = ("S3FsFilesSource",)
