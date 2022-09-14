"""
Object Store plugin for the Integrated Rule-Oriented Data System (iRODS)
"""
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

try:
    import irods
    import irods.keywords as kw
    from irods.exception import (
        CollectionDoesNotExist,
        DataObjectDoesNotExist,
    )
    from irods.session import iRODSSession
except ImportError:
    irods = None

from galaxy.exceptions import (
    ObjectInvalid,
    ObjectNotFound,
)
from galaxy.util import (
    directory_hash_id,
    ExecutionTimer,
    umask_fix_perms,
    unlink,
)
from galaxy.util.path import safe_relpath
from ..objectstore import DiskObjectStore

IRODS_IMPORT_MESSAGE = "The Python irods package is required to use this feature, please install it"
# 1 MB
CHUNK_SIZE = 2**20
log = logging.getLogger(__name__)
logging.getLogger("irods.connection").setLevel(logging.INFO)  # irods logging generates gigabytes of logs


def _config_xml_error(tag):
    msg = f"No {tag} element in config XML tree"
    raise Exception(msg)


def _config_dict_error(key):
    msg = "No {key} key in config dictionary".forma(key=key)
    raise Exception(msg)


def parse_config_xml(config_xml):
    try:
        a_xml = config_xml.findall("auth")
        if not a_xml:
            _config_xml_error("auth")
        username = a_xml[0].get("username")
        password = a_xml[0].get("password")

        r_xml = config_xml.findall("resource")
        if not r_xml:
            _config_xml_error("resource")
        resource_name = r_xml[0].get("name")

        z_xml = config_xml.findall("zone")
        if not z_xml:
            _config_xml_error("zone")
        zone_name = z_xml[0].get("name")

        c_xml = config_xml.findall("connection")
        if not c_xml:
            _config_xml_error("connection")
        host = c_xml[0].get("host", None)
        port = int(c_xml[0].get("port", 0))
        timeout = int(c_xml[0].get("timeout", 30))
        refresh_time = int(c_xml[0].get("refresh_time", 300))

        c_xml = config_xml.findall("cache")
        if not c_xml:
            _config_xml_error("cache")
        cache_size = float(c_xml[0].get("size", -1))
        staging_path = c_xml[0].get("path", None)

        attrs = ("type", "path")
        e_xml = config_xml.findall("extra_dir")
        if not e_xml:
            _config_xml_error("extra_dir")
        extra_dirs = [{k: e.get(k) for k in attrs} for e in e_xml]

        return {
            "auth": {
                "username": username,
                "password": password,
            },
            "resource": {
                "name": resource_name,
            },
            "zone": {
                "name": zone_name,
            },
            "connection": {
                "host": host,
                "port": port,
                "timeout": timeout,
                "refresh_time": refresh_time,
            },
            "cache": {
                "size": cache_size,
                "path": staging_path,
            },
            "extra_dirs": extra_dirs,
        }
    except Exception:
        # Toss it back up after logging, we can't continue loading at this point.
        log.exception("Malformed iRODS ObjectStore Configuration XML -- unable to continue.")
        raise


class CloudConfigMixin:
    def _config_to_dict(self):
        return {
            "auth": {
                "username": self.username,
                "password": self.password,
            },
            "resource": {
                "name": self.resource,
            },
            "zone": {
                "name": self.zone,
            },
            "connection": {
                "host": self.host,
                "port": self.port,
                "timeout": self.timeout,
                "refresh_time": self.refresh_time,
            },
            "cache": {
                "size": self.cache_size,
                "path": self.staging_path,
            },
        }


