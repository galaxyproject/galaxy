"""
Object Store plugin for the Microsoft Azure Block Blob Storage system
"""

import logging
import os
from datetime import (
    datetime,
    timedelta,
    timezone,
)

try:
    from azure.common import AzureHttpError
    from azure.storage.blob import (
        BlobSasPermissions,
        BlobServiceClient,
        generate_blob_sas,
    )
except ImportError:
    BlobServiceClient = None  # type: ignore[assignment,unused-ignore,misc]

from ._caching_base import CachingConcreteObjectStore
from .caching import (
    enable_cache_monitor,
    parse_caching_config_dict_from_xml,
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

        transfer_xml = config_xml.findall("transfer")
        if not transfer_xml:
            transfer_xml = {}
        else:
            transfer_xml = transfer_xml[0]
        transfer_dict = {}
        for key in [
            "max_concurrency",
            "download_max_concurrency",
            "upload_max_concurrency",
            "max_single_put_size",
            "max_single_get_size",
            "max_block_size",
        ]:
            value = transfer_xml.get(key)
            if transfer_xml.get(key) is not None:
                transfer_dict[key] = value

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

        config_dict = {
            "auth": auth,
            "container": {
                "name": container_name,
            },
            "cache": cache_dict,
            "transfer": transfer_dict,
            "extra_dirs": extra_dirs,
            "private": CachingConcreteObjectStore.parse_private_from_config_xml(config_xml),
        }
        name = config_xml.attrib.get("name", None)
        if name is not None:
            config_dict["name"] = name
        device = config_xml.attrib.get("device", None)
        config_dict["device"] = device
        return config_dict
    except Exception:
        # Toss it back up after logging, we can't continue loading at this point.
        log.exception("Malformed ObjectStore Configuration XML -- unable to continue")
        raise


class AzureBlobObjectStore(CachingConcreteObjectStore):
    """
    Object store that stores objects as blobs in an Azure Blob Container. A local
    cache exists that is used as an intermediate location for files between
    Galaxy and Azure.
    """

    store_type = "azure_blob"
    cloud = True

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
        raw_transfer_dict = config_dict.get("transfer", {})
        typed_transfer_dict = {}
        for key in [
            "max_concurrency",
            "download_max_concurrency",
            "upload_max_concurrency",
            "max_single_put_size",
            "max_single_get_size",
            "max_block_size",
        ]:
            value = raw_transfer_dict.get(key)
            if value is not None:
                typed_transfer_dict[key] = int(value)
        self.transfer_dict = typed_transfer_dict

        self.cache_size = cache_dict.get("size") or self.config.object_store_cache_size
        self.staging_path = cache_dict.get("path") or self.config.object_store_cache_path
        self.cache_updated_data = cache_dict.get("cache_updated_data", True)

        self._initialize()

    def _initialize(self):
        if BlobServiceClient is None:
            raise Exception(NO_BLOBSERVICE_ERROR_MESSAGE)

        self._configure_connection()
        self._ensure_staging_path_writable()
        self._start_cache_monitor_if_needed()

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
                },
                "transfer": self.transfer_dict,
                "cache": {
                    "size": self.cache_size,
                    "path": self.staging_path,
                    "cache_updated_data": self.cache_updated_data,
                },
            }
        )
        return as_dict

    # config_xml is an ElementTree object.
    @classmethod
    def parse_xml(clazz, config_xml):
        return parse_config_xml(config_xml)

    def _configure_connection(self):
        log.debug("Configuring Connection")
        extra_kwds = {}
        for key in [
            "max_single_put_size",
            "max_single_get_size",
            "max_block_size",
        ]:
            if key in self.transfer_dict:
                extra_kwds[key] = self.transfer_dict[key]

        if self.account_url:
            # https://pypi.org/project/azure-storage-blob/
            service = BlobServiceClient(
                account_url=self.account_url,
                credential={"account_name": self.account_name, "account_key": self.account_key},
                **extra_kwds,
            )
        else:
            service = BlobServiceClient(
                account_url=f"https://{self.account_name}.blob.core.windows.net",
                credential=self.account_key,
                **extra_kwds,
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

    def _blobs_from(self, rel_path):
        return self.service.get_container_client(self.container_name).list_blobs(name_starts_with=rel_path)

    def _exists_remotely(self, rel_path: str):
        try:
            is_dir = rel_path[-1] == "/"
            if is_dir:
                blobs = self._blobs_from(rel_path)
                if blobs:
                    return True
                else:
                    return False
            else:
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
            if not self._caching_allowed(rel_path):
                return False
            else:
                self._download_to_file(rel_path, local_destination)
                return True
        except AzureHttpError:
            log.exception("Problem downloading '%s' from Azure", rel_path)
        return False

    def _download_to_file(self, rel_path, local_destination):
        kwd = {}
        max_concurrency = self.transfer_dict.get("download_max_concurrency") or self.transfer_dict.get(
            "max_concurrency"
        )
        if max_concurrency is not None:
            kwd["max_concurrency"] = max_concurrency
        with open(local_destination, "wb") as f:
            self._blob_client(rel_path).download_blob().download_to_stream(f, **kwd)

    def _download_directory_into_cache(self, rel_path, cache_path):
        blobs = self._blobs_from(rel_path)
        for blob in blobs:
            key = blob.name
            local_file_path = os.path.join(cache_path, os.path.relpath(key, rel_path))

            # Create directories if they don't exist
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

            # Download the file
            self._download_to_file(key, local_file_path)

    def _push_string_to_path(self, rel_path: str, from_string: str) -> bool:
        try:
            self._blob_client(rel_path).upload_blob(from_string, overwrite=True)
            return True
        except AzureHttpError:
            log.exception("Trouble pushing to Azure Blob '%s' from string", rel_path)
            return False

    def _push_file_to_path(self, rel_path: str, source_file: str) -> bool:
        try:
            with open(source_file, "rb") as f:
                kwd = {}
                max_concurrency = self.transfer_dict.get("upload_max_concurrency") or self.transfer_dict.get(
                    "max_concurrency"
                )
                if max_concurrency is not None:
                    kwd["max_concurrency"] = max_concurrency
                self._blob_client(rel_path).upload_blob(f, overwrite=True, **kwd)
            return True
        except AzureHttpError:
            log.exception("Trouble pushing to Azure Blob '%s' from file '%s'", rel_path, source_file)
            return False

    def _delete_remote_all(self, rel_path: str) -> bool:
        try:
            blobs = self._blobs_from(rel_path)
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
                    expiry=datetime.now(tz=timezone.utc) + timedelta(hours=1),
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
