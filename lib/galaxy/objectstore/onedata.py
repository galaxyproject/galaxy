"""
Object Store plugin for the Onedata Service.
"""

import logging
import os
import shutil
from datetime import datetime
from typing import Optional

try:
    from fs.errors import FSError, ResourceNotFound
    from fs.onedatarestfs import OnedataRESTFS
except ImportError:
    OnedataRESTFS = None

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
from galaxy.util.path import safe_relpath
from . import ConcreteObjectStore
from .caching import (
    CacheTarget,
    enable_cache_monitor,
    InProcessCacheMonitor,
    parse_caching_config_dict_from_xml,
)

NO_ONEDATA_ERROR_MESSAGE = (
    "ObjectStore configured to use Onedata, but no OnedataRESTFS dependency "
    "available. Please install and properly configure onedata or modify Object "
    "Store configuration."
)

log = logging.getLogger(__name__)


def _parse_config_xml(config_xml):
    try:
        auth_xml = _get_config_xml_elements(config_xml, "auth")[0]
        access_token = auth_xml.get("access_token")

        conn_xml = _get_config_xml_elements(config_xml, "connection")[0]
        onezone_domain = conn_xml.get("onezone_domain")
        insecure = string_as_bool(conn_xml.get("insecure", "False"))

        space_xml = _get_config_xml_elements(config_xml, "space")[0]
        space_name = space_xml.get("name")

        cache_dict = parse_caching_config_dict_from_xml(config_xml)

        extra_dirs = [{attr: elem.get(attr) for attr in ("type", "path")} 
                      for elem in _get_config_xml_elements(config_xml, "extra_dir")]

        print('\n\n!!22!!\n\n', config_xml, '\n\n\n\n')

        return {
            "auth": {
                "access_token": access_token
            },
            "connection": {
                "onezone_domain": onezone_domain,
                "insecure": insecure,
            },
            "space": {
                "name": space_name
            },
            "cache": cache_dict,
            "extra_dirs": extra_dirs,
            "private": ConcreteObjectStore.parse_private_from_config_xml(config_xml),
        }
    except Exception:
        # Toss it back up after logging, we can't continue loading at this point.
        log.exception("Malformed ObjectStore Configuration XML -- unable to continue")
        raise


def _get_config_xml_elements(config_xml, tag):
    elements = config_xml.findall(tag)

    if not elements:
        msg = f"No {tag} element in config XML tree"
        log.error(msg)
        raise Exception(msg)

    return elements


