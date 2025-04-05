import hashlib
import logging
import os
import shutil
from typing import Optional

try:
    import rucio.common
    from rucio.client import Client
    from rucio.client.downloadclient import DownloadClient
    from rucio.client.uploadclient import UploadClient

    from .rucio_extra_clients import (
        DeleteClient,
        InPlaceIngestClient,
    )
except ImportError:
    Client = None

try:
    from galaxy.authnz.util import provider_name_to_backend
except ImportError:
    provider_name_to_backend = None  # type: ignore[assignment, unused-ignore]

from galaxy.exceptions import (
    ObjectInvalid,
    ObjectNotFound,
)
from galaxy.util import (
    directory_hash_id,
    string_as_bool,
    umask_fix_perms,
    unlink,
)
from ._caching_base import CachingConcreteObjectStore
from .caching import (
    enable_cache_monitor,
    parse_caching_config_dict_from_xml,
)

log = logging.getLogger(__name__)

NO_RUCIO_ERROR_MESSAGE = (
    "ObjectStore configured to use Rucio, but no rucio-clients dependency available."
    "Please install and properly configure rucio-clients or modify Object "
    "Store configuration."
)


def _config_xml_error(tag):
    msg = f"No {tag} element in config XML tree"
    raise Exception(msg)


def _config_dict_error(key):
    msg = f"No {key} key in config dictionary"
    raise Exception(msg)


def _encode_key(input_string):
    input_bytes = input_string.encode("utf-8")
    sha256_hash = hashlib.sha256(input_bytes)
    hashed_string = sha256_hash.hexdigest()
    return hashed_string


def parse_config_xml(config_xml):
    try:
        cache_dict = parse_caching_config_dict_from_xml(config_xml)

        attrs = ("type", "path")
        e_xml = config_xml.findall("extra_dir")
        if not e_xml:
            _config_xml_error("extra_dir")
        extra_dirs = [{k: e.get(k) for k in attrs} for e in e_xml]

        attrs_schemes = ("rse", "scheme", "ignore_checksum")
        e_xml = config_xml.findall("rucio_download_scheme")
        rucio_download_schemes = []
        if e_xml:
            rucio_download_schemes = [{k: e.get(k) for k in attrs_schemes} for e in e_xml]

        oidc_provider = config_xml.findtext("oidc_provider", None)
        enable_cache_mon = string_as_bool(config_xml.findtext("enable_cache_monitor", "False"))

        e_xml = config_xml.findall("rucio_upload_scheme")
        if e_xml:
            rucio_upload_rse_name = e_xml[0].get("rse", None)
            rucio_upload_scheme = e_xml[0].get("scheme", None)
            rucio_scope = e_xml[0].get("scope", None)
            rucio_register_only = string_as_bool(e_xml[0].get("register_only", "False"))
        else:
            rucio_upload_rse_name = None
            rucio_upload_scheme = None
            rucio_scope = None
            rucio_register_only = False
            oidc_provider = None

        e_xml = config_xml.findall("rucio_auth")
        if not e_xml:
            _config_xml_error("rucio_auth")
        rucio_account = e_xml[0].get("account", None)
        rucio_auth_host = e_xml[0].get("host", None)
        rucio_username = e_xml[0].get("username", None)
        rucio_password = e_xml[0].get("password", None)
        rucio_auth_type = e_xml[0].get("type", "userpass")

        e_xml = config_xml.findall("rucio_connection")
        if not e_xml:
            _config_xml_error("rucio_connection")
        rucio_host = e_xml[0].get("host", None)

        rucio_dict = {
            "upload_rse_name": rucio_upload_rse_name,
            "upload_scheme": rucio_upload_scheme,
            "scope": rucio_scope,
            "register_only": rucio_register_only,
            "download_schemes": rucio_download_schemes,
            "account": rucio_account,
            "auth_host": rucio_auth_host,
            "username": rucio_username,
            "password": rucio_password,
            "auth_type": rucio_auth_type,
            "host": rucio_host,
        }

        return {
            "cache": cache_dict,
            "rucio": rucio_dict,
            "extra_dirs": extra_dirs,
            "oidc_provider": oidc_provider,
            "enable_cache_monitor": enable_cache_mon,
        }
    except Exception:
        # Toss it back up after logging, we can't continue loading at this point.
        log.exception("Malformed Rucio ObjectStore Configuration XML -- unable to continue.")
        raise


