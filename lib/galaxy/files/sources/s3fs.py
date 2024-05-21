import functools
import logging
import os
from typing import (
    cast,
    List,
    Optional,
    Tuple,
)

from typing_extensions import Unpack

from galaxy.files import OptionalUserContext
from . import (
    AnyRemoteEntry,
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
        # There is a possibility that the bucket name could be parameterized: e.g.
        # bucket: ${user.preferences['generic_s3|bucket']}
        # that's ok, because we evaluate the bucket name again later. The bucket property here will only
        # be used by `score_url_match`. In the case of a parameterized bucket name, we will always return
        # a score of 4 as the url will only match the s3:// part.
        self._bucket = props.get("bucket", "")
        self._endpoint_url = props.pop("endpoint_url", None)
        self._props = props
        if self._endpoint_url:
            self._props.update({"client_kwargs": {"endpoint_url": self._endpoint_url}})

    def _list(
        self,
        path="/",
        recursive=True,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> Tuple[List[AnyRemoteEntry], int]:
        _props = self._serialization_props(user_context)
        # we need to pop the 'bucket' here, because the argument is not recognised in a downstream function
        _bucket_name = _props.pop("bucket", "")
        fs = self._open_fs(props=_props, opts=opts)
        if recursive:
            res: List[AnyRemoteEntry] = []
            bucket_path = self._bucket_path(_bucket_name, path)
            for p, dirs, files in fs.walk(bucket_path, detail=True):
                to_dict = functools.partial(self._resource_info_to_dict, p)
                res.extend(map(to_dict, dirs.values()))
                res.extend(map(to_dict, files.values()))
            return res, len(res)
        else:
            bucket_path = self._bucket_path(_bucket_name, path)
            res = fs.ls(bucket_path, detail=True)
            to_dict = functools.partial(self._resource_info_to_dict, path)
            return list(map(to_dict, res)), len(res)

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        _props = self._serialization_props(user_context)
        _bucket_name = _props.pop("bucket", "")
        fs = self._open_fs(props=_props, opts=opts)
        bucket_path = self._bucket_path(_bucket_name, source_path)
        fs.download(bucket_path, native_path)

    def _write_from(
        self,
        target_path,
        native_path,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        _props = self._serialization_props(user_context)
        _bucket_name = _props.pop("bucket", "")
        fs = self._open_fs(props=_props, opts=opts)
        bucket_path = self._bucket_path(_bucket_name, target_path)
        fs.upload(native_path, bucket_path)

    def _bucket_path(self, bucket_name: str, path: str):
        if path.startswith("s3://"):
            return path.replace("s3://", "")
        elif not path.startswith("/"):
            path = f"/{path}"
        return f"{bucket_name}{path}"

    def _open_fs(self, props: FilesSourceProperties, opts: Optional[FilesSourceOptions] = None):
        extra_props = opts.extra_props or {} if opts else {}
        fs = s3fs.S3FileSystem(**{**props, **extra_props})
        return fs

    def _resource_info_to_dict(self, dir_path: str, resource_info) -> AnyRemoteEntry:
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

    def _serialization_props(self, user_context: OptionalUserContext = None) -> S3FsFilesSourceProperties:
        effective_props = {}
        for key, val in self._props.items():
            effective_props[key] = self._evaluate_prop(val, user_context=user_context)
        return cast(S3FsFilesSourceProperties, effective_props)

    def score_url_match(self, url: str):
        # For security, we need to ensure that a partial match doesn't work. e.g. s3://{bucket}something/myfiles
        if self._bucket and (url.startswith(f"s3://{self._bucket}/") or url == f"s3://{self._bucket}"):
            return len(f"s3://{self._bucket}")
        elif not self._bucket and url.startswith("s3://"):
            return len("s3://")
        else:
            return super().score_url_match(url)


__all__ = ("S3FsFilesSource",)
