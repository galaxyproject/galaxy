"""A more modern version of the S3 object store based on boto3 instead of boto.
"""

import logging
import os
from typing import (
    Any,
    Callable,
    Dict,
    TYPE_CHECKING,
)

from typing_extensions import (
    Literal,
    NotRequired,
    TypedDict,
)

if TYPE_CHECKING:
    from mypy_boto3_c3.client import S3Client

try:
    # Imports are done this way to allow objectstore code to be used outside of Galaxy.
    import boto3
    from boto3.s3.transfer import TransferConfig
    from botocore.client import ClientError
except ImportError:
    boto3 = None  # type: ignore[assignment,unused-ignore]
    TransferConfig = None  # type: ignore[assignment,unused-ignore,misc]

from galaxy.util import asbool
from ._caching_base import CachingConcreteObjectStore
from .caching import (
    enable_cache_monitor,
    parse_caching_config_dict_from_xml,
)

NO_BOTO_ERROR_MESSAGE = (
    "S3/Swift object store configured, but no boto3 dependency available."
    "Please install and properly configure boto or modify object store configuration."
)

log = logging.getLogger(__name__)
# This object store generates a lot of logging by default, fairly sure it is an anti-pattern
# to just disable library logging.
# logging.getLogger("botocore").setLevel(logging.INFO)
# logging.getLogger("s3transfer").setLevel(logging.INFO)


def host_to_endpoint(mapping):
    # convert older-style boto parameters to boto3 endpoint_url.
    host = mapping["host"]
    port = mapping.get("port", 6000)
    is_secure = asbool(mapping.get("is_secure", "True"))
    conn_path = mapping.get("conn_path", "/")
    scheme = "https" if is_secure else "http"
    return f"{scheme}://{host}:{port}{conn_path}"