class RucioBroker:
    def __init__(self, rucio_object_store):
        self._temp_file_name = None
        self.rucio_config_path: Optional[str] = None
        self.config = rucio_object_store.rucio_config
        self.extra_dirs = rucio_object_store.extra_dirs
        self.upload_scheme = self.config["upload_scheme"]
        self.upload_rse_name = self.config["upload_rse_name"]
        self.scope = self.config["scope"]
        self.register_only = self.config["register_only"]
        self.download_schemes = self.config["download_schemes"]
        if Client is None:
            raise Exception(NO_RUCIO_ERROR_MESSAGE)
        rucio.common.utils.PREFERRED_CHECKSUM = "md5"

    def get_rucio_client(self):
        if not self.rucio_config_path:
            temp_directory = self.extra_dirs["temp"]
            self.rucio_config_path = os.path.join(temp_directory, "rucio.cfg")
            key_for_pass = "password"
            with open(self.rucio_config_path, "w") as f:
                f.write(
                    f"""[client]
rucio_host = {self.config['host']}
auth_host = {self.config['auth_host']}
account = {self.config['account']}
auth_type = {self.config['auth_type']}
username = {self.config['username']}
{key_for_pass} = {self.config[key_for_pass]}
"""
                )
        # We may have crossed a forkpool boundary. No harm setting the env var again.
        # Fixes rucio integration tests
        os.environ["RUCIO_CONFIG"] = self.rucio_config_path
        client = Client(
            rucio_host=self.config["host"],
            auth_host=self.config["auth_host"],
            account=self.config["account"],
            auth_type=self.config["auth_type"],
            creds={"username": self.config["username"], "password": self.config["password"]},
        )
        return client

    def get_rucio_upload_client(self, auth_token=None):
        client = self.get_rucio_client()
        uc = UploadClient(_client=client)
        uc.auth_token = auth_token
        return uc

    def get_rucio_download_client(self, auth_token=None):
        client = self.get_rucio_client()
        dc = DownloadClient(client=client)
        dc.auth_token = auth_token
        return dc

    def get_rucio_ingest_client(self, auth_token=None):
        client = self.get_rucio_client()
        ic = InPlaceIngestClient(_client=client)
        ic.auth_token = auth_token
        return ic

    def get_rucio_delete_client(self, auth_token=None):
        client = self.get_rucio_client()
        ic = DeleteClient(_client=client)
        ic.auth_token = auth_token
        return ic

    def register(self, key, source_path):
        key = _encode_key(key)
        item = {
            "path": source_path,
            "rse": self.upload_rse_name,
            "did_scope": self.scope,
            "did_name": key,
            "pfn": f"file://localhost/{source_path}",
        }
        items = [item]
        self.get_rucio_ingest_client().ingest(items)

    def upload(self, key, source_path):
        key = _encode_key(key)
        item = {
            "path": source_path,
            "rse": self.upload_rse_name,
            "did_scope": self.scope,
            "did_name": key,
            "force_scheme": self.upload_scheme,
        }
        items = [item]
        self.get_rucio_upload_client().upload(items)

    def download(self, key, dest_path, auth_token):
        key = _encode_key(key)
        base_dir = os.path.dirname(dest_path)
        dids = [{"scope": self.scope, "name": key}]
        try:
            repl = next(self.get_rucio_client().list_replicas(dids))["rses"].keys()
            item = None
            for rse_scheme in self.download_schemes:
                if rse_scheme["rse"] in repl:
                    item = {
                        "did": f"{self.scope}:{key}",
                        "force_scheme": rse_scheme["scheme"],
                        "rse": rse_scheme["rse"],
                        "base_dir": base_dir,
                        "check_local_with_filesize_only": string_as_bool(rse_scheme["ignore_checksum"]),
                        "ignore_checksum": string_as_bool(rse_scheme["ignore_checksum"]),
                        "no_subdir": True,
                    }
                    break
            if item is None:
                item = {
                    "did": f"{self.scope}:{key}",
                    "base_dir": base_dir,
                    "no_subdir": True,
                }
            items = [item]
            download_client = self.get_rucio_download_client(auth_token=auth_token)
            download_client.download_dids(items)
        except Exception as e:
            log.exception(f"Cannot download file: {str(e)}")
            return False
        return True

    def data_object_exists(self, key):
        key = _encode_key(key)
        dids = [{"scope": self.scope, "name": key}]
        try:
            repl = next(self.get_rucio_client().list_replicas(dids))
            return "AVAILABLE" in repl["states"].values()
        except Exception:
            return False

    def get_size(self, key) -> int:
        key = _encode_key(key)
        dids = [{"scope": self.scope, "name": key}]
        try:
            repl = next(self.get_rucio_client().list_replicas(dids))
            return int(repl["bytes"])
        except Exception:
            return 0

    def delete(self, key, auth_token):
        key = _encode_key(key)
        try:
            items = [{"did": {"scope": self.scope, "name": key}}]
            self.get_rucio_delete_client(auth_token=auth_token).delete(items, self.download_schemes, True)
        except Exception as e:
            log.exception(f"Cannot delete file: {e}")
            return False
        return True


