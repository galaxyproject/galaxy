import functools
import logging
import os
from typing import (
    Optional,
    Union,
)

from galaxy import exceptions
from galaxy.files.models import (
    AnyRemoteEntry,
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
    RemoteDirectory,
    RemoteFile,
)
from galaxy.util.config_templates import TemplateExpansion

try:
    import s3fs
except ImportError:
    s3fs = None

from . import BaseFilesSource

DEFAULT_ENFORCE_SYMLINK_SECURITY = True
DEFAULT_DELETE_ON_REALIZE = False
FS_PLUGIN_TYPE = "s3fs"

log = logging.getLogger(__name__)


class S3FSFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    anon: Union[bool, TemplateExpansion] = False
    endpoint_url: Union[str, TemplateExpansion, None] = None
    bucket: Union[str, TemplateExpansion, None] = None
    secret: Union[str, TemplateExpansion, None] = None
    key: Union[str, TemplateExpansion, None] = None


class S3FSFileSourceConfiguration(BaseFileSourceConfiguration):
    anon: bool = False
    endpoint_url: Optional[str] = None
    bucket: Optional[str] = None
    secret: Optional[str] = None
    key: Optional[str] = None


class S3FsFilesSource(BaseFilesSource[S3FSFileSourceTemplateConfiguration, S3FSFileSourceConfiguration]):
    plugin_type = FS_PLUGIN_TYPE

    template_config_class = S3FSFileSourceTemplateConfiguration
    resolved_config_class = S3FSFileSourceConfiguration

    def _open_fs(self):
        if s3fs is None:
            raise Exception("Missing s3fs package, please install it to use S3 file sources.")
        client_kwargs = {"endpoint_url": self.config.endpoint_url} if self.config.endpoint_url else None
        fs = s3fs.S3FileSystem(
            anon=self.config.anon,
            key=self.config.key,
            secret=self.config.secret,
            client_kwargs=client_kwargs,
            listings_expiry_time=self.listings_expiry_time,
        )
        return fs

    @property
    def listings_expiry_time(self) -> Optional[int]:
        """Return the listings expiry time for this file source."""
        return self.config.file_sources_config.listings_expiry_time

    def _list(
        self,
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        _bucket_name = self.config.bucket or ""
        fs = self._open_fs()
        if recursive:
            res: list[AnyRemoteEntry] = []
            bucket_path = self._bucket_path(_bucket_name, path)
            for p, dirs, files in fs.walk(bucket_path, detail=True):
                to_dict = functools.partial(self._resource_info_to_dict, p)
                res.extend(map(to_dict, dirs.values()))
                res.extend(map(to_dict, files.values()))
            return res, len(res)
        else:
            bucket_path = self._bucket_path(_bucket_name, path)
            try:
                res = fs.ls(bucket_path, detail=True)
            except Exception as e:
                raise exceptions.MessageException(f"Error listing {bucket_path}: {e}")
            to_dict = functools.partial(self._resource_info_to_dict, path)
            return list(map(to_dict, res)), len(res)

    def _realize_to(self, source_path: str, native_path: str):
        _bucket_name = self.config.bucket or ""
        fs = self._open_fs()
        bucket_path = self._bucket_path(_bucket_name, source_path)
        fs.download(bucket_path, native_path)

    def _write_from(self, target_path, native_path):
        _bucket_name = self.config.bucket or ""
        fs = self._open_fs()
        bucket_path = self._bucket_path(_bucket_name, target_path)
        fs.upload(native_path, bucket_path)

    def _bucket_path(self, bucket_name: str, path: str):
        if path.startswith("s3://"):
            return path.replace("s3://", "")
        elif not path.startswith("/"):
            path = f"/{path}"
        return f"{bucket_name}{path}"

    def _resource_info_to_dict(self, dir_path: str, resource_info) -> AnyRemoteEntry:
        name = str(os.path.basename(resource_info["name"]))
        path = os.path.join(dir_path, name)
        uri = self.uri_from_path(path)
        if resource_info["type"] == "directory":
            return RemoteDirectory(name=name, uri=uri, path=path)
        else:
            return RemoteFile(
                name=name,
                size=resource_info["size"],
                ctime=self.to_dict_time(resource_info["LastModified"]),
                uri=uri,
                path=path,
            )

    def score_url_match(self, url: str):
        # For security, we need to ensure that a partial match doesn't work. e.g. s3://{bucket}something/myfiles
        if self.config.bucket and (
            url.startswith(f"s3://{self.config.bucket}/") or url == f"s3://{self.config.bucket}"
        ):
            return len(f"s3://{self.config.bucket}")
        elif not self.config.bucket and url.startswith("s3://"):
            return len("s3://")
        else:
            return super().score_url_match(url)


__all__ = ("S3FsFilesSource",)