def parse_config_xml(config_xml):
    try:
        a_xml = config_xml.findall("auth")[0]
        access_key = a_xml.get("access_key")
        secret_key = a_xml.get("secret_key")

        b_xml = config_xml.findall("bucket")[0]
        bucket_name = b_xml.get("name")

        cn_xml = config_xml.findall("connection")
        if not cn_xml:
            cn_xml = {}
        else:
            cn_xml = cn_xml[0]
        endpoint_url = cn_xml.get("endpoint_url")

        # for admin ease - allow older style host, port, is_secure, conn_path to be used.
        if endpoint_url is None and cn_xml.get("host") is not None:
            endpoint_url = host_to_endpoint(cn_xml)
        region = cn_xml.get("region")
        cache_dict = parse_caching_config_dict_from_xml(config_xml)

        transfer_xml = config_xml.findall("transfer")
        if not transfer_xml:
            transfer_xml = {}
        else:
            transfer_xml = transfer_xml[0]
        transfer_dict = {}
        for prefix in ["", "upload_", "download_"]:
            for key in [
                "multipart_threshold",
                "max_concurrency",
                "multipart_chunksize",
                "num_download_attempts",
                "max_io_queue",
                "io_chunksize",
                "use_threads",
                "max_bandwidth",
            ]:
                full_key = f"{prefix}{key}"
                value = transfer_xml.get(full_key)
                if transfer_xml.get(full_key) is not None:
                    transfer_dict[full_key] = value

        tag, attrs = "extra_dir", ("type", "path")
        extra_dirs = config_xml.findall(tag)
        if not extra_dirs:
            msg = f"No {tag} element in XML tree"
            log.error(msg)
            raise Exception(msg)
        extra_dirs = [{k: e.get(k) for k in attrs} for e in extra_dirs]

        config_dict = {
            "auth": {
                "access_key": access_key,
                "secret_key": secret_key,
            },
            "bucket": {
                "name": bucket_name,
            },
            "connection": {
                "endpoint_url": endpoint_url,
                "region": region,
            },
            "transfer": transfer_dict,
            "cache": cache_dict,
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


class S3ClientConstructorKwds(TypedDict):
    service_name: Literal["s3"]
    endpoint_url: NotRequired[str]
    region_name: NotRequired[str]
    aws_access_key_id: NotRequired[str]
    aws_secret_access_key: NotRequired[str]


class S3ObjectStore(CachingConcreteObjectStore):
    """
    Object store that stores objects as items in an AWS S3 bucket. A local
    cache exists that is used as an intermediate location for files between
    Galaxy and S3.
    """

    _client: "S3Client"
    store_type = "boto3"
    cloud = True

    def __init__(self, config, config_dict):
        super().__init__(config, config_dict)
        self.cache_monitor = None

        auth_dict = config_dict["auth"]
        bucket_dict = config_dict["bucket"]
        connection_dict = config_dict.get("connection") or {}
        cache_dict = config_dict.get("cache") or {}
        transfer_dict = config_dict.get("transfer") or {}
        typed_transfer_dict = {}
        for prefix in ["", "upload_", "download_"]:
            options: Dict[str, Callable[[Any], Any]] = {
                "multipart_threshold": int,
                "max_concurrency": int,
                "multipart_chunksize": int,
                "num_download_attempts": int,
                "max_io_queue": int,
                "io_chunksize": int,
                "use_threads": asbool,
                "max_bandwidth": int,
            }
            for key, key_type in options.items():
                full_key = f"{prefix}{key}"
                transfer_value = transfer_dict.get(full_key)
                if transfer_value is not None:
                    typed_transfer_dict[full_key] = key_type(transfer_value)
        self.transfer_dict = typed_transfer_dict

        self.enable_cache_monitor, self.cache_monitor_interval = enable_cache_monitor(config, config_dict)

        self.access_key = auth_dict.get("access_key")
        self.secret_key = auth_dict.get("secret_key")

        self.bucket = bucket_dict.get("name")

        self.endpoint_url = connection_dict.get("endpoint_url")
        if self.endpoint_url is None and "host" in connection_dict:
            self.endpoint_url = host_to_endpoint(connection_dict)

        self.region = connection_dict.get("region")

        self.cache_size = cache_dict.get("size") or self.config.object_store_cache_size
        self.staging_path = cache_dict.get("path") or self.config.object_store_cache_path
        self.cache_updated_data = cache_dict.get("cache_updated_data", True)

        extra_dirs = {e["type"]: e["path"] for e in config_dict.get("extra_dirs", [])}
        self.extra_dirs.update(extra_dirs)

        self._initialize()

    def _initialize(self):
        if boto3 is None:
            raise Exception(NO_BOTO_ERROR_MESSAGE)

        self._ensure_staging_path_writable()
        self._configure_connection()
        self._start_cache_monitor_if_needed()

    def _configure_connection(self):
        log.debug("Configuring S3 Connection")
        self._init_client()
        if not self._bucket_exists:
            self._create_bucket()

        # get_object_url only works on AWS if client is set, so if it wasn't
        # fetch it and reset the client now. Skip this logic entirely for other
        # non-AWS services by ensuring endpoint_url is not set.
        if not self.endpoint_url and not self.region:
            response = self._client.get_bucket_location(
                Bucket=self.bucket,
            )
            if "LocationConstraint" in response:
                region = response["LocationConstraint"]
                self.region = region
            self._init_client()

    def _init_client(self):
        # set _client based on current args.
        # If access_key is empty use default credential chain
        kwds: S3ClientConstructorKwds = {
            "service_name": "s3",
        }
        if self.endpoint_url:
            kwds["endpoint_url"] = self.endpoint_url
        if self.region:
            kwds["region_name"] = self.region
        if self.access_key:
            kwds["aws_access_key_id"] = self.access_key
            kwds["aws_secret_access_key"] = self.secret_key
        self._client = boto3.client(**kwds)

    @property
    def _bucket_exists(self) -> bool:
        try:
            self._client.head_bucket(Bucket=self.bucket)
            return True
        except ClientError as err:
            if err.response["ResponseMetadata"]["HTTPStatusCode"] == 404:
                return False
            raise

    def _create_bucket(self):
        kwds = {}
        if self.region:
            kwds["CreateBucketConfiguration"] = dict(LocationConstraint=self.region)
        self._client.create_bucket(Bucket=self.bucket, **kwds)

    @classmethod
    def parse_xml(clazz, config_xml):
        return parse_config_xml(config_xml)

    def _config_to_dict(self):
        return {
            "auth": {
                "access_key": self.access_key,
                "secret_key": self.secret_key,
            },
            "bucket": {
                "name": self.bucket,
            },
            "connection": {
                "endpoint_url": self.endpoint_url,
                "region": self.region,
            },
            "transfer": self.transfer_dict,
            "cache": {
                "size": self.cache_size,
                "path": self.staging_path,
                "cache_updated_data": self.cache_updated_data,
            },
        }

    def to_dict(self):
        as_dict = super().to_dict()
        as_dict.update(self._config_to_dict())
        return as_dict

    def _get_remote_size(self, rel_path) -> int:
        response = self._client.head_object(Bucket=self.bucket, Key=rel_path)
        return response["ContentLength"]

    def _exists_remotely(self, rel_path: str) -> bool:
        try:
            is_dir = rel_path[-1] == "/"
            if is_dir:
                for _ in self._keys(rel_path):
                    return True

                return False
            else:
                self._client.head_object(Bucket=self.bucket, Key=rel_path)
                return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    def _download(self, rel_path: str) -> bool:
        local_destination = self._get_cache_path(rel_path)
        try:
            log.debug("Pulling key '%s' into cache to %s", rel_path, local_destination)
            if not self._caching_allowed(rel_path):
                return False
            config = self._transfer_config("download")
            self._client.download_file(self.bucket, rel_path, local_destination, Config=config)
            return True
        except ClientError:
            log.exception("Failed to download file from S3")
        return False

    def _push_string_to_path(self, rel_path: str, from_string: str) -> bool:
        try:
            self._client.put_object(Body=from_string.encode("utf-8"), Bucket=self.bucket, Key=rel_path)
            return True
        except ClientError:
            log.exception("Trouble pushing to S3 '%s' from string", rel_path)
            return False

    def _push_file_to_path(self, rel_path: str, source_file: str) -> bool:
        try:
            config = self._transfer_config("upload")
            self._client.upload_file(source_file, self.bucket, rel_path, Config=config)
            return True
        except ClientError:
            log.exception("Trouble pushing to S3 '%s' from file '%s'", rel_path, source_file)
            return False

    def _delete_remote_all(self, rel_path: str) -> bool:
        try:
            for key in self._keys(rel_path):
                self._client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            log.exception("Could not delete blob '%s' from S3", rel_path)
            return False

    def _delete_existing_remote(self, rel_path: str) -> bool:
        try:
            self._client.delete_object(Bucket=self.bucket, Key=rel_path)
            return True
        except ClientError:
            log.exception("Could not delete blob '%s' from S3", rel_path)
            return False

    # https://stackoverflow.com/questions/30249069/listing-contents-of-a-bucket-with-boto3
    def _keys(self, prefix="/", delimiter="/", start_after=""):
        s3_paginator = self._client.get_paginator("list_objects_v2")
        prefix = prefix.lstrip(delimiter)
        start_after = (start_after or prefix) if prefix.endswith(delimiter) else start_after
        for page in s3_paginator.paginate(Bucket=self.bucket, Prefix=prefix, StartAfter=start_after):
            for content in page.get("Contents", ()):
                yield content["Key"]

    def _download_directory_into_cache(self, rel_path, cache_path):
        for key in self._keys(rel_path):
            local_file_path = os.path.join(cache_path, os.path.relpath(key, rel_path))

            # Create directories if they don't exist
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

            # Download the file
            self._client.download_file(self.bucket, key, local_file_path)

    def _get_object_url(self, obj, **kwargs):
        try:
            if self._exists(obj, **kwargs):
                rel_path = self._construct_path(obj, **kwargs)
                url = self._client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={
                        "Bucket": self.bucket,
                        "Key": rel_path,
                    },
                    ExpiresIn=3600,
                    HttpMethod="GET",
                )
                return url
        except ClientError:
            log.exception("Failed to generate URL for dataset.")
        return None

    def _get_store_usage_percent(self, obj):
        return 0.0

    def _transfer_config(self, prefix: Literal["upload", "download"]) -> "TransferConfig":
        config = {}
        for key in [
            "multipart_threshold",
            "max_concurrency",
            "multipart_chunksize",
            "num_download_attempts",
            "max_io_queue",
            "io_chunksize",
            "use_threads",
            "max_bandwidth",
        ]:
            specific_key = f"{prefix}_{key}"
            if specific_key in self.transfer_dict:
                config[key] = self.transfer_dict[specific_key]
            elif key in self.transfer_dict:
                config[key] = self.transfer_dict[key]
        return TransferConfig(**config)

    def shutdown(self):
        self._shutdown_cache_monitor()
