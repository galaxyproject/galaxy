"""
Object Store plugin for Cloud storage.
"""

import logging
import os
import os.path
from typing import (
    Any,
    Literal,
    Optional,
)

from galaxy.util import asbool
from ._caching_base import (
    CachingConcreteObjectStore,
    RemoteDataStream,
    STREAM_CHUNK_SIZE,
)
from .caching import (
    CacheShardManager,
    CacheTarget,
    enable_cache_monitor,
)
from .cloud_auth import (
    AUTH_KEY_MAP,
    CONNECTION_KEY_MAP,
    NON_XML_AUTH_KEYS,
    PROVIDER_LIST_NAMES,
    validate_auth,
)
from .s3 import parse_config_xml

try:
    from cloudbridge.factory import (
        CloudProviderFactory,
        ProviderList,
    )
    from cloudbridge.interfaces.exceptions import InvalidNameException
    from cloudbridge.interfaces.resources import TransferConfig
except ImportError:
    CloudProviderFactory = None  # type: ignore[assignment,misc,unused-ignore]
    ProviderList = None  # type: ignore[assignment,misc,unused-ignore]
    TransferConfig = None  # type: ignore[assignment,misc,unused-ignore]

log = logging.getLogger(__name__)

NO_CLOUDBRIDGE_ERROR_MESSAGE = (
    "Cloud ObjectStore is configured, but no CloudBridge dependency available."
    "Please install CloudBridge or modify ObjectStore configuration."
)

TRANSFER_OPTION_KEYS = ("multipart_threshold", "multipart_chunksize", "max_concurrency")
# Each option may be given bare (applies to both directions) or prefixed with
# upload_/download_ to tune one direction, mirroring the boto3 store.
ALL_TRANSFER_OPTION_KEYS = tuple(
    prefix + key for key in TRANSFER_OPTION_KEYS for prefix in ("", "upload_", "download_")
)
# Providers reject multipart upload parts smaller than 5 MiB (except the final
# part); ranged downloads have no minimum.
MIN_MULTIPART_CHUNKSIZE = 5 * 1024 * 1024


