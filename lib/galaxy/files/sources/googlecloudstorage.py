try:
    from fs_gcsfs import GCSFS
    from google.cloud.storage import Client
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
except ImportError:
    GCSFS = None

import os
from typing import (
    Optional,
    Union,
)

from galaxy.files.models import (
    AnyRemoteEntry,
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
    FilesSourceRuntimeContext,
    RemoteDirectory,
    RemoteFile,
)
from galaxy.util.config_templates import TemplateExpansion
from ._pyfilesystem2 import PyFilesystem2FilesSource


class GoogleCloudStorageFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    bucket_name: Union[str, TemplateExpansion]
    root_path: Union[str, TemplateExpansion, None] = None
    project: Union[str, TemplateExpansion, None] = None
    anonymous: Union[bool, TemplateExpansion, None] = True
    service_account_json: Union[str, TemplateExpansion, None] = None
    token: Union[str, TemplateExpansion, None] = None
    token_uri: Union[str, TemplateExpansion, None] = None
    client_id: Union[str, TemplateExpansion, None] = None
    client_secret: Union[str, TemplateExpansion, None] = None
    refresh_token: Union[str, TemplateExpansion, None] = None


class GoogleCloudStorageFileSourceConfiguration(BaseFileSourceConfiguration):
    bucket_name: str
    root_path: Optional[str] = None
    project: Optional[str] = None
    anonymous: Optional[bool] = True
    service_account_json: Optional[str] = None
    token: Optional[str] = None
    token_uri: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token: Optional[str] = None


class GoogleCloudStorageFilesSource(
    PyFilesystem2FilesSource[
        GoogleCloudStorageFileSourceTemplateConfiguration, GoogleCloudStorageFileSourceConfiguration
    ]
):
    plugin_type = "googlecloudstorage"
    required_module = GCSFS
    required_package = "fs-gcsfs"

    template_config_class = GoogleCloudStorageFileSourceTemplateConfiguration
    resolved_config_class = GoogleCloudStorageFileSourceConfiguration

    def _open_fs(self, context: FilesSourceRuntimeContext[GoogleCloudStorageFileSourceConfiguration]):
        if GCSFS is None:
            raise self.required_package_exception

        config = context.config
        if config.anonymous:
            client = Client.create_anonymous_client()
        elif config.service_account_json:
            credentials = service_account.Credentials.from_service_account_file(config.service_account_json)
            client = Client(project=config.project, credentials=credentials)
        elif config.token:
            client = Client(
                project=config.project,
                credentials=Credentials(
                    token=config.token,
                    token_uri=config.token_uri,
                    client_id=config.client_id,
                    client_secret=config.client_secret,
                    refresh_token=config.refresh_token,
                ),
            )

        handle = GCSFS(bucket_name=config.bucket_name, root_path=config.root_path or "", retry=0, client=client)
        return handle

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
        """
        Override base class _list to work around fs_gcsfs limitation with virtual directories.

        GCS doesn't require directory marker objects, but fs_gcsfs's getinfo() requires them.
        This implementation uses the GCS API directly to list blobs, bypassing the problematic
        getinfo() validation that fails for virtual directories.
        """
        if recursive:
            # For recursive listing, fall back to the base implementation
            return super()._list(context, path, recursive, write_intent, limit, offset, query, sort_by)

        # Open filesystem to get access to the bucket
        with self._open_fs(context) as fs_handle:
            # Access the bucket from the GCSFS object
            bucket = fs_handle.bucket

            # Convert path to GCS prefix format
            # Remove leading/trailing slashes and add trailing slash for directory prefix
            normalized_path = path.strip("/")
            if normalized_path:
                prefix = normalized_path + "/"
            else:
                prefix = ""

            # List blobs with delimiter to get immediate children only (non-recursive)
            delimiter = "/"

            # Collect directories (prefixes) and files (blobs)
            entries: list[AnyRemoteEntry] = []

            # First iterator: Get directories from prefixes
            page_iterator_dirs = bucket.list_blobs(prefix=prefix, delimiter=delimiter)
            for page in page_iterator_dirs.pages:
                for dir_prefix in page.prefixes:
                    # Remove the parent prefix and trailing slash to get just the dir name
                    dir_name = dir_prefix[len(prefix) :].rstrip("/")
                    if dir_name:
                        full_path = os.path.join("/", normalized_path, dir_name) if normalized_path else f"/{dir_name}"
                        uri = self.uri_from_path(full_path)
                        entries.append(RemoteDirectory(name=dir_name, uri=uri, path=full_path))

            # Second iterator: Get files from blobs
            page_iterator_files = bucket.list_blobs(prefix=prefix, delimiter=delimiter)
            for blob in page_iterator_files:
                # Skip directory marker objects (empty blobs ending with /)
                if blob.name.endswith("/"):
                    continue

                # Get just the filename (remove prefix)
                file_name = blob.name[len(prefix) :]
                if file_name:
                    full_path = os.path.join("/", normalized_path, file_name) if normalized_path else f"/{file_name}"
                    uri = self.uri_from_path(full_path)

                    # Convert blob metadata to RemoteFile
                    ctime = None
                    if blob.time_created:
                        ctime = blob.time_created.isoformat()

                    entries.append(
                        RemoteFile(name=file_name, size=blob.size or 0, ctime=ctime, uri=uri, path=full_path)
                    )

            # Apply query filter if provided
            if query:
                query_lower = query.lower()
                entries = [e for e in entries if query_lower in e.name.lower()]

            # Get total count before pagination
            total_count = len(entries)

            # Apply pagination
            if offset is not None or limit is not None:
                start = offset or 0
                end = start + limit if limit is not None else None
                entries = entries[start:end]

            return entries, total_count

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[GoogleCloudStorageFileSourceConfiguration],
    ):
        """
        Override to download files directly from GCS, bypassing fs_gcsfs's directory marker checks.
        """
        with self._open_fs(context) as fs_handle:
            bucket = fs_handle.bucket

            # Convert path to GCS blob key
            normalized_path = source_path.strip("/")

            # Get the blob
            blob = bucket.get_blob(normalized_path)
            if not blob:
                raise Exception(f"File not found: {source_path}")

            # Download directly to file
            with open(native_path, "wb") as write_file:
                blob.download_to_file(write_file)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[GoogleCloudStorageFileSourceConfiguration],
    ):
        """
        Override to upload files directly to GCS, bypassing fs_gcsfs's directory marker checks.
        """
        with self._open_fs(context) as fs_handle:
            bucket = fs_handle.bucket

            # Convert path to GCS blob key
            normalized_path = target_path.strip("/")

            # Create blob and upload
            blob = bucket.blob(normalized_path)
            with open(native_path, "rb") as read_file:
                blob.upload_from_file(read_file)


__all__ = ("GoogleCloudStorageFilesSource",)
