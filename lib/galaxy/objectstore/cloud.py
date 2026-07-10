"""
Object Store plugin for Cloud storage.
"""

import logging
import os
import os.path

from galaxy.util import string_as_bool
from ._caching_base import CachingConcreteObjectStore
from ._util import UsesAxel
from .caching import enable_cache_monitor
from .s3 import parse_config_xml

try:
    from cloudbridge.factory import (
        CloudProviderFactory,
        ProviderList,
    )
    from cloudbridge.interfaces.exceptions import InvalidNameException
    from cloudbridge.interfaces.resources import UploadConfig
except ImportError:
    CloudProviderFactory = None  # type: ignore[assignment,misc,unused-ignore]
    ProviderList = None  # type: ignore[assignment,misc,unused-ignore]
    UploadConfig = None  # type: ignore[assignment,misc,unused-ignore]

log = logging.getLogger(__name__)

NO_CLOUDBRIDGE_ERROR_MESSAGE = (
    "Cloud ObjectStore is configured, but no CloudBridge dependency available."
    "Please install CloudBridge or modify ObjectStore configuration."
)

TRANSFER_OPTION_KEYS = ("multipart_threshold", "multipart_chunksize", "max_concurrency")
# Providers reject multipart parts smaller than 5 MiB (except the final part).
MIN_MULTIPART_CHUNKSIZE = 5 * 1024 * 1024


