"""
Object Store plugin for the Amazon Simple Storage Service (S3)
"""

import logging
import multiprocessing
import os
import shutil
import subprocess
import time
from datetime import datetime
from typing import Optional

try:
    # Imports are done this way to allow objectstore code to be used outside of Galaxy.
    import boto
    from boto.exception import S3ResponseError
    from boto.s3.connection import S3Connection
    from boto.s3.key import Key
except ImportError:
    boto = None  # type: ignore[assignment]

from galaxy.exceptions import (
    ObjectInvalid,
    ObjectNotFound,
)
from galaxy.util import (
    directory_hash_id,
    string_as_bool,
    unlink,
    which,
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
from .s3_multipart_upload import multipart_upload

NO_BOTO_ERROR_MESSAGE = (
    "S3/Swift object store configured, but no boto dependency available."
    "Please install and properly configure boto or modify object store configuration."
)

log = logging.getLogger(__name__)
logging.getLogger("boto").setLevel(logging.INFO)  # Otherwise boto is quite noisy


def download_directory(bucket, remote_folder, local_path):
    # List objects in the specified S3 folder
    objects = bucket.list(prefix=remote_folder)

    for obj in objects:
        remote_file_path = obj.key
        local_file_path = os.path.join(local_path, os.path.relpath(remote_file_path, remote_folder))

        # Create directories if they don't exist
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

        # Download the file
        obj.get_contents_to_filename(local_file_path)


def parse_config_xml(config_xml):
    try:
        a_xml = config_xml.findall("auth")[0]
        access_key = a_xml.get("access_key")
        secret_key = a_xml.get("secret_key")

        b_xml = config_xml.findall("bucket")[0]
        bucket_name = b_xml.get("name")
        use_rr = string_as_bool(b_xml.get("use_reduced_redundancy", "False"))
        max_chunk_size = int(b_xml.get("max_chunk_size", 250))

        cn_xml = config_xml.findall("connection")
        if not cn_xml:
            cn_xml = {}
        else:
            cn_xml = cn_xml[0]

        host = cn_xml.get("host", None)
        port = int(cn_xml.get("port", 6000))
        multipart = string_as_bool(cn_xml.get("multipart", "True"))
        is_secure = string_as_bool(cn_xml.get("is_secure", "True"))
        conn_path = cn_xml.get("conn_path", "/")
        region = cn_xml.get("region", None)

        cache_dict = parse_caching_config_dict_from_xml(config_xml)

        tag, attrs = "extra_dir", ("type", "path")
        extra_dirs = config_xml.findall(tag)
        if not extra_dirs:
            msg = f"No {tag} element in XML tree"
            log.error(msg)
            raise Exception(msg)
        extra_dirs = [{k: e.get(k) for k in attrs} for e in extra_dirs]

        return {
            "auth": {
                "access_key": access_key,
                "secret_key": secret_key,
            },
            "bucket": {
                "name": bucket_name,
                "use_reduced_redundancy": use_rr,
                "max_chunk_size": max_chunk_size,
            },
            "connection": {
                "host": host,
                "port": port,
                "multipart": multipart,
                "is_secure": is_secure,
                "conn_path": conn_path,
                "region": region,
            },
            "cache": cache_dict,
            "extra_dirs": extra_dirs,
            "private": ConcreteObjectStore.parse_private_from_config_xml(config_xml),
        }
    except Exception:
        # Toss it back up after logging, we can't continue loading at this point.
        log.exception("Malformed ObjectStore Configuration XML -- unable to continue")
        raise


class CloudConfigMixin:
    def _config_to_dict(self):
        return {
            "auth": {
                "access_key": self.access_key,
                "secret_key": self.secret_key,
            },
            "bucket": {
                "name": self.bucket,
                "use_reduced_redundancy": self.use_rr,
            },
            "connection": {
                "host": self.host,
                "port": self.port,
                "multipart": self.multipart,
                "is_secure": self.is_secure,
                "conn_path": self.conn_path,
                "region": self.region,
            },
            "cache": {
                "size": self.cache_size,
                "path": self.staging_path,
                "cache_updated_data": self.cache_updated_data,
            },
        }


class S3ObjectStore(ConcreteObjectStore, CloudConfigMixin, UsesCache):
    """
    Object store that stores objects as items in an AWS S3 bucket. A local
    cache exists that is used as an intermediate location for files between
    Galaxy and S3.
    """

    cache_monitor: Optional[InProcessCacheMonitor] = None
    store_type = "aws_s3"

    def __init__(self, config, config_dict):
        super().__init__(config, config_dict)
        self.cache_monitor = None

        self.transfer_progress = 0

        auth_dict = config_dict["auth"]
        bucket_dict = config_dict["bucket"]
        connection_dict = config_dict.get("connection", {})
        cache_dict = config_dict.get("cache") or {}
        self.enable_cache_monitor, self.cache_monitor_interval = enable_cache_monitor(config, config_dict)

        self.access_key = auth_dict.get("access_key")
        self.secret_key = auth_dict.get("secret_key")

        self.bucket = bucket_dict.get("name")
        self.use_rr = bucket_dict.get("use_reduced_redundancy", False)
        self.max_chunk_size = bucket_dict.get("max_chunk_size", 250)

        self.host = connection_dict.get("host", None)
        self.port = connection_dict.get("port", 6000)
        self.multipart = connection_dict.get("multipart", True)
        self.is_secure = connection_dict.get("is_secure", True)
        self.conn_path = connection_dict.get("conn_path", "/")
        self.region = connection_dict.get("region", None)

        self.cache_size = cache_dict.get("size") or self.config.object_store_cache_size
        self.staging_path = cache_dict.get("path") or self.config.object_store_cache_path
        self.cache_updated_data = cache_dict.get("cache_updated_data", True)

        extra_dirs = {e["type"]: e["path"] for e in config_dict.get("extra_dirs", [])}
        self.extra_dirs.update(extra_dirs)

        self._initialize()

    def _initialize(self):
        if boto is None:
            raise Exception(NO_BOTO_ERROR_MESSAGE)

        # for multipart upload
        self.s3server = {
            "access_key": self.access_key,
            "secret_key": self.secret_key,
            "is_secure": self.is_secure,
            "max_chunk_size": self.max_chunk_size,
            "host": self.host,
            "port": self.port,
            "use_rr": self.use_rr,
            "conn_path": self.conn_path,
        }

        self._configure_connection()
        self._bucket = self._get_bucket(self.bucket)
        self.start_cache_monitor()
        # Test if 'axel' is available for parallel download and pull the key into cache
        if which("axel"):
            self.use_axel = True
        else:
            self.use_axel = False

    def start_cache_monitor(self):
        if self.enable_cache_monitor:
            self.cache_monitor = InProcessCacheMonitor(self.cache_target, self.cache_monitor_interval)

    def _configure_connection(self):
        log.debug("Configuring S3 Connection")
        # If access_key is empty use default credential chain
        if self.access_key:
            if self.region:
                # If specify a region we can infer a host and turn on SIGV4.
                # https://stackoverflow.com/questions/26744712/s3-using-boto-and-sigv4-missing-host-parameter

                # Turning on SIGV4 is needed for AWS regions created after 2014... from
                # https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html:
                #
                # "Amazon S3 supports Signature Version 4, a protocol for authenticating inbound API requests to AWS services,
                # in all AWS Regions. At this time, AWS Regions created before January 30, 2014 will continue to support the
                # previous protocol, Signature Version 2. Any new Regions after January 30, 2014 will support only Signature
                # Version 4 and therefore all requests to those Regions must be made with Signature Version 4."
                os.environ["S3_USE_SIGV4"] = "True"
                self.conn = S3Connection(self.access_key, self.secret_key, host=f"s3.{self.region}.amazonaws.com")
            else:
                # See notes above, this path through the code will not work for
                # newer regions.
                self.conn = S3Connection(self.access_key, self.secret_key)
        else:
            self.conn = S3Connection()

    @classmethod
    def parse_xml(clazz, config_xml):
        return parse_config_xml(config_xml)

    def to_dict(self):
        as_dict = super().to_dict()
        as_dict.update(self._config_to_dict())
        return as_dict

    @property
    def cache_target(self) -> CacheTarget:
        return CacheTarget(
            self.staging_path,
            self.cache_size,
            0.9,
        )

    def _get_bucket(self, bucket_name):
        """Sometimes a handle to a bucket is not established right away so try
        it a few times. Raise error is connection is not established."""
        for i in range(5):
            try:
                bucket = self.conn.get_bucket(bucket_name)
                log.debug("Using cloud object store with bucket '%s'", bucket.name)
                return bucket
            except S3ResponseError:
                try:
                    log.debug("Bucket not found, creating s3 bucket with handle '%s'", bucket_name)
                    self.conn.create_bucket(bucket_name)
                except S3ResponseError:
                    log.exception("Could not get bucket '%s', attempt %s/5", bucket_name, i + 1)
                    time.sleep(2)
        # All the attempts have been exhausted and connection was not established,
        # raise error
        raise S3ResponseError

    def _get_transfer_progress(self):
        return self.transfer_progress

    def _get_remote_size(self, rel_path):
        try:
            key = self._bucket.get_key(rel_path)
            return key.size
        except (S3ResponseError, AttributeError):
            log.exception("Could not get size of key '%s' from S3", rel_path)
            return -1

    def _exists_remotely(self, rel_path):
        exists = False
        try:
            # A hackish way of testing if the rel_path is a folder vs a file
            is_dir = rel_path[-1] == "/"
            if is_dir:
                keyresult = self._bucket.get_all_keys(prefix=rel_path)
                if len(keyresult) > 0:
                    exists = True
                else:
                    exists = False
            else:
                key = Key(self._bucket, rel_path)
                exists = key.exists()
        except S3ResponseError:
            log.exception("Trouble checking existence of S3 key '%s'", rel_path)
            return False
        return exists

    def _transfer_cb(self, complete, total):
        self.transfer_progress += 10

    def _download(self, rel_path):
        try:
            log.debug("Pulling key '%s' into cache to %s", rel_path, self._get_cache_path(rel_path))
            key = self._bucket.get_key(rel_path)
            if key is None:
                message = f"Attempting to download an invalid key for path {rel_path}."
                log.critical(message)
                raise Exception(message)
            # Test if cache is large enough to hold the new file
            if not self.cache_target.fits_in_cache(key.size):
                log.critical(
                    "File %s is larger (%s) than the configured cache allows (%s). Cannot download.",
                    rel_path,
                    key.size,
                    self.cache_target.log_description,
                )
                return False
            if self.use_axel:
                log.debug("Parallel pulled key '%s' into cache to %s", rel_path, self._get_cache_path(rel_path))
                ncores = multiprocessing.cpu_count()
                url = key.generate_url(7200)
                ret_code = subprocess.call(["axel", "-a", "-n", str(ncores), url])
                if ret_code == 0:
                    return True
            else:
                log.debug("Pulled key '%s' into cache to %s", rel_path, self._get_cache_path(rel_path))
                self.transfer_progress = 0  # Reset transfer progress counter
                key.get_contents_to_filename(self._get_cache_path(rel_path), cb=self._transfer_cb, num_cb=10)
                return True
        except S3ResponseError:
            log.exception("Problem downloading key '%s' from S3 bucket '%s'", rel_path, self._bucket.name)
        return False

    def _push_to_os(self, rel_path, source_file=None, from_string=None):
        """
        Push the file pointed to by ``rel_path`` to the object store naming the key
        ``rel_path``. If ``source_file`` is provided, push that file instead while
        still using ``rel_path`` as the key name.
        If ``from_string`` is provided, set contents of the file to the value of
        the string.
        """
        try:
            source_file = source_file if source_file else self._get_cache_path(rel_path)
            if os.path.exists(source_file):
                key = Key(self._bucket, rel_path)
                if os.path.getsize(source_file) == 0 and key.exists():
                    log.debug(
                        "Wanted to push file '%s' to S3 key '%s' but its size is 0; skipping.", source_file, rel_path
                    )
                    return True
                if from_string:
                    key.set_contents_from_string(from_string, reduced_redundancy=self.use_rr)
                    log.debug("Pushed data from string '%s' to key '%s'", from_string, rel_path)
                else:
                    start_time = datetime.now()
                    log.debug(
                        "Pushing cache file '%s' of size %s bytes to key '%s'",
                        source_file,
                        os.path.getsize(source_file),
                        rel_path,
                    )
                    mb_size = os.path.getsize(source_file) / 1e6
                    if mb_size < 10 or (not self.multipart):
                        self.transfer_progress = 0  # Reset transfer progress counter
                        key.set_contents_from_filename(
                            source_file, reduced_redundancy=self.use_rr, cb=self._transfer_cb, num_cb=10
                        )
                    else:
                        multipart_upload(self.s3server, self._bucket, key.name, source_file, mb_size)
                    end_time = datetime.now()
                    log.debug(
                        "Pushed cache file '%s' to key '%s' (%s bytes transfered in %s sec)",
                        source_file,
                        rel_path,
                        os.path.getsize(source_file),
                        end_time - start_time,
                    )
                return True
            else:
                log.error(
                    "Tried updating key '%s' from source file '%s', but source file does not exist.",
                    rel_path,
                    source_file,
                )
        except S3ResponseError:
            log.exception("Trouble pushing S3 key '%s' from file '%s'", rel_path, source_file)
            raise
        return False

    def _delete(self, obj, entire_dir=False, **kwargs):
        rel_path = self._construct_path(obj, **kwargs)
        extra_dir = kwargs.get("extra_dir", None)
        base_dir = kwargs.get("base_dir", None)
        dir_only = kwargs.get("dir_only", False)
        obj_dir = kwargs.get("obj_dir", False)
        try:
            # Remove temparory data in JOB_WORK directory
            if base_dir and dir_only and obj_dir:
                shutil.rmtree(os.path.abspath(rel_path))
                return True

            # For the case of extra_files, because we don't have a reference to
            # individual files/keys we need to remove the entire directory structure
            # with all the files in it. This is easy for the local file system,
            # but requires iterating through each individual key in S3 and deleing it.
            if entire_dir and extra_dir:
                shutil.rmtree(self._get_cache_path(rel_path), ignore_errors=True)
                return self._delete_remote_all(rel_path)
            else:
                # Delete from cache first
                unlink(self._get_cache_path(rel_path), ignore_errors=True)
                # Delete from S3 as well
                if self._exists_remotely(rel_path):
                    self._delete_existing_remote(rel_path)
        except OSError:
            log.exception("%s delete error", self._get_filename(obj, **kwargs))
        return False
        # return cache_path # Until the upload tool does not explicitly create the dataset, return expected path

    def _delete_remote_all(self, rel_path: str) -> bool:
        try:
            results = self._bucket.get_all_keys(prefix=rel_path)
            for key in results:
                log.debug("Deleting key %s", key.name)
                key.delete()
            return True
        except S3ResponseError:
            log.exception("Could not delete blob '%s' from S3", rel_path)
            return False

    def _delete_existing_remote(self, rel_path: str) -> bool:
        try:
            key = Key(self._bucket, rel_path)
            log.debug("Deleting key %s", key.name)
            key.delete()
            return True
        except S3ResponseError:
            log.exception("Could not delete blob '%s' from S3", rel_path)
            return False

    def _download_directory_into_cache(self, rel_path, cache_path):
        download_directory(self._bucket, rel_path, cache_path)

    def _get_object_url(self, obj, **kwargs):
        if self._exists(obj, **kwargs):
            rel_path = self._construct_path(obj, **kwargs)
            try:
                key = Key(self._bucket, rel_path)
                return key.generate_url(expires_in=86400)  # 24hrs
            except S3ResponseError:
                log.exception("Trouble generating URL for dataset '%s'", rel_path)
        return None

    def _get_store_usage_percent(self, obj):
        return 0.0

    def shutdown(self):
        self.cache_monitor and self.cache_monitor.shutdown()


class GenericS3ObjectStore(S3ObjectStore):
    """
    Object store that stores objects as items in a generic S3 (non AWS) bucket.
    A local cache exists that is used as an intermediate location for files between
    Galaxy and the S3 storage service.
    """

    store_type = "generic_s3"

    def _configure_connection(self):
        log.debug("Configuring generic S3 Connection")
        self.conn = boto.connect_s3(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            is_secure=self.is_secure,
            host=self.host,
            port=self.port,
            calling_format=boto.s3.connection.OrdinaryCallingFormat(),
            path=self.conn_path,
        )