class Cloud(CachingConcreteObjectStore):
    """
    Object store that stores objects as items in an cloud storage. A local
    cache exists that is used as an intermediate location for files between
    Galaxy and the cloud storage.
    """

    store_type = "cloud"
    cloud = True

    def __init__(self, config, config_dict):
        super().__init__(config, config_dict)

        bucket_dict = config_dict["bucket"]
        cache_dict = config_dict.get("cache") or {}
        self.enable_cache_monitor, self.cache_monitor_interval = enable_cache_monitor(config, config_dict)

        self.provider = config_dict["provider"]
        self.credentials = config_dict["auth"]
        self.bucket_name = bucket_dict.get("name")
        self.use_rr = bucket_dict.get("use_reduced_redundancy", False)
        self.max_chunk_size = bucket_dict.get("max_chunk_size", 250)

        transfer_dict = config_dict.get("transfer") or {}
        self.transfer_dict = {
            key: int(transfer_dict[key]) for key in ALL_TRANSFER_OPTION_KEYS if transfer_dict.get(key) is not None
        }
        upload_chunksize = self.transfer_dict.get(
            "upload_multipart_chunksize", self.transfer_dict.get("multipart_chunksize")
        )
        if upload_chunksize is not None and upload_chunksize < MIN_MULTIPART_CHUNKSIZE:
            raise Exception(
                f"Invalid multipart_chunksize {upload_chunksize}: cloud storage providers require "
                f"multipart upload parts of at least {MIN_MULTIPART_CHUNKSIZE} bytes (5 MiB)."
            )

        # The endpoint URL's scheme carries http/https, so there is no is_secure key.
        connection_dict = config_dict.get("connection") or {}
        self.connection_dict: dict[str, Any] = {}
        for key in ("endpoint_url", "signature_version"):
            value = connection_dict.get(key)
            if value:
                self.connection_dict[key] = value
        validate_certs = connection_dict.get("validate_certs")
        if validate_certs is not None:
            self.connection_dict["validate_certs"] = asbool(validate_certs)

        # Sibling stores take the region from <connection>; accept it there too
        # rather than dropping it silently when a boto3 stanza is ported over.
        if not self.credentials.get("region") and connection_dict.get("region"):
            self.credentials = dict(self.credentials, region=connection_dict["region"])

        validate_auth(self.provider, self.credentials)

        self.cache_updated_data = cache_dict.get("cache_updated_data", True)
        self._cache_shards = CacheShardManager.from_config(cache_dict, self.config)

        self._initialize()

    def _initialize(self):
        if CloudProviderFactory is None:
            raise Exception(NO_CLOUDBRIDGE_ERROR_MESSAGE)

        self.conn = self._get_connection(self.provider, self.credentials, self.connection_dict)
        self.bucket = self._get_bucket(self.bucket_name)
        self._ensure_staging_path_writable()
        self._start_cache_monitor_if_needed()

    @staticmethod
    def _map_config_values(source: dict[str, Any], key_map: tuple[tuple[str, str], ...]) -> dict[str, Any]:
        return {mapped_key: source[key] for key, mapped_key in key_map if source.get(key) is not None}

    @staticmethod
    def _get_connection(provider: str, credentials: dict[str, Any], connection_config: dict[str, Any] | None = None):
        log.debug(f"Configuring `{provider}` Connection")
        if provider not in AUTH_KEY_MAP:
            raise Exception(f"Unsupported provider `{provider}`.")
        # An option left unset is omitted rather than passed as None, so the
        # provider falls back to its own default (for AWS, the environment and
        # then the instance role).
        config = Cloud._map_config_values(credentials, AUTH_KEY_MAP[provider])
        config.update(Cloud._map_config_values(connection_config or {}, CONNECTION_KEY_MAP.get(provider, ())))
        connection = CloudProviderFactory().create_provider(
            getattr(ProviderList, PROVIDER_LIST_NAMES[provider]), config
        )

        # Deliberately no connection.authenticate() here: cloudbridge's
        # credential check is compute-scoped (e.g. listing EC2 key pairs on
        # AWS), so a least-privilege credential authorized only for bucket
        # access would fail it even though it can fully serve the object
        # store (https://github.com/CloudVE/cloudbridge/issues/120).
        return connection

    @classmethod
    def parse_xml(clazz, config_xml):
        # The following reads common cloud-based storage configuration
        # as implemented for the S3 backend. Hence, it also attempts to
        # parse S3-specific configuration (e.g., credentials); however,
        # such provider-specific configuration is overwritten in the
        # following.
        config = parse_config_xml(config_xml)

        transfer_element = config_xml.find("transfer")
        if transfer_element is not None:
            config["transfer"] = {
                key: transfer_element.get(key)
                for key in ALL_TRANSFER_OPTION_KEYS
                if transfer_element.get(key) is not None
            }

        connection_element = config_xml.find("connection")
        if connection_element is not None:
            for key in ("endpoint_url", "validate_certs", "signature_version"):
                value = connection_element.get(key)
                if value is not None:
                    config["connection"][key] = value

        try:
            provider = config_xml.attrib.get("provider")
            if provider is None:
                msg = "Missing `provider` attribute from the Cloud backend of the ObjectStore."
                log.error(msg)
                raise Exception(msg)
            provider = provider.lower()
            config["provider"] = provider

            # Read any provider-specific configuration.
            if provider not in AUTH_KEY_MAP:
                msg = f"Unsupported provider `{provider}`."
                log.error(msg)
                raise Exception(msg)
            auth_element = config_xml.findall("auth")[0]
            auth = {}
            for key, _ in AUTH_KEY_MAP[provider]:
                if key in NON_XML_AUTH_KEYS:
                    continue
                value = auth_element.get(key)
                if value is not None:
                    auth[key] = value
            if provider == "aws":
                # An AWS store with no keys is supported (the provider then falls
                # back to the environment and the instance role), so record both
                # keys either way to keep the serialized config self-describing.
                auth.setdefault("access_key", None)
                auth.setdefault("secret_key", None)
            elif provider == "google":
                credentials_file = auth.get("credentials_file")
                if credentials_file is not None and not os.path.isfile(credentials_file):
                    msg = f"The following file specified for GCP credentials not found: {credentials_file}"
                    log.error(msg)
                    raise OSError(msg)
            config["auth"] = auth

            validate_auth(provider, auth)
            return config
        except Exception:
            log.exception("Malformed ObjectStore Configuration XML -- unable to continue")
            raise

    def to_dict(self):
        as_dict = super().to_dict()
        as_dict.update(self._config_to_dict())
        return as_dict

    def _config_to_dict(self):
        config = {
            "provider": self.provider,
            "auth": self.credentials,
            "bucket": {
                "name": self.bucket_name,
                "use_reduced_redundancy": self.use_rr,
            },
            "connection": self.connection_dict,
            "transfer": self.transfer_dict,
            "cache": self._cache_config_to_dict(),
        }
        return config

    def _transfer_config(self, direction: Literal["upload", "download"]) -> Optional["TransferConfig"]:
        # Unset values fall back to cloudbridge's CB_MULTIPART_* defaults.
        values = {}
        for key in TRANSFER_OPTION_KEYS:
            value = self.transfer_dict.get(f"{direction}_{key}", self.transfer_dict.get(key))
            if value is not None:
                values[key] = value
        if not values:
            return None
        return TransferConfig(
            threshold=values.get("multipart_threshold"),
            part_size=values.get("multipart_chunksize"),
            max_concurrency=values.get("max_concurrency"),
        )

    def _get_bucket(self, bucket_name):
        try:
            bucket = self.conn.storage.buckets.get(bucket_name)
            if bucket is None:
                log.debug("Bucket not found, creating a bucket with handle '%s'", bucket_name)
                bucket = self.conn.storage.buckets.create(bucket_name)
            log.debug("Using cloud ObjectStore with bucket '%s'", bucket.name)
            return bucket
        except InvalidNameException:
            log.exception("Invalid bucket name -- unable to continue")
            raise
        except Exception:
            # These two generic exceptions will be replaced by specific exceptions
            # once proper exceptions are exposed by CloudBridge.
            log.exception(f"Could not get bucket '{bucket_name}'")
        raise Exception(f"Could not get bucket '{bucket_name}'")

    def _get_remote_size(self, rel_path):
        try:
            obj = self.bucket.objects.get(rel_path)
            return obj.size
        except Exception:
            log.exception("Could not get size of key '%s' from S3", rel_path)
            return -1

    def _exists_remotely(self, rel_path):
        exists = False
        try:
            # A hackish way of testing if the rel_path is a folder vs a file
            is_dir = rel_path[-1] == "/"
            if is_dir:
                # One page suffices here: any match at all puts at least one
                # object on the first page.
                keyresult = self.bucket.objects.list(prefix=rel_path)
                if len(keyresult) > 0:
                    exists = True
                else:
                    exists = False
            else:
                exists = True if self.bucket.objects.get(rel_path) is not None else False
        except Exception:
            log.exception("Trouble checking existence of S3 key '%s'", rel_path)
            return False
        return exists

    def _download(self, rel_path, *, cache_path: str, cache_target: CacheTarget):
        local_destination = cache_path
        try:
            log.debug("Pulling key '%s' into cache to %s", rel_path, local_destination)
            key = self.bucket.objects.get(rel_path)
            remote_size = key.size
            if not self._caching_allowed(rel_path, cache_target=cache_target, remote_size=remote_size):
                return False
            log.debug("Pulled key '%s' into cache to %s", rel_path, local_destination)
            with self._atomic_download(local_destination) as tmp:
                self._download_to(key, tmp)
            return True
        except Exception:
            log.exception("Problem downloading key '%s' from S3 bucket '%s'", rel_path, self.bucket.name)
        return False

    def _stream_remote(self, rel_path: str) -> RemoteDataStream | None:
        key = self.bucket.objects.get(rel_path)
        if key is None:
            return None
        content = key.iter_content(chunk_size=STREAM_CHUNK_SIZE)
        # cloudbridge promises an iterable and nothing more, and what it hands back differs per
        # provider -- a wrapper around the S3 body, a swift generator, a BytesIO -- so release it
        # only if it knows how.
        return RemoteDataStream(iter(content), getattr(content, "close", lambda: None))

    def _download_directory_into_cache(self, rel_path, cache_path):
        # iter() (unlike list()) pages through the full result set.
        for obj in self.bucket.objects.iter(prefix=rel_path):
            remote_file_path = obj.name
            local_file_path = os.path.join(cache_path, os.path.relpath(remote_file_path, rel_path))
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            with self._atomic_download(local_file_path) as tmp:
                self._download_to(obj, tmp)

    def _download_to(self, key, local_destination: str) -> None:
        key.download_to_file(local_destination, config=self._transfer_config("download"))

    def _get_or_create_object(self, rel_path: str) -> Any:
        return self.bucket.objects.get(rel_path) or self.bucket.objects.create(rel_path)

    def _push_string_to_path(self, rel_path: str, from_string: str) -> bool:
        try:
            obj = self._get_or_create_object(rel_path)
            obj.upload(from_string, config=self._transfer_config("upload"))
            return True
        except Exception:
            log.exception("Trouble pushing to cloud '%s' from string", rel_path)
            return False

    def _push_file_to_path(self, rel_path: str, source_file: str) -> bool:
        try:
            obj = self._get_or_create_object(rel_path)
            obj.upload_from_file(source_file, config=self._transfer_config("upload"))
            return True
        except Exception:
            log.exception("Trouble pushing to cloud '%s' from file '%s'", rel_path, source_file)
            return False

    def _delete_remote_all(self, rel_path: str) -> bool:
        try:
            for key in self.bucket.objects.iter(prefix=rel_path):
                log.debug("Deleting key %s", key.name)
                key.delete()
            return True
        except Exception:
            log.exception("Could not delete key '%s' from cloud", rel_path)
            return False

    def _delete_existing_remote(self, rel_path: str) -> bool:
        try:
            key = self.bucket.objects.get(rel_path)
            log.debug("Deleting key %s", key.name)
            key.delete()
            return True
        except Exception:
            log.exception("Could not delete key '%s' from cloud", rel_path)
            return False

    def _get_object_url(self, obj, content_disposition=None, content_type=None, **kwargs):
        if self._exists(obj, **kwargs):
            rel_path = self._construct_path(obj, **kwargs)
            try:
                key = self.bucket.objects.get(rel_path)
                return key.generate_url(
                    expires_in=86400,  # 24hrs
                    content_disposition=content_disposition,
                    content_type=content_type,
                )
            except Exception:
                log.exception("Trouble generating URL for dataset '%s'", rel_path)
        return None

    def _get_store_usage_percent(self, obj):
        return 0.0

    def shutdown(self):
        self._shutdown_cache_monitor()
