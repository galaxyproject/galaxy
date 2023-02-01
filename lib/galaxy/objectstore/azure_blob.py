"""
Object Store plugin for the Microsoft Azure Block Blob Storage system
"""

import logging
import os
import shutil
import threading
import time
from datetime import datetime

try:
    from azure.common import AzureHttpError
    from azure.storage import CloudStorageAccount
    from azure.storage.blob import BlockBlobService
    from azure.storage.blob.models import Blob
except ImportError:
    BlockBlobService = None

from galaxy.exceptions import (
    ObjectInvalid,
    ObjectNotFound,
)
from galaxy.util import (
    directory_hash_id,
    umask_fix_perms,
    unlink,
)
from galaxy.util.path import safe_relpath
from galaxy.util.sleeper import Sleeper
from . import (
    ConcreteObjectStore,
    convert_bytes,
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

        container_xml = config_xml.find("container")
        container_name = container_xml.get("name")
        max_chunk_size = int(container_xml.get("max_chunk_size", 250))  # currently unused

        c_xml = config_xml.findall("cache")[0]
        cache_size = float(c_xml.get("size", -1))
        staging_path = c_xml.get("path", None)

        tag, attrs = "extra_dir", ("type", "path")
        extra_dirs = config_xml.findall(tag)
        if not extra_dirs:
            msg = f"No {tag} element in XML tree"
            log.error(msg)
            raise Exception(msg)
        extra_dirs = [{k: e.get(k) for k in attrs} for e in extra_dirs]
        return {
            "auth": {
                "account_name": account_name,
                "account_key": account_key,
            },
            "container": {
                "name": container_name,
                "max_chunk_size": max_chunk_size,
            },
            "cache": {
                "size": cache_size,
                "path": staging_path,
            },
            "extra_dirs": extra_dirs,
        }
    except Exception:
        # Toss it back up after logging, we can't continue loading at this point.
        log.exception("Malformed ObjectStore Configuration XML -- unable to continue")
        raise


class AzureBlobObjectStore(ConcreteObjectStore):
    """
    Object store that stores objects as blobs in an Azure Blob Container. A local
    cache exists that is used as an intermediate location for files between
    Galaxy and Azure.
    """

    store_type = "azure_blob"

    def __init__(self, config, config_dict):
        super().__init__(config, config_dict)

        self.transfer_progress = 0

        auth_dict = config_dict["auth"]
        container_dict = config_dict["container"]
        cache_dict = config_dict["cache"]

        self.account_name = auth_dict.get("account_name")
        self.account_key = auth_dict.get("account_key")

        self.container_name = container_dict.get("name")
        self.max_chunk_size = container_dict.get("max_chunk_size", 250)  # currently unused

        self.cache_size = cache_dict.get("size", -1)
        self.staging_path = cache_dict.get("path") or self.config.object_store_cache_path

        self._initialize()

    def _initialize(self):
        if BlockBlobService is None:
            raise Exception(NO_BLOBSERVICE_ERROR_MESSAGE)

        self._configure_connection()

        # Clean cache only if value is set in galaxy.ini
        if self.cache_size != -1:
            # Convert GBs to bytes for comparison
            self.cache_size = self.cache_size * 1073741824
            # Helper for interruptable sleep
            self.sleeper = Sleeper()
            self.cache_monitor_thread = threading.Thread(target=self.__cache_monitor)
            self.cache_monitor_thread.start()
            log.info("Cache cleaner manager started")

    def to_dict(self):
        as_dict = super().to_dict()
        as_dict.update(
            {
                "auth": {
                    "account_name": self.account_name,
                    "account_key": self.account_key,
                },
                "container": {
                    "name": self.container_name,
                    "max_chunk_size": self.max_chunk_size,
                },
                "cache": {
                    "size": self.cache_size,
                    "path": self.staging_path,
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
        self.account = CloudStorageAccount(self.account_name, self.account_key)
        self.service = self.account.create_block_blob_service()

    def _construct_path(
        self,
        obj,
        base_dir=None,
        dir_only=None,
        extra_dir=None,
        extra_dir_at_root=False,
        alt_name=None,
        obj_dir=False,
        **kwargs,
    ):
        # extra_dir should never be constructed from provided data but just
        # make sure there are no shenannigans afoot
        if extra_dir and extra_dir != os.path.normpath(extra_dir):
            log.warning("extra_dir is not normalized: %s", extra_dir)
            raise ObjectInvalid("The requested object is invalid")
        # ensure that any parent directory references in alt_name would not
        # result in a path not contained in the directory path constructed here
        if alt_name:
            if not safe_relpath(alt_name):
                log.warning("alt_name would locate path outside dir: %s", alt_name)
                raise ObjectInvalid("The requested object is invalid")
            # alt_name can contain parent directory references, but S3 will not
            # follow them, so if they are valid we normalize them out
            alt_name = os.path.normpath(alt_name)

        rel_path = os.path.join(*directory_hash_id(self._get_object_id(obj)))

        if extra_dir is not None:
            if extra_dir_at_root:
                rel_path = os.path.join(extra_dir, rel_path)
            else:
                rel_path = os.path.join(rel_path, extra_dir)

        # for JOB_WORK directory
        if obj_dir:
            rel_path = os.path.join(rel_path, str(self._get_object_id(obj)))
        if base_dir:
            base = self.extra_dirs.get(base_dir)
            return os.path.join(base, rel_path)

        # S3 folders are marked by having trailing '/' so add it now
        # rel_path = '%s/' % rel_path # assume for now we don't need this in Azure blob storage.

        if not dir_only:
            rel_path = os.path.join(rel_path, alt_name if alt_name else f"dataset_{self._get_object_id(obj)}.dat")

        return rel_path

    def _fix_permissions(self, rel_path):
        """Set permissions on rel_path"""
        for basedir, _, files in os.walk(rel_path):
            umask_fix_perms(basedir, self.config.umask, 0o777, self.config.gid)
            for filename in files:
                path = os.path.join(basedir, filename)
                # Ignore symlinks
                if os.path.islink(path):
                    continue
                umask_fix_perms(path, self.config.umask, 0o666, self.config.gid)

    def _get_cache_path(self, rel_path):
        return os.path.abspath(os.path.join(self.staging_path, rel_path))

    def _get_transfer_progress(self):
        return self.transfer_progress

    def _get_size_in_azure(self, rel_path):
        try:
            properties = self.service.get_blob_properties(self.container_name, rel_path)
            # Currently this returns a blob and not a BlobProperties object
            # Similar issue for the ruby https://github.com/Azure/azure-storage-ruby/issues/13
            # The typecheck is an attempt at future-proofing this when/if the bug is fixed.
            if type(properties) is Blob:
                properties = properties.properties
            if properties:
                size_in_bytes = properties.content_length
                return size_in_bytes
        except AzureHttpError:
            log.exception("Could not get size of blob '%s' from Azure", rel_path)
            return -1

    def _in_azure(self, rel_path):
        try:
            exists = self.service.exists(self.container_name, rel_path)
        except AzureHttpError:
            log.exception("Trouble checking existence of Azure blob '%s'", rel_path)
            return False
        return exists

    def _in_cache(self, rel_path):
        """Check if the given dataset is in the local cache."""
        cache_path = self._get_cache_path(rel_path)
        return os.path.exists(cache_path)

    def _pull_into_cache(self, rel_path):
        # Ensure the cache directory structure exists (e.g., dataset_#_files/)
        rel_path_dir = os.path.dirname(rel_path)
        if not os.path.exists(self._get_cache_path(rel_path_dir)):
            os.makedirs(self._get_cache_path(rel_path_dir), exist_ok=True)
        # Now pull in the file
        file_ok = self._download(rel_path)
        self._fix_permissions(self._get_cache_path(rel_path_dir))
        return file_ok

    def _transfer_cb(self, complete, total):
        self.transfer_progress = float(complete) / float(total) * 100  # in percent

    def _download(self, rel_path):
        local_destination = self._get_cache_path(rel_path)
        try:
            log.debug("Pulling '%s' into cache to %s", rel_path, local_destination)
            if self.cache_size > 0 and self._get_size_in_azure(rel_path) > self.cache_size:
                log.critical(
                    "File %s is larger (%s) than the cache size (%s). Cannot download.",
                    rel_path,
                    self._get_size_in_azure(rel_path),
                    self.cache_size,
                )
                return False
            else:
                self.transfer_progress = 0  # Reset transfer progress counter
                self.service.get_blob_to_path(
                    self.container_name, rel_path, local_destination, progress_callback=self._transfer_cb
                )
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

            if not os.path.exists(source_file):
                log.error(
                    "Tried updating blob '%s' from source file '%s', but source file does not exist.",
                    rel_path,
                    source_file,
                )
                return False

            if os.path.getsize(source_file) == 0:
                log.debug(
                    "Wanted to push file '%s' to azure blob '%s' but its size is 0; skipping.", source_file, rel_path
                )
                return True

            if from_string:
                self.service.create_blob_from_text(
                    self.container_name, rel_path, from_string, progress_callback=self._transfer_cb
                )
                log.debug("Pushed data from string '%s' to blob '%s'", from_string, rel_path)
            else:
                start_time = datetime.now()
                log.debug(
                    "Pushing cache file '%s' of size %s bytes to '%s'",
                    source_file,
                    os.path.getsize(source_file),
                    rel_path,
                )
                self.transfer_progress = 0  # Reset transfer progress counter
                self.service.create_blob_from_path(
                    self.container_name, rel_path, source_file, progress_callback=self._transfer_cb
                )
                end_time = datetime.now()
                log.debug(
                    "Pushed cache file '%s' to blob '%s' (%s bytes transfered in %s sec)",
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

        in_cache = self._in_cache(rel_path)
        in_azure = self._in_azure(rel_path)
        # log.debug("~~~~~~ File '%s' exists in cache: %s; in azure: %s" % (rel_path, in_cache, in_azure))
        # dir_only does not get synced so shortcut the decision
        dir_only = kwargs.get("dir_only", False)
        base_dir = kwargs.get("base_dir", None)
        if dir_only:
            if in_cache or in_azure:
                return True
            # for JOB_WORK directory
            elif base_dir:
                if not os.path.exists(rel_path):
                    os.makedirs(rel_path, exist_ok=True)
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

    def _empty(self, obj, **kwargs):
        if self._exists(obj, **kwargs):
            return bool(self._size(obj, **kwargs) > 0)
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
                blobs = self.service.list_blobs(self.container_name, prefix=rel_path)
                for blob in blobs:
                    log.debug("Deleting from Azure: %s", blob)
                    self.service.delete_blob(self.container_name, blob.name)
                return True
            else:
                # Delete from cache first
                unlink(self._get_cache_path(rel_path), ignore_errors=True)
                # Delete from S3 as well
                if self._in_azure(rel_path):
                    log.debug("Deleting from Azure: %s", rel_path)
                    self.service.delete_blob(self.container_name, rel_path)
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

        # for JOB_WORK directory
        if base_dir and dir_only and obj_dir:
            return os.path.abspath(rel_path)

        cache_path = self._get_cache_path(rel_path)
        # S3 does not recognize directories as files so cannot check if those exist.
        # So, if checking dir only, ensure given dir exists in cache and return
        # the expected cache path.
        # dir_only = kwargs.get('dir_only', False)
        # if dir_only:
        #     if not os.path.exists(cache_path):
        #         os.makedirs(cache_path)
        #     return cache_path
        # Check if the file exists in the cache first
        if self._in_cache(rel_path):
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
        elif self._exists(obj, **kwargs):
            rel_path = self._construct_path(obj, **kwargs)
            # Chose whether to use the dataset file itself or an alternate file
            if file_name:
                source_file = os.path.abspath(file_name)
                # Copy into cache
                cache_file = self._get_cache_path(rel_path)
                try:
                    if source_file != cache_file:
                        # FIXME? Should this be a `move`?
                        shutil.copy2(source_file, cache_file)
                    self._fix_permissions(cache_file)
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
                url = self.service.make_blob_url(container_name=self.container_name, blob_name=rel_path)
                return url
            except AzureHttpError:
                log.exception("Trouble generating URL for dataset '%s'", rel_path)
        return None

    def _get_store_usage_percent(self):
        return 0.0

    ##################
    # Secret Methods #
    ##################

    def __cache_monitor(self):
        time.sleep(2)  # Wait for things to load before starting the monitor
        while self.running:
            total_size = 0
            # Is this going to be too expensive of an operation to be done frequently?
            file_list = []
            for dirpath, _, filenames in os.walk(self.staging_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    file_size = os.path.getsize(filepath)
                    total_size += file_size
                    # Get the time given file was last accessed
                    last_access_time = time.localtime(os.stat(filepath)[7])
                    # Compose a tuple of the access time and the file path
                    file_tuple = last_access_time, filepath, file_size
                    file_list.append(file_tuple)
            # Sort the file list (based on access time)
            file_list.sort()
            # Initiate cleaning once within 10% of the defined cache size?
            cache_limit = self.cache_size * 0.9
            if total_size > cache_limit:
                log.info(
                    "Initiating cache cleaning: current cache size: %s; clean until smaller than: %s",
                    convert_bytes(total_size),
                    convert_bytes(cache_limit),
                )
                # How much to delete? If simply deleting up to the cache-10% limit,
                # is likely to be deleting frequently and may run the risk of hitting
                # the limit - maybe delete additional #%?
                # For now, delete enough to leave at least 10% of the total cache free
                delete_this_much = total_size - cache_limit
                # Keep deleting datasets from file_list until deleted_amount does not
                # exceed delete_this_much; start deleting from the front of the file list,
                # which assumes the oldest files come first on the list.
                deleted_amount = 0
                for entry in enumerate(file_list):
                    if deleted_amount < delete_this_much:
                        deleted_amount += entry[2]
                        os.remove(entry[1])
                        # Debugging code for printing deleted files' stats
                        # folder, file_name = os.path.split(f[1])
                        # file_date = time.strftime("%m/%d/%y %H:%M:%S", f[0])
                        # log.debug("%s. %-25s %s, size %s (deleted %s/%s)" \
                        #     % (i, file_name, convert_bytes(f[2]), file_date, \
                        #     convert_bytes(deleted_amount), convert_bytes(delete_this_much)))
                    else:
                        log.debug("Cache cleaning done. Total space freed: %s", convert_bytes(deleted_amount))

            self.sleeper.sleep(30)  # Test cache size every 30 seconds?
