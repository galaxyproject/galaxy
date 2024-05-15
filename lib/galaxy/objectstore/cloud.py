"""
Object Store plugin for Cloud storage.
"""

import logging
import os
import os.path

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
except ImportError:
    CloudProviderFactory = None
    ProviderList = None

log = logging.getLogger(__name__)

NO_CLOUDBRIDGE_ERROR_MESSAGE = (
    "Cloud ObjectStore is configured, but no CloudBridge dependency available."
    "Please install CloudBridge or modify ObjectStore configuration."
)


class Cloud(CachingConcreteObjectStore, UsesAxel):
    """
    Object store that stores objects as items in an cloud storage. A local
    cache exists that is used as an intermediate location for files between
    Galaxy and the cloud storage.
    """

    store_type = "cloud"

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

        self.cache_size = cache_dict.get("size") or self.config.object_store_cache_size
        self.staging_path = cache_dict.get("path") or self.config.object_store_cache_path
        self.cache_updated_data = cache_dict.get("cache_updated_data", True)

        self._initialize()

    def _initialize(self):
        if CloudProviderFactory is None:
            raise Exception(NO_CLOUDBRIDGE_ERROR_MESSAGE)

        self.conn = self._get_connection(self.provider, self.credentials)
        self.bucket = self._get_bucket(self.bucket_name)
        self._ensure_staging_path_writable()
        self._start_cache_monitor_if_needed()
        self._init_axel()

    @staticmethod
    def _get_connection(provider, credentials):
        log.debug(f"Configuring `{provider}` Connection")
        if provider == "aws":
            config = {"aws_access_key": credentials["access_key"], "aws_secret_key": credentials["secret_key"]}
            if "region" in credentials:
                config["aws_region_name"] = credentials["region"]
            connection = CloudProviderFactory().create_provider(ProviderList.AWS, config)
        elif provider == "azure":
            config = {
                "azure_subscription_id": credentials["subscription_id"],
                "azure_client_id": credentials["client_id"],
                "azure_secret": credentials["secret"],
                "azure_tenant": credentials["tenant"],
            }
            connection = CloudProviderFactory().create_provider(ProviderList.AZURE, config)
        elif provider == "google":
            config = {"gcp_service_creds_file": credentials["credentials_file"]}
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
                if "region" in auth_element:
                    config["auth"]["region"] = auth_element["region"]
            elif provider == "azure":
                sid = auth_element.get("subscription_id")
                if sid is None:
                    missing_config.append("subscription_id")
                cid = auth_element.get("client_id")
                if cid is None:
                    missing_config.append("client_id")
                sec = auth_element.get("secret")
                if sec is None:
                    missing_config.append("secret")
                ten = auth_element.get("tenant")
                if ten is None:
                    missing_config.append("tenant")
                config["auth"] = {"subscription_id": sid, "client_id": cid, "secret": sec, "tenant": ten}
            elif provider == "google":
                cre = auth_element.get("credentials_file")
                if not os.path.isfile(cre):
                    msg = f"The following file specified for GCP credentials not found: {cre}"
                    log.error(msg)
                    raise OSError(msg)
                if cre is None:
                    missing_config.append("credentials_file")
                config["auth"] = {"credentials_file": cre}
            else:
                msg = f"Unsupported provider `{provider}`."
                log.error(msg)
                raise Exception(msg)

            if len(missing_config) > 0:
                msg = (
                    f"The following configuration required for {provider} cloud backend "
                    f"are missing: {missing_config}"
                )
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
            "cache": {
                "size": self.cache_size,
                "path": self.staging_path,
                "cache_updated_data": self.cache_updated_data,
            },
        }

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
            self._download_to(key, local_destination)
            return True
        except Exception:
            log.exception("Problem downloading key '%s' from S3 bucket '%s'", rel_path, self.bucket.name)
        return False

    def _download_directory_into_cache(self, rel_path, cache_path):
        # List objects in the specified cloud folder
        objects = self.bucket.objects.list(prefix=rel_path)

        for obj in objects:
            remote_file_path = obj.name
            local_file_path = os.path.join(cache_path, os.path.relpath(remote_file_path, rel_path))

            # Create directories if they don't exist
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

            # Download the file
            self._download_to(obj, local_file_path)

    def _download_to(self, key, local_destination):
        if self.use_axel:
            url = key.generate_url(7200)
            return self._axel_download(url, local_destination)
        else:
            with open(local_destination, "wb+") as downloaded_file_handle:
                key.save_content(downloaded_file_handle)

    def _push_string_to_path(self, rel_path: str, from_string: str) -> bool:
        try:
            if not self.bucket.objects.get(rel_path):
                created_obj = self.bucket.objects.create(rel_path)
                created_obj.upload(from_string)
            else:
                self.bucket.objects.get(rel_path).upload(from_string)
            return True
        except Exception:
            log.exception("Trouble pushing to cloud '%s' from string", rel_path)
            return False

    def _push_file_to_path(self, rel_path: str, source_file: str) -> bool:
        try:
            if not self.bucket.objects.get(rel_path):
                created_obj = self.bucket.objects.create(rel_path)
                created_obj.upload_from_file(source_file)
            else:
                self.bucket.objects.get(rel_path).upload_from_file(source_file)
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

    def _get_object_url(self, obj, **kwargs):
        if self._exists(obj, **kwargs):
            rel_path = self._construct_path(obj, **kwargs)
            try:
                key = self.bucket.objects.get(rel_path)
                return key.generate_url(expires_in=86400)  # 24hrs
            except Exception:
                log.exception("Trouble generating URL for dataset '%s'", rel_path)
        return None

    def _get_store_usage_percent(self, obj):
        return 0.0

    def shutdown(self):
        self._shutdown_cache_monitor()
