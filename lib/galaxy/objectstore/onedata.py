"""
Object Store plugin for the Onedata Service.
"""

import logging
import os
from datetime import datetime

try:
    from onedatafilerestclient import OnedataFileRESTClient
    from onedatafilerestclient.errors import (
        OnedataError,
        OnedataRESTError,
    )
except ImportError:
    OnedataFileRESTClient = None

from galaxy.util import (
    mapped_chars,
    string_as_bool,
)
from ._caching_base import CachingConcreteObjectStore
from .caching import (
    enable_cache_monitor,
    parse_caching_config_dict_from_xml,
)

NO_ONEDATA_ERROR_MESSAGE = (
    "ObjectStore configured to use Onedata, but no OnedataFileRESTClient dependency "
    "available. Please install and properly configure Onedata or modify Object "
    "Store configuration."
)

log = logging.getLogger(__name__)

STREAM_CHUNK_SIZE = 1024 * 1024


def _parse_config_xml(config_xml):
    try:
        auth_xml = _get_config_xml_elements(config_xml, "auth")[0]
        access_token = auth_xml.get("access_token")

        conn_xml = _get_config_xml_elements(config_xml, "connection")[0]
        onezone_domain = conn_xml.get("onezone_domain")
        disable_tls_certificate_validation = string_as_bool(conn_xml.get("disable_tls_certificate_validation", "False"))

        space_xml = _get_config_xml_elements(config_xml, "space")[0]
        space_name = space_xml.get("name")
        galaxy_root_dir = space_xml.get("galaxy_root_dir", "")

        cache_dict = parse_caching_config_dict_from_xml(config_xml)

        extra_dirs = [
            {attr: elem.get(attr) for attr in ("type", "path")}
            for elem in _get_config_xml_elements(config_xml, "extra_dir")
        ]

        return {
            "auth": {"access_token": access_token},
            "connection": {
                "onezone_domain": onezone_domain,
                "disable_tls_certificate_validation": disable_tls_certificate_validation,
            },
            "space": {"name": space_name, "galaxy_root_dir": galaxy_root_dir},
            "cache": cache_dict,
            "extra_dirs": extra_dirs,
            "private": CachingConcreteObjectStore.parse_private_from_config_xml(config_xml),
        }
    except Exception:
        # Toss it back up after logging, we can't continue loading at this point.
        log.exception("Malformed Onedata ObjectStore Configuration XML -- unable to continue")
        raise


def _get_config_xml_elements(config_xml, tag):
    elements = config_xml.findall(tag)

    if not elements:
        msg = f"No {tag} element in config XML tree"
        log.error(msg)
        raise Exception(msg)

    return elements


