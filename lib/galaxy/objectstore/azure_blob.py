"""
Object Store plugin for the Microsoft Azure Block Blob Storage system
"""

import logging
import os
import shutil
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

from galaxy.exceptions import (
    ObjectInvalid,
    ObjectNotFound,
)
from galaxy.util import (
    directory_hash_id,
    unlink,
)
from galaxy.util.path import safe_relpath
from . import ConcreteObjectStore
from ._util import fix_permissions
from .caching import (
    CacheTarget,
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

    def _get_size_in_azure(self, rel_path):
        try:
            properties = self._blob_client(rel_path).get_blob_properties()
            size_in_bytes = properties.size
            return size_in_bytes
        except AzureHttpError:
            log.exception("Could not get size of blob '%s' from Azure", rel_path)
            return -1

    def _in_azure(self, rel_path):
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
            if not self.cache_target.fits_in_cache(self._get_size_in_azure(rel_path)):
                log.critical(
                    "File %s is larger (%s bytes) than the configured cache allows (%s). Cannot download.",
                    rel_path,
                    self._get_size_in_azure(rel_path),
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

    def _exists(self, obj, **kwargs):
        in_cache = in_azure = False
        rel_path = self._construct_path(obj, **kwargs)
        dir_only = kwargs.get("dir_only", False)
        base_dir = kwargs.get("base_dir", None)

        # check job work directory stuff early to skip API hits.
        if dir_only and base_dir:
            if not os.path.exists(rel_path):
                os.makedirs(rel_path, exist_ok=True)
            return True

        in_cache = self._in_cache(rel_path)
        in_azure = self._in_azure(rel_path)
        # log.debug("~~~~~~ File '%s' exists in cache: %s; in azure: %s" % (rel_path, in_cache, in_azure))
        # dir_only does not get synced so shortcut the decision
        dir_only = kwargs.get("dir_only", False)
        base_dir = kwargs.get("base_dir", None)
        if dir_only:
            if in_cache or in_azure:
                return True
            else:
                return False

        # TODO: Sync should probably not be done here. Add this to an async upload stack?
        if in_cache and not in_azure:
            self._push_to_os(rel_path, source_file=self._get_cache_path(rel_path))
            return True
        elif in_azure:
            return True
        else:
            return False

    def file_ready(self, obj, **kwargs):
        """
        A helper method that checks if a file corresponding to a dataset is
        ready and available to be used. Return ``True`` if so, ``False`` otherwise.
        """
        rel_path = self._construct_path(obj, **kwargs)
        # Make sure the size in cache is available in its entirety
        if self._in_cache(rel_path):
            local_size = os.path.getsize(self._get_cache_path(rel_path))
            remote_size = self._get_size_in_azure(rel_path)
            if local_size == remote_size:
                return True
            else:
                log.debug("Waiting for dataset %s to transfer from OS: %s/%s", rel_path, local_size, remote_size)

        return False

    def _create(self, obj, **kwargs):
        if not self._exists(obj, **kwargs):
            # Pull out locally used fields
            extra_dir = kwargs.get("extra_dir", None)
            extra_dir_at_root = kwargs.get("extra_dir_at_root", False)
            dir_only = kwargs.get("dir_only", False)
            alt_name = kwargs.get("alt_name", None)

            # Construct hashed path
            rel_path = os.path.join(*directory_hash_id(self._get_object_id(obj)))

            # Optionally append extra_dir
            if extra_dir is not None:
                if extra_dir_at_root:
                    rel_path = os.path.join(extra_dir, rel_path)
                else:
                    rel_path = os.path.join(rel_path, extra_dir)

            # Create given directory in cache
            cache_dir = os.path.join(self.staging_path, rel_path)
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir, exist_ok=True)

            # Although not really necessary to create S3 folders (because S3 has
            # flat namespace), do so for consistency with the regular file system
            # S3 folders are marked by having trailing '/' so add it now
            # s3_dir = '%s/' % rel_path
            # self._push_to_os(s3_dir, from_string='')
            # If instructed, create the dataset in cache & in S3
            if not dir_only:
                rel_path = os.path.join(rel_path, alt_name if alt_name else f"dataset_{self._get_object_id(obj)}.dat")
                open(os.path.join(self.staging_path, rel_path), "w").close()
                self._push_to_os(rel_path, from_string="")
        return self

    def _empty(self, obj, **kwargs):
        if self._exists(obj, **kwargs):
            size = self._size(obj, **kwargs)
            is_empty = bool(size == 0)
            return is_empty
        else:
            raise ObjectNotFound(f"objectstore.empty, object does not exist: {str(obj)}, kwargs: {str(kwargs)}")

    def _size(self, obj, **kwargs):
        rel_path = self._construct_path(obj, **kwargs)
        if self._in_cache(rel_path):
            try:
                return os.path.getsize(self._get_cache_path(rel_path))
            except OSError as ex:
                log.info("Could not get size of file '%s' in local cache, will try Azure. Error: %s", rel_path, ex)
        elif self._exists(obj, **kwargs):
            return self._get_size_in_azure(rel_path)
        log.warning("Did not find dataset '%s', returning 0 for size", rel_path)
        return 0

    def _delete(self, obj, entire_dir=False, **kwargs):
        rel_path = self._construct_path(obj, **kwargs)
        extra_dir = kwargs.get("extra_dir", None)
        base_dir = kwargs.get("base_dir", None)
        dir_only = kwargs.get("dir_only", False)
        obj_dir = kwargs.get("obj_dir", False)
        try:
            if base_dir and dir_only and obj_dir:
                # Remove temporary data in JOB_WORK directory
                shutil.rmtree(os.path.abspath(rel_path))
                return True

            # For the case of extra_files, because we don't have a reference to
            # individual files/blobs we need to remove the entire directory structure
            # with all the files in it. This is easy for the local file system,
            # but requires iterating through each individual blob in Azure and deleing it.
            if entire_dir and extra_dir:
                shutil.rmtree(self._get_cache_path(rel_path), ignore_errors=True)
                blobs = self.service.get_container_client(self.container_name).list_blobs(name_starts_with=rel_path)
                for blob in blobs:
                    log.debug("Deleting from Azure: %s", blob)
                    self._blob_client(blob.name).delete_blob()
                return True
            else:
                # Delete from cache first
                unlink(self._get_cache_path(rel_path), ignore_errors=True)
                # Delete from S3 as well
                if self._in_azure(rel_path):
                    log.debug("Deleting from Azure: %s", rel_path)
                    self._blob_client(rel_path).delete_blob()
                    return True
        except AzureHttpError:
            log.exception("Could not delete blob '%s' from Azure", rel_path)
        except OSError:
            log.exception("%s delete error", self._get_filename(obj, **kwargs))
        return False

    def _get_data(self, obj, start=0, count=-1, **kwargs):
        rel_path = self._construct_path(obj, **kwargs)
        # Check cache first and get file if not there
        if not self._in_cache(rel_path):
            self._pull_into_cache(rel_path)
        # Read the file content from cache
        data_file = open(self._get_cache_path(rel_path))
        data_file.seek(start)
        content = data_file.read(count)
        data_file.close()
        return content

    def _get_filename(self, obj, **kwargs):
        rel_path = self._construct_path(obj, **kwargs)
        base_dir = kwargs.get("base_dir", None)
        dir_only = kwargs.get("dir_only", False)
        obj_dir = kwargs.get("obj_dir", False)
        sync_cache = kwargs.get("sync_cache", True)

        # for JOB_WORK directory
        if base_dir and dir_only and obj_dir:
            return os.path.abspath(rel_path)

        cache_path = self._get_cache_path(rel_path)
        if not sync_cache:
            return cache_path
        # Check if the file exists in the cache first, always pull if file size in cache is zero
        if self._in_cache(rel_path) and (dir_only or os.path.getsize(self._get_cache_path(rel_path)) > 0):
            return cache_path
        # Check if the file exists in persistent storage and, if it does, pull it into cache
        elif self._exists(obj, **kwargs):
            if dir_only:  # Directories do not get pulled into cache
                return cache_path
            else:
                if self._pull_into_cache(rel_path):
                    return cache_path
        # For the case of retrieving a directory only, return the expected path
        # even if it does not exist.
        # if dir_only:
        #     return cache_path
        raise ObjectNotFound(f"objectstore.get_filename, no cache_path: {str(obj)}, kwargs: {str(kwargs)}")

    def _update_from_file(self, obj, file_name=None, create=False, **kwargs):
        if create is True:
            self._create(obj, **kwargs)

        if self._exists(obj, **kwargs):
            rel_path = self._construct_path(obj, **kwargs)
            # Chose whether to use the dataset file itself or an alternate file
            if file_name:
                source_file = os.path.abspath(file_name)
                # Copy into cache
                cache_file = self._get_cache_path(rel_path)
                try:
                    if source_file != cache_file and self.cache_updated_data:
                        # FIXME? Should this be a `move`?
                        shutil.copy2(source_file, cache_file)
                    fix_permissions(self.config, cache_file)
                except OSError:
                    log.exception("Trouble copying source file '%s' to cache '%s'", source_file, cache_file)
            else:
                source_file = self._get_cache_path(rel_path)

            self._push_to_os(rel_path, source_file)

        else:
            raise ObjectNotFound(
                f"objectstore.update_from_file, object does not exist: {str(obj)}, kwargs: {str(kwargs)}"
            )

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

    @property
    def cache_target(self) -> CacheTarget:
        return CacheTarget(
            self.staging_path,
            self.cache_size,
            0.9,
        )

    def shutdown(self):
        self.cache_monitor and self.cache_monitor.shutdown()
