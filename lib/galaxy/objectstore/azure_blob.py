"""
Object Store plugin for the Microsoft Azure Block Blob Storage system
"""

import logging
import os
from datetime import (
    datetime,
    timedelta,
)
from typing import Optional

try:
    from azure.common import AzureHttpError
    from azure.storage.blob import (
        BlobSasPermissions,
        BlobServiceClient,
        generate_blob_sas,
    )
except ImportError:
    BlobServiceClient = None

from . import ConcreteObjectStore
from .caching import (
    enable_cache_monitor,
    InProcessCacheMonitor,
    parse_caching_config_dict_from_xml,
    UsesCache,
)

NO_BLOBSERVICE_ERROR_MESSAGE = (
    "ObjectStore configured, but no azure.storage.blob dependency available."
    "Please install and properly configure azure.storage.blob or modify Object Store configuration."
)

log = logging.getLogger(__name__)


def parse_config_xml(config_xml):
    try:
        auth_xml = config_xml.findall("auth")[0]

        account_name = auth_xml.get("account_name")
        account_key = auth_xml.get("account_key")
        account_url = auth_xml.get("account_url")

        container_xml = config_xml.find("container")
        container_name = container_xml.get("name")
        max_chunk_size = int(container_xml.get("max_chunk_size", 250))  # currently unused

        cache_dict = parse_caching_config_dict_from_xml(config_xml)

        tag, attrs = "extra_dir", ("type", "path")
        extra_dirs = config_xml.findall(tag)
        if not extra_dirs:
            msg = f"No {tag} element in XML tree"
            log.error(msg)
            raise Exception(msg)
        extra_dirs = [{k: e.get(k) for k in attrs} for e in extra_dirs]
        auth = {
            "account_name": account_name,
            "account_key": account_key,
        }
        if account_url:
            auth["account_url"] = account_url

        return {
            "auth": auth,
            "container": {
                "name": container_name,
                "max_chunk_size": max_chunk_size,
            },
            "cache": cache_dict,
            "extra_dirs": extra_dirs,
            "private": ConcreteObjectStore.parse_private_from_config_xml(config_xml),
        }
    except Exception:
        # Toss it back up after logging, we can't continue loading at this point.
        log.exception("Malformed ObjectStore Configuration XML -- unable to continue")
        raise