class IRODSObjectStore(DiskObjectStore, CloudConfigMixin):
    """
    Object store that stores files as data objects in an iRODS Zone. A local cache
    exists that is used as an intermediate location for files between Galaxy and iRODS.
    """

    store_type = "irods"

    def __init__(self, config, config_dict):
        ipt_timer = ExecutionTimer()
        super().__init__(config, config_dict)

        auth_dict = config_dict.get("auth")
        if auth_dict is None:
            _config_dict_error("auth")

        self.username = auth_dict.get("username")
        if self.username is None:
            _config_dict_error("auth->username")
        self.password = auth_dict.get("password")
        if self.password is None:
            _config_dict_error("auth->password")

        resource_dict = config_dict["resource"]
        if resource_dict is None:
            _config_dict_error("resource")
        self.resource = resource_dict.get("name")
        if self.resource is None:
            _config_dict_error("resource->name")

        zone_dict = config_dict["zone"]
        if zone_dict is None:
            _config_dict_error("zone")
        self.zone = zone_dict.get("name")
        if self.zone is None:
            _config_dict_error("zone->name")

        connection_dict = config_dict["connection"]
        if connection_dict is None:
            _config_dict_error("connection")
        self.host = connection_dict.get("host")
        if self.host is None:
            _config_dict_error("connection->host")
        self.port = connection_dict.get("port")
        if self.port is None:
            _config_dict_error("connection->port")
        self.timeout = connection_dict.get("timeout")
        if self.timeout is None:
            _config_dict_error("connection->timeout")
        self.refresh_time = connection_dict.get("refresh_time")
        if self.refresh_time is None:
            _config_dict_error("connection->refresh_time")

        cache_dict = config_dict["cache"]
        if cache_dict is None:
            _config_dict_error("cache")
        self.cache_size = cache_dict.get("size", -1)
        if self.cache_size is None:
            _config_dict_error("cache->size")
        self.staging_path = cache_dict.get("path") or self.config.object_store_cache_path
        if self.staging_path is None:
            _config_dict_error("cache->path")

        extra_dirs = {e["type"]: e["path"] for e in config_dict.get("extra_dirs", [])}
        if not extra_dirs:
            _config_dict_error("extra_dirs")
        self.extra_dirs.update(extra_dirs)

        if irods is None:
            raise Exception(IRODS_IMPORT_MESSAGE)

        self.home = f"/{self.zone}/home/{self.username}"

        if irods is None:
            raise Exception(IRODS_IMPORT_MESSAGE)

        self.session = iRODSSession(
            host=self.host,
            port=self.port,
            user=self.username,
            password=self.password,
            zone=self.zone,
            refresh_time=self.refresh_time,
        )
        # Set connection timeout
        self.session.connection_timeout = self.timeout
        log.debug("irods_pt __init__: %s", ipt_timer)

    def shutdown(self):
        # This call will cleanup all the connections in the connection pool
        # OSError sometimes happens on GitHub Actions, after the test has successfully completed. Ignore it if it happens.
        ipt_timer = ExecutionTimer()
        try:
            self.session.cleanup()
        except OSError:
            pass
        log.debug("irods_pt shutdown: %s", ipt_timer)

    @classmethod
    def parse_xml(cls, config_xml):
        return parse_config_xml(config_xml)

    def to_dict(self):
        as_dict = super().to_dict()
        as_dict.update(self._config_to_dict())
        return as_dict

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
        **kwargs,
    ):
        ipt_timer = ExecutionTimer()
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
            log.debug("irods_pt _construct_path: %s", ipt_timer)
            return os.path.join(base, rel_path)

        if not dir_only:
            rel_path = os.path.join(rel_path, alt_name if alt_name else f"dataset_{self._get_object_id(obj)}.dat")
        log.debug("irods_pt _construct_path: %s", ipt_timer)
        return rel_path

    def _get_cache_path(self, rel_path):
        return os.path.abspath(os.path.join(self.staging_path, rel_path))

    # rel_path is file or folder?
    def _get_size_in_irods(self, rel_path):
        ipt_timer = ExecutionTimer()
        p = Path(rel_path)
        data_object_name = p.stem + p.suffix
        subcollection_name = p.parent

        collection_path = f"{self.home}/{subcollection_name}"
        data_object_path = f"{collection_path}/{data_object_name}"
        options = {kw.DEST_RESC_NAME_KW: self.resource}

        try:
            data_obj = self.session.data_objects.get(data_object_path, **options)
            return data_obj.__sizeof__()
        except (DataObjectDoesNotExist, CollectionDoesNotExist):
            log.warning("Collection or data object (%s) does not exist", data_object_path)
            return -1
        finally:
            log.debug("irods_pt _get_size_in_irods: %s", ipt_timer)

    # rel_path is file or folder?
    def _data_object_exists(self, rel_path):
        ipt_timer = ExecutionTimer()
        p = Path(rel_path)
        data_object_name = p.stem + p.suffix
        subcollection_name = p.parent

        collection_path = f"{self.home}/{subcollection_name}"
        data_object_path = f"{collection_path}/{data_object_name}"
        options = {kw.DEST_RESC_NAME_KW: self.resource}

        try:
            self.session.data_objects.get(data_object_path, **options)
            return True
        except (DataObjectDoesNotExist, CollectionDoesNotExist):
            log.debug("Collection or data object (%s) does not exist", data_object_path)
            return False
        finally:
            log.debug("irods_pt _data_object_exists: %s", ipt_timer)

    def _in_cache(self, rel_path):
        """Check if the given dataset is in the local cache and return True if so."""
        cache_path = self._get_cache_path(rel_path)
        return os.path.exists(cache_path)

    def _pull_into_cache(self, rel_path):
        ipt_timer = ExecutionTimer()
        # Ensure the cache directory structure exists (e.g., dataset_#_files/)
        rel_path_dir = os.path.dirname(rel_path)
        if not os.path.exists(self._get_cache_path(rel_path_dir)):
            os.makedirs(self._get_cache_path(rel_path_dir), exist_ok=True)
        # Now pull in the file
        file_ok = self._download(rel_path)
        self._fix_permissions(self._get_cache_path(rel_path_dir))
        log.debug("irods_pt _pull_into_cache: %s", ipt_timer)
        return file_ok

    def _download(self, rel_path):
        ipt_timer = ExecutionTimer()
        log.debug("Pulling data object '%s' into cache to %s", rel_path, self._get_cache_path(rel_path))

        p = Path(rel_path)
        data_object_name = p.stem + p.suffix
        subcollection_name = p.parent

        collection_path = f"{self.home}/{subcollection_name}"
        data_object_path = f"{collection_path}/{data_object_name}"
        options = {kw.DEST_RESC_NAME_KW: self.resource}

        try:
            cache_path = self._get_cache_path(rel_path)
            self.session.data_objects.get(data_object_path, cache_path, **options)
            log.debug("Pulled data object '%s' into cache to %s", rel_path, cache_path)
            return True
        except (DataObjectDoesNotExist, CollectionDoesNotExist):
            log.warning("Collection or data object (%s) does not exist", data_object_path)
            return False
        finally:
            log.debug("irods_pt _download: %s", ipt_timer)

    def _push_to_irods(self, rel_path, source_file=None, from_string=None):
        """
        Push the file pointed to by ``rel_path`` to the iRODS. Extract folder name
        from rel_path as iRODS collection name, and extract file name from rel_path
        as iRODS data object name.
        If ``source_file`` is provided, push that file instead while
        still using ``rel_path`` for collection and object store names.
        If ``from_string`` is provided, set contents of the file to the value of the string.
        """
        ipt_timer = ExecutionTimer()
        p = Path(rel_path)
        data_object_name = p.stem + p.suffix
        subcollection_name = p.parent

        source_file = source_file if source_file else self._get_cache_path(rel_path)
        options = {kw.FORCE_FLAG_KW: "", kw.DEST_RESC_NAME_KW: self.resource}

        if not os.path.exists(source_file):
            log.error(
                "Tried updating key '%s' from source file '%s', but source file does not exist.", rel_path, source_file
            )
            return False

        # Check if the data object exists in iRODS
        collection_path = f"{self.home}/{subcollection_name}"
        data_object_path = f"{collection_path}/{data_object_name}"
        exists = False

        try:
            exists = self.session.data_objects.exists(data_object_path)

            if os.path.getsize(source_file) == 0 and exists:
                log.debug(
                    "Wanted to push file '%s' to iRODS collection '%s' but its size is 0; skipping.",
                    source_file,
                    rel_path,
                )
                return True

            # Create sub-collection first
            self.session.collections.create(collection_path, recurse=True, **options)

            if from_string:
                # Create data object
                data_obj = self.session.data_objects.create(data_object_path, self.resource, **options)

                # Save 'from_string' as a file
                with data_obj.open("w") as data_obj_fp:
                    data_obj_fp.write(from_string)

                # Add file containing 'from_string' to the irods collection, since
                # put() expects a file as input. Get file name from data object's 'desc' field
                self.session.data_objects.put(data_obj.desc, f"{collection_path}/", **options)

                log.debug("Pushed data from string '%s' to collection '%s'", from_string, data_object_path)
            else:
                start_time = datetime.now()
                log.debug(
                    "Pushing cache file '%s' of size %s bytes to collection '%s'",
                    source_file,
                    os.path.getsize(source_file),
                    rel_path,
                )

                # Add the source file to the irods collection
                self.session.data_objects.put(source_file, data_object_path, **options)

                end_time = datetime.now()
                log.debug(
                    "Pushed cache file '%s' to collection '%s' (%s bytes transfered in %s sec)",
                    source_file,
                    rel_path,
                    os.path.getsize(source_file),
                    (end_time - start_time).total_seconds(),
                )
            return True
        finally:
            log.debug("irods_pt _push_to_irods: %s", ipt_timer)

    def file_ready(self, obj, **kwargs):
        """
        A helper method that checks if a file corresponding to a dataset is
        ready and available to be used. Return ``True`` if so, ``False`` otherwise.
        """
        ipt_timer = ExecutionTimer()
        rel_path = self._construct_path(obj, **kwargs)
        # Make sure the size in cache is available in its entirety
        if self._in_cache(rel_path):
            if os.path.getsize(self._get_cache_path(rel_path)) == self._get_size_in_irods(rel_path):
                log.debug("irods_pt _file_ready: %s", ipt_timer)
                return True
            log.debug(
                "Waiting for dataset %s to transfer from OS: %s/%s",
                rel_path,
                os.path.getsize(self._get_cache_path(rel_path)),
                self._get_size_in_irods(rel_path),
            )
        log.debug("irods_pt _file_ready: %s", ipt_timer)
        return False

    def _exists(self, obj, **kwargs):
        ipt_timer = ExecutionTimer()
        rel_path = self._construct_path(obj, **kwargs)

        # Check cache and irods
        if self._in_cache(rel_path) or self._data_object_exists(rel_path):
            log.debug("irods_pt _exists: %s", ipt_timer)
            return True

        # dir_only does not get synced so shortcut the decision
        dir_only = kwargs.get("dir_only", False)
        base_dir = kwargs.get("base_dir", None)
        if dir_only and base_dir:
            # for JOB_WORK directory
            if not os.path.exists(rel_path):
                os.makedirs(rel_path, exist_ok=True)
            log.debug("irods_pt _exists: %s", ipt_timer)
            return True
        log.debug("irods_pt _exists: %s", ipt_timer)
        return False

    def _create(self, obj, **kwargs):
        ipt_timer = ExecutionTimer()
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
                open(os.path.join(self.staging_path, rel_path), "w").close()
                self._push_to_irods(rel_path, from_string="")
        log.debug("irods_pt _create: %s", ipt_timer)

    def _empty(self, obj, **kwargs):
        if self._exists(obj, **kwargs):
            return bool(self._size(obj, **kwargs) > 0)
        else:
            raise ObjectNotFound(f"objectstore.empty, object does not exist: {obj}, kwargs: {kwargs}")

    def _size(self, obj, **kwargs):
        ipt_timer = ExecutionTimer()
        rel_path = self._construct_path(obj, **kwargs)
        if self._in_cache(rel_path):
            try:
                return os.path.getsize(self._get_cache_path(rel_path))
            except OSError as ex:
                log.info("Could not get size of file '%s' in local cache, will try iRODS. Error: %s", rel_path, ex)
            finally:
                log.debug("irods_pt _size: %s", ipt_timer)
        elif self._exists(obj, **kwargs):
            log.debug("irods_pt _size: %s", ipt_timer)
            return self._get_size_in_irods(rel_path)
        log.warning("Did not find dataset '%s', returning 0 for size", rel_path)
        log.debug("irods_pt _size: %s", ipt_timer)
        return 0

    def _delete(self, obj, entire_dir=False, **kwargs):
        ipt_timer = ExecutionTimer()
        rel_path = self._construct_path(obj, **kwargs)
        extra_dir = kwargs.get("extra_dir", None)
        base_dir = kwargs.get("base_dir", None)
        dir_only = kwargs.get("dir_only", False)
        obj_dir = kwargs.get("obj_dir", False)

        options = {kw.DEST_RESC_NAME_KW: self.resource}

        try:
            # Remove temparory data in JOB_WORK directory
            if base_dir and dir_only and obj_dir:
                shutil.rmtree(os.path.abspath(rel_path))
                return True

            # For the case of extra_files, because we don't have a reference to
            # individual files we need to remove the entire directory structure
            # with all the files in it. This is easy for the local file system,
            # but requires iterating through each individual key in irods and deleing it.
            if entire_dir and extra_dir:
                shutil.rmtree(self._get_cache_path(rel_path), ignore_errors=True)

                col_path = f"{self.home}/{rel_path}"
                col = None
                try:
                    col = self.session.collections.get(col_path)
                except CollectionDoesNotExist:
                    log.warning("Collection (%s) does not exist!", col_path)
                    return False

                cols = col.walk()
                # Traverse the tree only one level deep
                for _ in range(2):
                    # get next result
                    _, _, data_objects = next(cols)

                    # Delete data objects
                    for data_object in data_objects:
                        data_object.unlink(force=True)

                return True

            else:
                # Delete from cache first
                unlink(self._get_cache_path(rel_path), ignore_errors=True)
                # Delete from irods as well
                p = Path(rel_path)
                data_object_name = p.stem + p.suffix
                subcollection_name = p.parent

                collection_path = f"{self.home}/{subcollection_name}"
                data_object_path = f"{collection_path}/{data_object_name}"

                try:
                    data_obj = self.session.data_objects.get(data_object_path, **options)
                    # remove object
                    data_obj.unlink(force=True)
                    return True
                except (DataObjectDoesNotExist, CollectionDoesNotExist):
                    log.info("Collection or data object (%s) does not exist", data_object_path)
                    return True
        except OSError:
            log.exception("%s delete error", self._get_filename(obj, **kwargs))
        finally:
            log.debug("irods_pt _delete: %s", ipt_timer)
        return False

    def _get_data(self, obj, start=0, count=-1, **kwargs):
        ipt_timer = ExecutionTimer()
        rel_path = self._construct_path(obj, **kwargs)
        # Check cache first and get file if not there
        if not self._in_cache(rel_path):
            self._pull_into_cache(rel_path)
        # Read the file content from cache
        data_file = open(self._get_cache_path(rel_path))
        data_file.seek(start)
        content = data_file.read(count)
        data_file.close()
        log.debug("irods_pt _get_data: %s", ipt_timer)
        return content

    def _get_filename(self, obj, **kwargs):
        ipt_timer = ExecutionTimer()
        base_dir = kwargs.get("base_dir", None)
        dir_only = kwargs.get("dir_only", False)
        obj_dir = kwargs.get("obj_dir", False)
        rel_path = self._construct_path(obj, **kwargs)

        # for JOB_WORK directory
        if base_dir and dir_only and obj_dir:
            log.debug("irods_pt _get_filename: %s", ipt_timer)
            return os.path.abspath(rel_path)

        cache_path = self._get_cache_path(rel_path)
        # iRODS does not recognize directories as files so cannot check if those exist.
        # So, if checking dir only, ensure given dir exists in cache and return
        # the expected cache path.
        # dir_only = kwargs.get('dir_only', False)
        # if dir_only:
        #     if not os.path.exists(cache_path):
        #         os.makedirs(cache_path)
        #     return cache_path
        # Check if the file exists in the cache first
        if self._in_cache(rel_path):
            log.debug("irods_pt _get_filename: %s", ipt_timer)
            return cache_path
        # Check if the file exists in persistent storage and, if it does, pull it into cache
        elif self._exists(obj, **kwargs):
            if dir_only:  # Directories do not get pulled into cache
                log.debug("irods_pt _get_filename: %s", ipt_timer)
                return cache_path
            else:
                if self._pull_into_cache(rel_path):
                    log.debug("irods_pt _get_filename: %s", ipt_timer)
                    return cache_path
        # For the case of retrieving a directory only, return the expected path
        # even if it does not exist.
        # if dir_only:
        #     return cache_path
        log.debug("irods_pt _get_filename: %s", ipt_timer)
        raise ObjectNotFound(f"objectstore.get_filename, no cache_path: {obj}, kwargs: {kwargs}")
        # return cache_path # Until the upload tool does not explicitly create the dataset, return expected path

    def _update_from_file(self, obj, file_name=None, create=False, **kwargs):
        ipt_timer = ExecutionTimer()
        if create:
            self._create(obj, **kwargs)
        if self._exists(obj, **kwargs):
            rel_path = self._construct_path(obj, **kwargs)
            # Choose whether to use the dataset file itself or an alternate file
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
            # Update the file on iRODS
            self._push_to_irods(rel_path, source_file)
        else:
            log.debug("irods_pt _update_from_file: %s", ipt_timer)
            raise ObjectNotFound(f"objectstore.update_from_file, object does not exist: {obj}, kwargs: {kwargs}")
        log.debug("irods_pt _update_from_file: %s", ipt_timer)

    # Unlike S3, url is not really applicable to iRODS
    def _get_object_url(self, obj, **kwargs):
        if self._exists(obj, **kwargs):
            rel_path = self._construct_path(obj, **kwargs)

            p = Path(rel_path)
            data_object_name = p.stem + p.suffix
            subcollection_name = p.parent

            collection_path = f"{self.home}/{subcollection_name}"
            data_object_path = f"{collection_path}/{data_object_name}"

            return data_object_path

    def _get_store_usage_percent(self):
        return 0.0
