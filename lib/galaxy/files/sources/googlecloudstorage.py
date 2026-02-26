import logging
from typing import (
    Optional,
    Union,
)

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
    from gcsfs import GCSFileSystem
except ImportError:
    GCSFileSystem = None


REQUIRED_PACKAGE = "gcsfs"

log = logging.getLogger(__name__)


class GoogleCloudStorageFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    bucket_name: Union[str, TemplateExpansion]
    root_path: Union[str, TemplateExpansion, None] = None
    project: Union[str, TemplateExpansion, None] = None
    anonymous: Union[bool, TemplateExpansion, None] = True
    service_account_json: Union[str, TemplateExpansion, None] = None
    # OAuth credentials
    client_id: Union[str, TemplateExpansion, None] = None
    client_secret: Union[str, TemplateExpansion, None] = None
    token: Union[str, TemplateExpansion, None] = None
    refresh_token: Union[str, TemplateExpansion, None] = None
    token_uri: Union[str, TemplateExpansion, None] = "https://oauth2.googleapis.com/token"


class GoogleCloudStorageFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    bucket_name: str
    root_path: Optional[str] = None
    project: Optional[str] = None
    anonymous: Optional[bool] = True
    service_account_json: Optional[str] = None
    # OAuth credentials
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_uri: Optional[str] = "https://oauth2.googleapis.com/token"


class GoogleCloudStorageFilesSource(
    FsspecFilesSource[GoogleCloudStorageFileSourceTemplateConfiguration, GoogleCloudStorageFileSourceConfiguration]
):
    plugin_type = "googlecloudstorage"
    required_module = GCSFileSystem
    required_package = REQUIRED_PACKAGE

    template_config_class = GoogleCloudStorageFileSourceTemplateConfiguration
    resolved_config_class = GoogleCloudStorageFileSourceConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[GoogleCloudStorageFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ):
        if GCSFileSystem is None:
            raise self.required_package_exception

        config = context.config
        token: Union[str, dict[str, Optional[str]], None]

        if config.anonymous:
            # Use token='anon' for anonymous access to public buckets
            token = "anon"
        elif config.service_account_json:
            # Path to service account JSON file
            token = config.service_account_json
        elif config.token:
            # OAuth credentials passed as a dictionary
            token = {
                "access_token": config.token,
                "refresh_token": config.refresh_token,
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "token_uri": config.token_uri,
            }
        else:
            # Default: use application default credentials
            token = None

        fs = GCSFileSystem(
            project=config.project,
            token=token,
            **cache_options,
        )
        return fs

    def _to_bucket_path(self, path: str, config: GoogleCloudStorageFileSourceConfiguration) -> str:
        """Adapt the path to the GCS bucket format, including root_path if configured."""
        bucket = config.bucket_name
        root = (config.root_path or "").strip("/")
        if path.startswith("/"):
            path = path[1:]
        # Build path: bucket / root_path / path
        if root and path:
            return f"{bucket}/{root}/{path}"
        elif root:
            return f"{bucket}/{root}"
        elif path:
            return f"{bucket}/{path}"
        return bucket

    def _adapt_entry_path(self, filesystem_path: str) -> str:
        """Remove the GCS bucket name and root_path from the filesystem path."""
        if self.template_config.bucket_name:
            bucket = self.template_config.bucket_name
            root = (self.template_config.root_path or "").strip("/")
            full_prefix = f"{bucket}/{root}" if root else bucket
            if filesystem_path == full_prefix:
                return "/"
            return "/" + filesystem_path.removeprefix(f"{full_prefix}/")
        return "/" + filesystem_path

    def _list(
        self,
        context: FilesSourceRuntimeContext[GoogleCloudStorageFileSourceConfiguration],
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
        self,
        source_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[GoogleCloudStorageFileSourceConfiguration],
    ):
        bucket_path = self._to_bucket_path(source_path, context.config)
        super()._realize_to(source_path=bucket_path, native_path=native_path, context=context)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[GoogleCloudStorageFileSourceConfiguration],
    ):
        bucket_path = self._to_bucket_path(target_path, context.config)
        super()._write_from(target_path=bucket_path, native_path=native_path, context=context)

    def score_url_match(self, url: str):
        bucket_name = self.template_config.bucket_name
        # For security, we need to ensure that a partial match doesn't work
        if bucket_name and (url.startswith(f"gs://{bucket_name}/") or url == f"gs://{bucket_name}"):
            return len(f"gs://{bucket_name}")
        elif bucket_name and (url.startswith(f"gcs://{bucket_name}/") or url == f"gcs://{bucket_name}"):
            return len(f"gcs://{bucket_name}")
        else:
            return super().score_url_match(url)


__all__ = ("GoogleCloudStorageFilesSource",)