class AzureBlobObjectStore(ConcreteObjectStore, UsesCache):
    """
    Object store that stores objects as blobs in an Azure Blob Container. A local
    cache exists that is used as an intermediate location for files between
    Galaxy and Azure.
    """

    cache_monitor: Optional[InProcessCacheMonitor] = None
    store_type = "azure_blob"

    def __init__(self, config, config_dict):
        super().__init__(config, config_dict)

        auth_dict = config_dict["auth"]
        container_dict = config_dict["container"]
        cache_dict = config_dict.get("cache") or {}
        self.enable_cache_monitor, self.cache_monitor_interval = enable_cache_monitor(config, config_dict)

        self.account_name = auth_dict.get("account_name")
        self.account_url = auth_dict.get("account_url")
        self.account_key = auth_dict.get("account_key")

        self.container_name = container_dict.get("name")
        self.max_chunk_size = container_dict.get("max_chunk_size", 250)  # currently unused

        self.cache_size = cache_dict.get("size") or self.config.object_store_cache_size
        self.staging_path = cache_dict.get("path") or self.config.object_store_cache_path
        self.cache_updated_data = cache_dict.get("cache_updated_data", True)

        self._initialize()

    def _initialize(self):
        if BlobServiceClient is None:
            raise Exception(NO_BLOBSERVICE_ERROR_MESSAGE)

        self._configure_connection()

        if self.enable_cache_monitor:
            self.cache_monitor = InProcessCacheMonitor(self.cache_target, self.cache_monitor_interval)

    def to_dict(self):
        as_dict = super().to_dict()
        auth = {
            "account_name": self.account_name,
            "account_key": self.account_key,
        }
        if self.account_url:
            auth["account_url"] = self.account_url
        as_dict.update(
            {
                "auth": auth,
                "container": {
                    "name": self.container_name,
                    "max_chunk_size": self.max_chunk_size,
                },
                "cache": {
                    "size": self.cache_size,
                    "path": self.staging_path,
                    "cache_updated_data": self.cache_updated_data,
                },
            }
        )
        return as_dict

    ###################
    # Private Methods #
    ###################

    # config_xml is an ElementTree object.
    @classmethod
    def parse_xml(clazz, config_xml):
        return parse_config_xml(config_xml)

    def _configure_connection(self):
        log.debug("Configuring Connection")
        if self.account_url:
            # https://pypi.org/project/azure-storage-blob/
            service = BlobServiceClient(
                account_url=self.account_url,
                credential={"account_name": self.account_name, "account_key": self.account_key},
            )
        else:
            service = BlobServiceClient(
                account_url=f"https://{self.account_name}.blob.core.windows.net",
                credential=self.account_key,
            )
        self.service = service

    def _get_remote_size(self, rel_path):
        try:
            properties = self._blob_client(rel_path).get_blob_properties()
            size_in_bytes = properties.size
            return size_in_bytes
        except AzureHttpError:
            log.exception("Could not get size of blob '%s' from Azure", rel_path)
            return -1

    def _exists_remotely(self, rel_path: str):
        try:
            exists = self._blob_client(rel_path).exists()
        except AzureHttpError:
            log.exception("Trouble checking existence of Azure blob '%s'", rel_path)
            return False
        return exists

    def _blob_client(self, rel_path: str):
        return self.service.get_blob_client(self.container_name, rel_path)

    def _download(self, rel_path):
        local_destination = self._get_cache_path(rel_path)
        try:
            log.debug("Pulling '%s' into cache to %s", rel_path, local_destination)
            if not self.cache_target.fits_in_cache(self._get_remote_size(rel_path)):
                log.critical(
                    "File %s is larger (%s bytes) than the configured cache allows (%s). Cannot download.",
                    rel_path,
                    self._get_remote_size(rel_path),
                    self.cache_target.log_description,
                )
                return False
            else:
                with open(local_destination, "wb") as f:
                    self._blob_client(rel_path).download_blob().download_to_stream(f)
                return True
        except AzureHttpError:
            log.exception("Problem downloading '%s' from Azure", rel_path)
        return False

    def _push_to_os(self, rel_path, source_file=None, from_string=None):
        """
        Push the file pointed to by ``rel_path`` to the object store naming the blob
        ``rel_path``. If ``source_file`` is provided, push that file instead while
        still using ``rel_path`` as the blob name.
        If ``from_string`` is provided, set contents of the file to the value of
        the string.
        """
        try:
            source_file = source_file or self._get_cache_path(rel_path)

            if from_string is None and not os.path.exists(source_file):
                log.error(
                    "Tried updating blob '%s' from source file '%s', but source file does not exist.",
                    rel_path,
                    source_file,
                )
                return False

            if from_string is None and os.path.getsize(source_file) == 0:
                log.debug(
                    "Wanted to push file '%s' to azure blob '%s' but its size is 0; skipping.", source_file, rel_path
                )
                return True

            if from_string is not None:
                self._blob_client(rel_path).upload_blob(from_string, overwrite=True)
                log.debug("Pushed data from string '%s' to blob '%s'", from_string, rel_path)
            else:
                start_time = datetime.now()
                log.debug(
                    "Pushing cache file '%s' of size %s bytes to '%s'",
                    source_file,
                    os.path.getsize(source_file),
                    rel_path,
                )
                with open(source_file, "rb") as f:
                    self._blob_client(rel_path).upload_blob(f, overwrite=True)
                end_time = datetime.now()
                log.debug(
                    "Pushed cache file '%s' to blob '%s' (%s bytes transferred in %s sec)",
                    source_file,
                    rel_path,
                    os.path.getsize(source_file),
                    end_time - start_time,
                )
            return True

        except AzureHttpError:
            log.exception("Trouble pushing to Azure Blob '%s' from file '%s'", rel_path, source_file)
        return False

    ##################
    # Public Methods #
    ##################

    def _delete_remote_all(self, rel_path: str) -> bool:
        try:
            blobs = self.service.get_container_client(self.container_name).list_blobs(name_starts_with=rel_path)
            for blob in blobs:
                log.debug("Deleting from Azure: %s", blob)
                self._blob_client(blob.name).delete_blob()
            return True
        except AzureHttpError:
            log.exception("Could not delete blob '%s' from Azure", rel_path)
            return False

    def _delete_existing_remote(self, rel_path: str) -> bool:
        try:
            self._blob_client(rel_path).delete_blob()
            return True
        except AzureHttpError:
            log.exception("Could not delete blob '%s' from Azure", rel_path)
            return False

    def _get_object_url(self, obj, **kwargs):
        if self._exists(obj, **kwargs):
            rel_path = self._construct_path(obj, **kwargs)
            try:
                url = self._blob_client(rel_path).url
                # https://learn.microsoft.com/en-us/azure/storage/blobs/sas-service-create-python
                token = generate_blob_sas(
                    account_name=self.account_name,
                    account_key=self.account_key,
                    container_name=self.container_name,
                    blob_name=rel_path,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.utcnow() + timedelta(hours=1),
                )
                return f"{url}?{token}"
            except AzureHttpError:
                log.exception("Trouble generating URL for dataset '%s'", rel_path)
        return None

    def _get_store_usage_percent(self, obj):
        # Percent used for Azure blob containers is effectively zero realistically.
        # https://learn.microsoft.com/en-us/azure/storage/blobs/scalability-targets
        return 0.0

    def shutdown(self):
        self._shutdown_cache_monitor()