class OnedataObjectStore(CachingConcreteObjectStore):
    """
    Object store that stores objects as items in an Onedata. A local
    cache exists that is used as an intermediate location for files between
    Galaxy and Onedata.
    """

    store_type = "onedata"

    def __init__(self, config, config_dict):
        super().__init__(config, config_dict)
        self.cache_monitor = None

        auth_dict = config_dict["auth"]
        self.access_token = auth_dict["access_token"]

        connection_dict = config_dict["connection"]
        self.onezone_domain = connection_dict["onezone_domain"]
        self.disable_tls_certificate_validation = connection_dict.get("disable_tls_certificate_validation", False)

        space_dict = config_dict["space"]
        self.space_name = space_dict["name"]
        self.galaxy_root_dir = space_dict.get("galaxy_root_dir", "")

        cache_dict = config_dict.get("cache") or {}
        self.enable_cache_monitor, self.cache_monitor_interval = enable_cache_monitor(config, config_dict)
        self.cache_size = cache_dict.get("size") or self.config.object_store_cache_size
        self.staging_path = cache_dict.get("path") or self.config.object_store_cache_path
        self.cache_updated_data = cache_dict.get("cache_updated_data", True)

        extra_dirs = {e["type"]: e["path"] for e in config_dict.get("extra_dirs", [])}
        self.extra_dirs.update(extra_dirs)

        self._initialize()

    def _initialize(self):
        if OnedataFileRESTClient is None:
            raise Exception(NO_ONEDATA_ERROR_MESSAGE)

        log.debug(
            f"Configuring Onedata connection to {self.onezone_domain} "
            f"(disable_tls_certificate_validation={self.disable_tls_certificate_validation})"
        )

        alt_space_fqn_separators = [mapped_chars["@"]] if "@" in mapped_chars else None
        verify_ssl = not self.disable_tls_certificate_validation
        self._client = OnedataFileRESTClient(
            self.onezone_domain,
            self.access_token,
            alt_space_fqn_separators=alt_space_fqn_separators,
            verify_ssl=verify_ssl,
        )

        self._ensure_staging_path_writable()
        self._start_cache_monitor_if_needed()

    @classmethod
    def parse_xml(cls, config_xml):
        return _parse_config_xml(config_xml)

    def to_dict(self):
        as_dict = super().to_dict()
        as_dict.update(
            {
                "auth": {
                    "access_token": self.access_token,
                },
                "connection": {
                    "onezone_domain": self.onezone_domain,
                    "disable_tls_certificate_validation": self.disable_tls_certificate_validation,
                },
                "space": {"name": self.space_name, "galaxy_root_dir": self.galaxy_root_dir},
                "cache": {
                    "size": self.cache_size,
                    "path": self.staging_path,
                    "cache_updated_data": self.cache_updated_data,
                },
            }
        )
        return as_dict

    def _build_remote_path(self, rel_path):
        return os.path.join(self.galaxy_root_dir, rel_path)

    def _get_remote_size(self, rel_path):
        try:
            remote_path = self._build_remote_path(rel_path)
            return self._client.get_attributes(self.space_name, attributes=["size"], file_path=remote_path)["size"]
        except OnedataError:
            log.exception("Could not get '%s' size from Onedata", rel_path)
            return -1

    def _exists_remotely(self, rel_path):
        try:
            remote_path = self._build_remote_path(rel_path)
            self._client.get_attributes(self.space_name, attributes=["type", "size"], file_path=remote_path)
            return True
        except OnedataError as ex:
            if _is_not_found_onedata_rest_error(ex):
                return False

            log.exception("Trouble checking '%s' existence in Onedata", rel_path)
            return False

    def _download(self, rel_path):
        try:
            dst_path = self._get_cache_path(rel_path)

            log.debug("Pulling file '%s' into cache to %s", rel_path, dst_path)

            remote_path = self._build_remote_path(rel_path)
            file_size = self._client.get_attributes(self.space_name, attributes=["size"], file_path=remote_path)["size"]

            # Test if cache is large enough to hold the new file
            if not self._caching_allowed(rel_path, file_size):
                return False

            with open(dst_path, "wb") as dst:
                for chunk in self._client.iter_file_content(
                    self.space_name, chunk_size=STREAM_CHUNK_SIZE, file_path=remote_path
                ):
                    dst.write(chunk)

            log.debug("Pulled '%s' into cache to %s", rel_path, dst_path)

            return True
        except OnedataError:
            log.exception("Problem downloading file '%s'", rel_path)
            return False

    def _push_to_storage(self, rel_path, source_file=None, from_string=None):
        """
        Push the file pointed to by ``rel_path`` to the object store under ``rel_path``.
        If ``source_file`` is provided, push that file instead while still using
        ``rel_path`` as the path.
        """
        try:
            source_file = source_file or self._get_cache_path(rel_path)
            if os.path.exists(source_file):
                if os.path.getsize(source_file) == 0 and self._exists_remotely(rel_path):
                    log.debug(
                        "Wanted to push file '%s' to Onedata '%s' but its size is 0; skipping.", source_file, rel_path
                    )
                    return True
                else:
                    start_time = datetime.now()
                    log.debug(
                        "Pushing cache file '%s' of size %s bytes under '%s'",
                        source_file,
                        os.path.getsize(source_file),
                        rel_path,
                    )
                    remote_path = self._build_remote_path(rel_path)

                    if not self._exists_remotely(rel_path):
                        file_id = self._client.create_file(
                            self.space_name, file_path=remote_path, file_type="REG", create_parents=True
                        )
                    else:
                        file_id = self._client.get_file_id(self.space_name, file_path=remote_path)

                    if source_file:
                        with open(source_file, "rb") as src:
                            offset = 0
                            while True:
                                chunk = src.read(STREAM_CHUNK_SIZE)
                                if not chunk:
                                    break

                                self._client.put_file_content(
                                    self.space_name, data=chunk, offset=offset, file_id=file_id
                                )
                                offset += len(chunk)
                    else:
                        self._client.put_file_content(
                            self.space_name, data=from_string.encode("utf-8"), file_id=file_id
                        )

                    end_time = datetime.now()
                    log.debug(
                        "Pushed cache file '%s' under '%s' (%s bytes transferred in %s sec)",
                        source_file,
                        rel_path,
                        os.path.getsize(source_file),
                        end_time - start_time,
                    )
                return True
            else:
                log.error("Source file does not exist.", rel_path, source_file)
        except OnedataError:
            log.exception("Trouble pushing Onedata key '%s' from file '%s'", rel_path, source_file)
            raise
        return False

    def _delete_existing_remote(self, rel_path) -> bool:
        try:
            onedata_path = self._build_remote_path(rel_path)
            self._client.remove(self.space_name, file_path=onedata_path)
            return True
        except OnedataError:
            log.exception("Could not delete '%s' from Onedata", rel_path)
            return False

    def _get_object_url(self, _obj, **_kwargs):
        return None

    def _get_store_usage_percent(self, _obj):
        return 0.0

    def shutdown(self):
        self._shutdown_cache_monitor()


def _is_not_found_onedata_rest_error(ex):
    if isinstance(ex, OnedataRESTError):
        if ex.http_code == 404:
            return True

        if ex.http_code == 400 and ex.category == "posix":
            return ex.details["errno"] == "enoent"

    return False
