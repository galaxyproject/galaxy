import logging
from typing import (
    Optional,
    Union,
)

from galaxy import exceptions
from galaxy.files.models import (
    AnyRemoteEntry,
    FilesSourceRuntimeContext,
)
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)
from galaxy.util.config_templates import TemplateExpansion

try:
    from s3fs import S3FileSystem
except ImportError:
    S3FileSystem = None


DEFAULT_ENFORCE_SYMLINK_SECURITY = True
DEFAULT_DELETE_ON_REALIZE = False
REQUIRED_PACKAGE = FS_PLUGIN_TYPE = "s3fs"

log = logging.getLogger(__name__)


class S3FSFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    anon: Union[bool, TemplateExpansion] = False
    endpoint_url: Union[str, TemplateExpansion, None] = None
    bucket: Union[str, TemplateExpansion, None] = None
    secret: Union[str, TemplateExpansion, None] = None
    key: Union[str, TemplateExpansion, None] = None


class S3FSFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    anon: bool = False
    endpoint_url: Optional[str] = None
    bucket: Optional[str] = None
    secret: Optional[str] = None
    key: Optional[str] = None


class S3FsFilesSource(FsspecFilesSource[S3FSFileSourceTemplateConfiguration, S3FSFileSourceConfiguration]):
    plugin_type = FS_PLUGIN_TYPE
    required_module = S3FileSystem
    required_package = REQUIRED_PACKAGE

    template_config_class = S3FSFileSourceTemplateConfiguration
    resolved_config_class = S3FSFileSourceConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[S3FSFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ):
        if S3FileSystem is None:
            raise self.required_package_exception

        config = context.config
        client_kwargs = {"endpoint_url": config.endpoint_url} if config.endpoint_url else None
        fs = S3FileSystem(
            anon=config.anon,
            key=config.key,
            secret=config.secret,
            client_kwargs=client_kwargs,
            **cache_options,
        )
        return fs

    def _to_bucket_path(self, path: str, config: S3FSFileSourceConfiguration) -> str:
        """Adapt the path to the S3 bucket format."""
        if path.startswith("s3://"):
            return path.replace("s3://", "")
        bucket = config.bucket
        if not bucket and not path.startswith("s3://"):
            raise exceptions.MessageException("Bucket name is required for S3FsFilesSource.")
        return self._bucket_path(bucket or "", path)

    def _adapt_entry_path(self, filesystem_path: str) -> str:
        """Remove the S3 bucket name from the filesystem path."""
        if self.template_config.bucket:
            bucket_prefix = f"{self.template_config.bucket}/"
            return filesystem_path.replace(bucket_prefix, "", 1)
        return filesystem_path

    def _list(
        self,
        context: FilesSourceRuntimeContext[S3FSFileSourceConfiguration],
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        bucket_path = self._to_bucket_path(path, context.config)
        return super()._list(
            context=context,
            path=bucket_path,
            recursive=recursive,
            limit=limit,
            offset=offset,
            query=query,
            sort_by=sort_by,
        )

    def _realize_to(
        self, source_path: str, native_path: str, context: FilesSourceRuntimeContext[S3FSFileSourceConfiguration]
    ):
        bucket_path = self._to_bucket_path(source_path, context.config)
        super()._realize_to(source_path=bucket_path, native_path=native_path, context=context)

    def _write_from(
        self, target_path: str, native_path: str, context: FilesSourceRuntimeContext[S3FSFileSourceConfiguration]
    ):
        bucket_path = self._to_bucket_path(target_path, context.config)
        super()._write_from(target_path=bucket_path, native_path=native_path, context=context)

    def _bucket_path(self, bucket_name: str, path: str):
        if path.startswith("s3://"):
            return path.replace("s3://", "")
        elif not path.startswith("/"):
            path = f"/{path}"
        return f"{bucket_name}{path}"

    def score_url_match(self, url: str):
        # We need to use template_config here because this is called before the template is expanded.
        bucket_name = self.template_config.bucket
        # For security, we need to ensure that a partial match doesn't work. e.g. s3://{bucket}something/myfiles
        if bucket_name and (url.startswith(f"s3://{bucket_name}/") or url == f"s3://{bucket_name}"):
            return len(f"s3://{bucket_name}")
        elif not bucket_name and url.startswith("s3://"):
            return len("s3://")
        else:
            return super().score_url_match(url)


__all__ = ("S3FsFilesSource",)