class Cloud(CachingConcreteObjectStore, UsesAxel):
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
            key: int(transfer_dict[key]) for key in TRANSFER_OPTION_KEYS if transfer_dict.get(key) is not None
        }
        chunksize = self.transfer_dict.get("multipart_chunksize")
        if chunksize is not None and chunksize < MIN_MULTIPART_CHUNKSIZE:
            raise Exception(
                f"Invalid multipart_chunksize {chunksize}: cloud storage providers require "
                f"multipart parts of at least {MIN_MULTIPART_CHUNKSIZE} bytes (5 MiB)."
            )

        # The endpoint scheme conveys http/https, so no is_secure here (matching
        # the boto3 store); the legacy host/port/... keys the s3 parser emits are
        # not used by this store.
        connection_dict = config_dict.get("connection") or {}
        self.connection_dict = {}
        for key in ("endpoint_url", "signature_version"):
            value = connection_dict.get(key)
            if value:
                self.connection_dict[key] = value
        validate_certs = connection_dict.get("validate_certs")
        if validate_certs is not None:
            self.connection_dict["validate_certs"] = string_as_bool(validate_certs)

        if self.provider == "google":
            has_file = bool(self.credentials.get("credentials_file"))
            has_dict = bool(self.credentials.get("credentials_dict"))
            if has_file == has_dict:
                raise Exception(
                    "The google provider requires exactly one of credentials_file or credentials_dict."
                )

        self.cache_size = cache_dict.get("size") or self.config.object_store_cache_size
        self.staging_path = cache_dict.get("path") or self.config.object_store_cache_path
        self.cache_updated_data = cache_dict.get("cache_updated_data", True)

        self._initialize()

    def _initialize(self):
        if CloudProviderFactory is None:
            raise Exception(NO_CLOUDBRIDGE_ERROR_MESSAGE)

        self.conn = self._get_connection(self.provider, self.credentials, self.connection_dict)
        self.bucket = self._get_bucket(self.bucket_name)
        self._ensure_staging_path_writable()
        self._start_cache_monitor_if_needed()
        self._init_axel()

    @staticmethod
    def _map_config_values(source, key_map):
        return {mapped_key: source[key] for key, mapped_key in key_map if source.get(key) is not None}

    @staticmethod
    def _get_connection(provider, credentials, connection_config=None):
        log.debug(f"Configuring `{provider}` Connection")
        connection_config = connection_config or {}
        if provider == "aws":
            config = {"aws_access_key": credentials.get("access_key"), "aws_secret_key": credentials.get("secret_key")}
            config.update(
                Cloud._map_config_values(
                    credentials,
                    (
                        ("session_token", "aws_session_token"),
                        ("region", "aws_region_name"),
                    ),
                )
            )
            config.update(
                Cloud._map_config_values(
                    connection_config,
                    (
                        ("endpoint_url", "s3_endpoint_url"),
                        ("validate_certs", "s3_validate_certs"),
                        ("signature_version", "s3_signature_version"),
                    ),
                )
            )
            connection = CloudProviderFactory().create_provider(ProviderList.AWS, config)
        elif provider == "azure":
            config = Cloud._map_config_values(
                credentials,
                (
                    ("subscription_id", "azure_subscription_id"),
                    ("client_id", "azure_client_id"),
                    ("secret", "azure_secret"),
                    ("tenant", "azure_tenant"),
                    ("access_token", "azure_access_token"),
                    ("storage_account", "azure_storage_account"),
                    ("resource_group", "azure_resource_group"),
                    ("region", "azure_region_name"),
                ),
            )
            connection = CloudProviderFactory().create_provider(ProviderList.AZURE, config)
        elif provider == "google":
            config = Cloud._map_config_values(
                credentials,
                (
                    ("credentials_file", "gcp_service_creds_file"),
                    ("credentials_dict", "gcp_service_creds_dict"),
                    ("region", "gcp_region_name"),
                ),
            )
            connection = CloudProviderFactory().create_provider(ProviderList.GCP, config)
        else:
            raise Exception(f"Unsupported provider `{provider}`.")

        # Ideally it would be better to assert if the connection is
        # authorized to perform operations required by ObjectStore
        # before returning it (and initializing ObjectStore); hence
        # any related issues can be handled properly here, and ObjectStore
        # can "trust" the connection is established.
        #
        # However, the mechanism implemented in Cloudbridge to assert if
        # a user/service is authorized to perform an operation, assumes
        # the user/service is granted with an elevated privileges, such
        # as admin/owner-level access to all resources. For a detailed
        # discussion see:
        #
        # https://github.com/CloudVE/cloudbridge/issues/135
        #
        # Hence, if a resource owner wants to only authorize Galaxy to r/w
        # a bucket/container on the provider, but does not allow it to access
        # other resources, Cloudbridge may fail asserting credentials.
        # For instance, to r/w an Amazon S3 bucket, the resource owner
        # also needs to authorize full access to Amazon EC2, because Cloudbridge
        # leverages EC2-specific functions to assert the credentials.
        #
        # Therefore, to adhere with principle of least privilege, we do not
        # assert credentials; instead, we handle exceptions raised as a
        # result of signing API calls to cloud provider (e.g., GCP) using
        # incorrect, invalid, or unauthorized credentials.

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
                key: transfer_element.get(key) for key in TRANSFER_OPTION_KEYS if transfer_element.get(key) is not None
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
            auth_element = config_xml.findall("auth")[0]
            missing_config = []
            if provider == "aws":
                akey = auth_element.get("access_key")
                skey = auth_element.get("secret_key")
                config["auth"] = {"access_key": akey, "secret_key": skey}
                for key in ("session_token", "region"):
                    value = auth_element.get(key)
                    if value:
                        config["auth"][key] = value
            elif provider == "azure":
                auth = {}
                for key in (
                    "subscription_id",
                    "client_id",
                    "secret",
                    "tenant",
                    "access_token",
                    "storage_account",
                    "resource_group",
                    "region",
                ):
                    value = auth_element.get(key)
                    if value is not None:
                        auth[key] = value
                if "access_token" not in auth:
                    # Without an access token the service-principal quartet is required.
                    for key in ("subscription_id", "client_id", "secret", "tenant"):
                        if key not in auth:
                            missing_config.append(key)
                config["auth"] = auth
            elif provider == "google":
                cre = auth_element.get("credentials_file")
                if cre is None:
                    missing_config.append("credentials_file")
                elif not os.path.isfile(cre):
                    msg = f"The following file specified for GCP credentials not found: {cre}"
                    log.error(msg)
                    raise OSError(msg)
                config["auth"] = {"credentials_file": cre}
                region = auth_element.get("region")
                if region:
                    config["auth"]["region"] = region
            else:
                msg = f"Unsupported provider `{provider}`."
                log.error(msg)
                raise Exception(msg)

            if len(missing_config) > 0:
                msg = f"The following configuration required for {provider} cloud backend are missing: {missing_config}"
                log.error(msg)
                raise Exception(msg)
            else:
                return config
        except Exception:
            log.exception("Malformed ObjectStore Configuration XML -- unable to continue")
            raise

    def to_dict(self):
        as_dict = super().to_dict()
        as_dict.update(self._config_to_dict())
        return as_dict

    def _config_to_dict(self):
        return {
            "provider": self.provider,
            "auth": self.credentials,
            "bucket": {
                "name": self.bucket_name,
                "use_reduced_redundancy": self.use_rr,
            },
            "connection": self.connection_dict,
            "transfer": self.transfer_dict,
            "cache": {
                "size": self.cache_size,
                "path": self.staging_path,
                "cache_updated_data": self.cache_updated_data,
            },
        }

    def _upload_config(self):
        # Any value left unset falls back to cloudbridge's own defaults (the
        # CB_MULTIPART_* settings); with nothing configured pass no config at all.
        if not self.transfer_dict:
            return None
        return UploadConfig(
            threshold=self.transfer_dict.get("multipart_threshold"),
            part_size=self.transfer_dict.get("multipart_chunksize"),
            max_concurrency=self.transfer_dict.get("max_concurrency"),
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
        raise Exception

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

    def _download(self, rel_path):
        local_destination = self._get_cache_path(rel_path)
        try:
            log.debug("Pulling key '%s' into cache to %s", rel_path, local_destination)
            key = self.bucket.objects.get(rel_path)
            remote_size = key.size
            if not self._caching_allowed(rel_path, remote_size):
                return False
            log.debug("Pulled key '%s' into cache to %s", rel_path, local_destination)
            with self._atomic_download(local_destination) as tmp:
                self._download_to(key, tmp)
            return True
        except Exception:
            log.exception("Problem downloading key '%s' from S3 bucket '%s'", rel_path, self.bucket.name)
        return False

    def _download_directory_into_cache(self, rel_path, cache_path):
        objects = self.bucket.objects.list(prefix=rel_path)
        for obj in objects:
            remote_file_path = obj.name
            local_file_path = os.path.join(cache_path, os.path.relpath(remote_file_path, rel_path))
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            with self._atomic_download(local_file_path) as tmp:
                self._download_to(obj, tmp)

    def _download_to(self, key, local_destination):
        if self.use_axel:
            url = key.generate_url(7200)
            return self._axel_download(url, local_destination)
        else:
            with open(local_destination, "wb+") as downloaded_file_handle:
                key.save_content(downloaded_file_handle)

    def _get_or_create_object(self, rel_path: str):
        return self.bucket.objects.get(rel_path) or self.bucket.objects.create(rel_path)

    def _push_string_to_path(self, rel_path: str, from_string: str) -> bool:
        try:
            obj = self._get_or_create_object(rel_path)
            obj.upload(from_string, config=self._upload_config())
            return True
        except Exception:
            log.exception("Trouble pushing to cloud '%s' from string", rel_path)
            return False

    def _push_file_to_path(self, rel_path: str, source_file: str) -> bool:
        try:
            obj = self._get_or_create_object(rel_path)
            obj.upload_from_file(source_file, config=self._upload_config())
            return True
        except Exception:
            log.exception("Trouble pushing to cloud '%s' from file '%s'", rel_path, source_file)
            return False

    def _delete_remote_all(self, rel_path: str) -> bool:
        try:
            results = self.bucket.objects.list(prefix=rel_path)
            for key in results:
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