class RucioObjectStore(CachingConcreteObjectStore):
    """
    Object store implementation that uses ORNL remote data broker.

    This implementation should be considered beta and may be dropped from
    Galaxy at some future point or significantly modified.
    """

    store_type = "rucio"

    def to_dict(self):
        rval = super().to_dict()
        rval["rucio"] = self.rucio_config
        rval["cache"] = self.cache_config
        rval["oidc_provider"] = self.oidc_provider
        rval["enable_cache_monitor"] = self.enable_cache_monitor
        return rval

    def __init__(self, config, config_dict):
        super().__init__(config, config_dict)
        self.rucio_config = config_dict.get("rucio") or {}

        self.oidc_provider = config_dict.get("oidc_provider", None)
        self.rucio_broker = RucioBroker(self)
        cache_dict = config_dict.get("cache") or {}
        self.enable_cache_monitor, self.cache_monitor_interval = enable_cache_monitor(config, config_dict)

        self.cache_size = cache_dict.get("size") or self.config.object_store_cache_size
        self.staging_path = cache_dict.get("path") or self.config.object_store_cache_path
        self.cache_updated_data = cache_dict.get("cache_updated_data", True)
        self.cache_config = cache_dict
        self._initialize()

    def _initialize(self):
        self._ensure_staging_path_writable()
        self._start_cache_monitor_if_needed()

    def _pull_into_cache(self, rel_path, **kwargs) -> bool:
        log.debug("rucio _pull_into_cache: %s", rel_path)
        # Ensure the cache directory structure exists (e.g., dataset_#_files/)
        rel_path_dir = os.path.dirname(rel_path)
        if not os.path.exists(self._get_cache_path(rel_path_dir)):
            os.makedirs(self._get_cache_path(rel_path_dir), exist_ok=True)
        # Now pull in the file
        dest = self._get_cache_path(rel_path)
        auth_token = self._get_token(**kwargs)
        file_ok = self.rucio_broker.download(rel_path, dest, auth_token)
        self._fix_permissions(self._get_cache_path(rel_path_dir))
        return file_ok

    def _fix_file_permissions(self, path):
        umask_fix_perms(path, self.config.umask, 0o666)

    def _fix_permissions(self, rel_path):
        """Set permissions on rel_path"""
        for basedir, _, files in os.walk(rel_path):
            umask_fix_perms(basedir, self.config.umask, 0o777)
            for filename in files:
                path = os.path.join(basedir, filename)
                # Ignore symlinks
                if os.path.islink(path):
                    continue
                umask_fix_perms(path, self.config.umask, 0o666)

    # "interfaces to implement"

    def _exists(self, obj, **kwargs) -> bool:
        rel_path = self._construct_path(obj, **kwargs)
        log.debug("rucio _exists: %s", rel_path)

        dir_only = kwargs.get("dir_only", False)
        base_dir = kwargs.get("base_dir", None)

        # Check cache and rucio
        if self._in_cache(rel_path) or (not dir_only and self.rucio_broker.data_object_exists(rel_path)):
            return True

        # dir_only does not get synced so shortcut the decision
        if dir_only and base_dir:
            # for JOB_WORK directory
            if not os.path.exists(rel_path):
                os.makedirs(rel_path, exist_ok=True)
            return True
        return False

    @classmethod
    def parse_xml(cls, config_xml):
        return parse_config_xml(config_xml)

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

            if not dir_only:
                rel_path = os.path.join(rel_path, alt_name if alt_name else f"dataset_{self._get_object_id(obj)}.dat")
                # need this line to set the dataset filename, not sure how this is done - filesystem is monitored?
                open(os.path.join(self.staging_path, rel_path), "w").close()
            log.debug("rucio _create: %s", rel_path)
        return self

    def _size(self, obj, **kwargs) -> int:
        rel_path = self._construct_path(obj, **kwargs)
        log.debug("rucio _size: %s", rel_path)

        if self._in_cache(rel_path):
            size: Optional[int] = None
            try:
                size = os.path.getsize(self._get_cache_path(rel_path))
            except OSError as ex:
                log.info("Could not get size of file '%s' in local cache, will try iRODS. Error: %s", rel_path, ex)
            if size is not None:
                return size
        if self._exists(obj, **kwargs):
            return self._get_remote_size(rel_path)
        log.warning("Did not find dataset '%s', returning 0 for size", rel_path)
        return 0

    def _get_remote_size(self, rel_path) -> int:
        return self.rucio_broker.get_size(rel_path)

    def _delete(self, obj, entire_dir: bool = False, **kwargs) -> bool:
        rel_path = self._construct_path(obj, **kwargs)
        extra_dir = kwargs.get("extra_dir", None)
        base_dir = kwargs.get("base_dir", None)
        dir_only = kwargs.get("dir_only", False)
        obj_dir = kwargs.get("obj_dir", False)
        log.debug("rucio _delete: %s", rel_path)
        auth_token = self._get_token(**kwargs)

        try:
            # Remove temporary data in JOB_WORK directory
            if base_dir and dir_only and obj_dir:
                shutil.rmtree(os.path.abspath(rel_path))
                return True

            # Delete from cache first
            if entire_dir and extra_dir:
                shutil.rmtree(self._get_cache_path(rel_path), ignore_errors=True)
            else:
                unlink(self._get_cache_path(rel_path), ignore_errors=True)

            # Delete from rucio as well
            if self.rucio_broker.data_object_exists(rel_path):
                self.rucio_broker.delete(rel_path, auth_token)
                return True
        except OSError:
            log.exception("%s delete error", self._get_filename(obj, **kwargs))
        return False

    def _get_token(self, **kwargs):
        auth_token = kwargs.get("auth_token", None)
        if auth_token:
            return auth_token

        arg_user = kwargs.get("user", None)
        try:
            if not arg_user:
                trans = kwargs.get("trans", None)
                user = trans.user
            else:
                user = arg_user
            backend = provider_name_to_backend(self.oidc_provider)
            tokens = user.get_oidc_tokens(backend)
            return tokens["id"]
        except Exception as e:
            log.debug("Failed to get auth token: %s", e)
            return None

    def _get_filename(self, obj, sync_cache: bool = True, **kwargs) -> str:
        base_dir = kwargs.get("base_dir", None)
        dir_only = kwargs.get("dir_only", False)
        auth_token = self._get_token(**kwargs)
        rel_path = self._construct_path(obj, **kwargs)

        log.debug("rucio _get_filename: %s", rel_path)

        # for JOB_WORK directory
        if base_dir and dir_only:
            return os.path.abspath(rel_path)

        cache_path = self._get_cache_path(rel_path)
        if not sync_cache:
            return cache_path

        in_cache = self._in_cache(rel_path)
        size_in_cache = 0
        if in_cache:
            size_in_cache = os.path.getsize(self._get_cache_path(rel_path))

        # return path if we do not need to update cache
        if in_cache and dir_only:
            return cache_path
        # something is already in cache
        elif in_cache:
            size_in_rdb = self.rucio_broker.get_size(rel_path)
            # same size as in  rucio, or empty file in rucio - do not pull
            if size_in_cache == size_in_rdb or size_in_rdb == 0:
                return cache_path

        # Check if the file exists in persistent storage and, if it does, pull it into cache
        if self._exists(obj, **kwargs):
            if dir_only:  # Directories do not get pulled into cache
                return cache_path
            else:
                if self._pull_into_cache(rel_path, auth_token=auth_token):
                    return cache_path
        raise ObjectNotFound(f"objectstore.get_filename, no cache_path: {obj}, kwargs: {kwargs}")

    def _register_file(self, rel_path, file_name):
        if file_name is None:
            file_name = self._get_cache_path(rel_path)
            if not os.path.islink(file_name):
                raise ObjectInvalid(
                    "rucio objectstore._register_file, rucio_register_only is set, but file in cache is not a link "
                )
        if os.path.islink(file_name):
            file_name = os.readlink(file_name)
        self.rucio_broker.register(rel_path, file_name)
        log.debug("rucio _register_file: %s", file_name)
        return

    def _update_from_file(
        self, obj, file_name=None, create: bool = False, preserve_symlinks: bool = False, **kwargs
    ) -> None:
        rel_path = self._construct_path(obj, **kwargs)
        log.debug("rucio _update_from_file: %s", rel_path)

        if not create:
            log.warning(
                "rucio objectstore.update_from_file, file update without create, will fail if file already in Rucio"
            )

        if self.rucio_config["register_only"]:
            self._register_file(rel_path, file_name)
            return

        # Choose whether to use the dataset file itself or an alternate file
        if file_name:
            source_file = os.path.abspath(file_name)
            # Copy into cache
            cache_file = self._get_cache_path(rel_path)
            try:
                if source_file != cache_file and self.cache_updated_data:
                    try:
                        shutil.copy2(source_file, cache_file)
                    except OSError:
                        os.makedirs(os.path.dirname(cache_file))
                        shutil.copy2(source_file, cache_file)
                self._fix_file_permissions(cache_file)
                source_file = cache_file
            except OSError:
                log.exception("Trouble copying source file '%s' to cache '%s'", source_file, cache_file)
        else:
            source_file = self._get_cache_path(rel_path)

        # Update the file on rucio
        self.rucio_broker.upload(rel_path, source_file)

    def _get_store_usage_percent(self, **kwargs):
        log.debug("rucio _get_store_usage_percent, not implemented yet")
        return 0.0

    def _get_object_url(self, obj, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        log.debug("rucio _get_object_url")
        return None

    def __build_kwargs(self, obj, **kwargs):
        kwargs["object_id"] = obj.id
        return kwargs

    def shutdown(self):
        self._shutdown_cache_monitor()