class OnedataObjectStore(ConcreteObjectStore):
    """
    Object store that stores objects as items in an Onedata. A local
    cache exists that is used as an intermediate location for files between
    Galaxy and Onedata.
    """

    cache_monitor: Optional[InProcessCacheMonitor] = None
    store_type = "onedata"

    def __init__(self, config, config_dict):
        super().__init__(config, config_dict)
        self.cache_monitor = None

        print('\n\n444\n\n', config_dict, '\n\n444\n\n')

        auth_dict = config_dict["auth"]
        self.access_token = auth_dict["access_token"]

        connection_dict = config_dict["connection"]
        self.onezone_domain = connection_dict["onezone_domain"]
        self.insecure = connection_dict.get("insecure", False)

        space_dict = config_dict["space"]
        self.space_name = space_dict["name"] 
        # self.space_name = "demo-space"

        cache_dict = config_dict.get("cache") or {}
        self.enable_cache_monitor, self.cache_monitor_interval = enable_cache_monitor(config, config_dict)
        self.cache_size = cache_dict["size"] or self.config.object_store_cache_size
        self.staging_path = cache_dict["path"] or self.config.object_store_cache_path
        self.cache_updated_data = cache_dict.get("cache_updated_data", True)

        extra_dirs = {e["type"]: e["path"] for e in config_dict.get("extra_dirs", [])}
        self.extra_dirs.update(extra_dirs)

        self._initialize()

    def _initialize(self):
        if OnedataRESTFS is None:
            raise Exception(NO_ONEDATA_ERROR_MESSAGE)

        log.debug("Configuring Onedata Connection")
        self.fs_handle = OnedataRESTFS(self.onezone_domain, 
                                       self.access_token,
                                       self.space_name,
                                       insecure=self.insecure)

        if self.enable_cache_monitor:
            self.cache_monitor = InProcessCacheMonitor(self.cache_target, 
                                                       self.cache_monitor_interval)

    @classmethod
    def parse_xml(clazz, config_xml):
        return _parse_config_xml(config_xml)

    def to_dict(self):
        as_dict = super().to_dict()
        as_dict.update({
            "auth": {
                "access_token": self.access_token,
            },
            "connection": {
                "onezone_domain": self.onezone_domain,
                "insecure": self.insecure,
            },
            "space": {
                "name": self.space_name
            },
            "cache": {
                "size": self.cache_size,
                "path": self.staging_path,
                "cache_updated_data": self.cache_updated_data,
            },
        })
        return as_dict

    @property
    def cache_target(self) -> CacheTarget:
        return CacheTarget(self.staging_path, self.cache_size, 0.9)

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

    def _construct_path(
        self,
        obj,
        base_dir=None,
        dir_only=None,
        extra_dir=None,
        extra_dir_at_root=False,
        alt_name=None,
        obj_dir=False,
        in_cache=False,
        **kwargs,
    ):
        # extra_dir should never be constructed from provided data but just
        # make sure there are no shenanigans afoot
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
            return os.path.join(str(base), rel_path)

        if not dir_only:
            rel_path = os.path.join(rel_path, alt_name if alt_name else f"dataset_{self._get_object_id(obj)}.dat")
        if in_cache:
            return self._get_cache_path(rel_path)

        return rel_path

    def _get_size_in_onedata(self, rel_path):
        try:
            info = self.fs_handle.getinfo(rel_path)
            return info.size
        except ResourceNotFound:
            log.exception("Could not get '%s' size from Onedata", rel_path)
            return -1

    def _exists_in_onedata(self, rel_path):
        # log.debug("\n\n\n\nPAAAATH %s\n\n\n\n", rel_path)  # XD?
        try:
            return self.fs_handle.exists(rel_path)
        except ResourceNotFound:
            log.exception("Trouble checking '%s' existence in Onedata", rel_path)
            return False

    def _in_cache(self, rel_path):
        """Check if the given dataset is in the local cache and return True if so."""
        cache_path = self._get_cache_path(rel_path)
        return os.path.exists(cache_path)

    def _get_cache_path(self, rel_path):
        return os.path.abspath(os.path.join(self.staging_path, rel_path))

    def _get_size_in_cache(self, rel_path):
        return os.path.getsize(self._get_cache_path(rel_path))

    def _pull_into_cache(self, rel_path):
        # Ensure the cache directory structure exists (e.g., dataset_#_files/)
        rel_path_dir = os.path.dirname(rel_path)
        if not os.path.exists(self._get_cache_path(rel_path_dir)):
            os.makedirs(self._get_cache_path(rel_path_dir), exist_ok=True)
        # Now pull in the file
        file_ok = self._download(rel_path)
        self._fix_permissions(self._get_cache_path(rel_path_dir))
        return file_ok

    def _download(self, rel_path):
        try:
            dst_path = self._get_cache_path(rel_path)
    
            log.debug("Pulling file '%s' into cache to %s", rel_path, dst_path)

            file_info = self.fs_handle.getinfo(rel_path)

            # Test if cache is large enough to hold the new file
            if not self.cache_target.fits_in_cache(file_info.size):
                log.critical(
                    "File %s is larger (%s) than the configured cache allows (%s). Cannot download.",
                    rel_path,
                    file_info.size,
                    self.cache_target.log_description,
                )
                return False

            with self.fs_handle.openbin(rel_path) as src, open(dst_path, 'wb') as dst:
                shutil.copyfileobj(src, dst)

            log.debug("Pulled '%s' into cache to %s", rel_path, dst_path)

            return True
        except FSError:
            log.exception("Problem downloading file '%s'", rel_path)
        return False

    def _push_to_os(self, rel_path, source_file=None):
        """
        Push the file pointed to by ``rel_path`` to the object store under ``rel_path``. 
        If ``source_file`` is provided, push that file instead while still using 
        ``rel_path`` as the path.
        """
        try:
            source_file = source_file if source_file else self._get_cache_path(rel_path)
            if os.path.exists(source_file):
                if os.path.getsize(source_file) == 0 and self._exists_in_onedata(rel_path):
                    log.debug(
                        "Wanted to push file '%s' to Onedata '%s' but its size is 0; skipping.", 
                        source_file, 
                        rel_path
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

                    with open(source_file, 'rb') as src, self.fs_handle.openbin(rel_path, 'w') as dst:
                        shutil.copyfileobj(src, dst)

                    end_time = datetime.now()
                    log.debug(
                        "Pushed cache file '%s' under '%s' (%s bytes transfered in %s sec)",
                        source_file,
                        rel_path,
                        os.path.getsize(source_file),
                        end_time - start_time,
                    )
                return True
            else:
                log.error("Source file does not exist.", rel_path, source_file)
        except FSError:
            log.exception("Trouble pushing Onedata key '%s' from file '%s'", rel_path, source_file)
            raise
        return False

    def file_ready(self, obj, **kwargs):
        """
        A helper method that checks if a file corresponding to a dataset is
        ready and available to be used. Return ``True`` if so, ``False`` otherwise.
        """
        rel_path = self._construct_path(obj, **kwargs)
        # Make sure the size in cache is available in its entirety
        if self._in_cache(rel_path):
            if self._get_size_in_cache(rel_path) == self._get_size_in_onedata(rel_path):
                return True
        log.debug(
            "Waiting for dataset %s to transfer from OS: %s/%s",
            rel_path,
            self._get_size_in_cache(rel_path),
            self._get_size_in_onedata(rel_path),
        )
        return False

    def _exists(self, obj, **kwargs):
        rel_path = self._construct_path(obj, **kwargs)
        in_cache = self._in_cache(rel_path)
        in_onedata = self._exists_in_onedata(rel_path)

        # dir_only does not get synced so shortcut the decision
        dir_only = kwargs.get("dir_only", False)
        base_dir = kwargs.get("base_dir", None)
        if dir_only:
            if in_cache or in_onedata:
                return True
            # for JOB_WORK directory
            elif base_dir:
                if not os.path.exists(rel_path):
                    os.makedirs(rel_path, exist_ok=True)
                return True
            else:
                return False

        if in_cache and not in_onedata:
            self._push_to_os(rel_path)
            return True
        elif in_onedata:
            return True
        else:
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

            if not dir_only:
                rel_path = os.path.join(rel_path, alt_name if alt_name else f"dataset_{self._get_object_id(obj)}.dat")
                # need this line to set the dataset filename, not sure how this is done - filesystem is monitored?
                open(os.path.join(self.staging_path, rel_path), "w").close()
                self.fs_handle.create(rel_path)
        return self

    def _empty(self, obj, **kwargs):
        if self._exists(obj, **kwargs):
            return bool(self._size(obj, **kwargs) > 0)
        else:
            raise ObjectNotFound(f"objectstore.empty, object does not exist: {obj}, kwargs: {kwargs}")

    def _size(self, obj, **kwargs):
        rel_path = self._construct_path(obj, **kwargs)
        if self._in_cache(rel_path):
            try:
                return self._get_size_in_cache(rel_path)
            except OSError as ex:
                log.info("Could not get size of file '%s' in local cache, will try Onedata. Error: %s", rel_path, ex)
        elif self._exists(obj, **kwargs):
            return self._get_size_in_onedata(rel_path)
        log.warning("Did not find dataset '%s', returning 0 for size", rel_path)
        return 0

    def _delete(self, obj, entire_dir=False, **kwargs):
        rel_path = self._construct_path(obj, **kwargs)
        extra_dir = kwargs.get("extra_dir", None)
        base_dir = kwargs.get("base_dir", None)
        dir_only = kwargs.get("dir_only", False)
        obj_dir = kwargs.get("obj_dir", False)

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

            # Delete from Onedata as well
            if self._exists_in_onedata(rel_path):
                self.fs_handle.remove(rel_path)
                return True
        except FSError:
            log.exception("Could not delete '%s' from Onedata", rel_path)
        except OSError:
            log.exception("%s delete error", self._get_filename(obj, **kwargs))
        return False

    def _get_data(self, obj, start=0, count=-1, **kwargs):
        rel_path = self._construct_path(obj, **kwargs)
        # Check cache first and get file if not there
        if not self._in_cache(rel_path) or self._get_size_in_cache(rel_path) == 0:
            self._pull_into_cache(rel_path)
        # Read the file content from cache
        # TODO with open?
        data_file = open(self._get_cache_path(rel_path))
        data_file.seek(start)
        content = data_file.read(count)
        data_file.close()
        return content

    def _get_filename(self, obj, **kwargs):
        base_dir = kwargs.get("base_dir", None)
        dir_only = kwargs.get("dir_only", False)
        obj_dir = kwargs.get("obj_dir", False)
        sync_cache = kwargs.get("sync_cache", True)

        rel_path = self._construct_path(obj, **kwargs)

        # for JOB_WORK directory
        if base_dir and dir_only and obj_dir:
            return os.path.abspath(rel_path)

        cache_path = self._get_cache_path(rel_path)
        if not sync_cache:
            return cache_path

        # return path if we do not need to update cache
        if self._in_cache(rel_path) and (dir_only or self._get_size_in_cache(rel_path) > 0):
            return cache_path
        # something is already in cache
        elif self._exists(obj, **kwargs):
            if dir_only:  # Directories do not get pulled into cache
                return cache_path
            else:
                if self._pull_into_cache(rel_path):
                    return cache_path

        raise ObjectNotFound(f"objectstore.get_filename, no cache_path: {obj}, kwargs: {kwargs}")

    def _update_from_file(self, obj, file_name=None, create=False, **kwargs):
        if create:
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
                        try:
                            shutil.copy2(source_file, cache_file)
                        except OSError:
                            os.makedirs(os.path.dirname(cache_file))
                            shutil.copy2(source_file, cache_file)
                    self._fix_permissions(cache_file)
                except OSError:
                    log.exception("Trouble copying source file '%s' to cache '%s'", source_file, cache_file)
            else:
                source_file = self._get_cache_path(rel_path)
            # Update the file on Onedata
            self._push_to_os(rel_path, source_file)
        else:
            raise ObjectNotFound(f"objectstore.update_from_file, object does not exist: {obj}, kwargs: {kwargs}")

    def _get_object_url(self, obj, **kwargs):
        return None

    def _get_store_usage_percent(self, **kwargs):
        return 0.0

    def shutdown(self):
        self.cache_monitor and self.cache_monitor.shutdown()
