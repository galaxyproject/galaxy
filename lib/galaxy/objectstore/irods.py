"""
Object Store plugin for the Integrated Rule-Oriented Data System (iRODS)
"""

import logging
import os
import shutil
import threading
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

from galaxy.util import (
    ExecutionTimer,
    string_as_bool,
    unlink,
)
from ._caching_base import CachingConcreteObjectStore

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
        envfile = a_xml[0].get("envfile", None)

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
        connection_pool_monitor_interval = int(c_xml[0].get("connection_pool_monitor_interval", -1))

        c_xml = config_xml.findall("cache")
        if not c_xml:
            _config_xml_error("cache")
        cache_size = float(c_xml[0].get("size", -1))
        staging_path = c_xml[0].get("path", None)
        cache_updated_data = string_as_bool(c_xml[0].get("cache_updated_data", "True"))

        attrs = ("type", "path")
        e_xml = config_xml.findall("extra_dir")
        if not e_xml:
            _config_xml_error("extra_dir")
        extra_dirs = [{k: e.get(k) for k in attrs} for e in e_xml]

        return {
            "auth": {
                "username": username,
                "password": password,
                "envfile": envfile,
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
                "connection_pool_monitor_interval": connection_pool_monitor_interval,
            },
            "cache": {
                "size": cache_size,
                "path": staging_path,
                "cache_updated_data": cache_updated_data,
            },
            "extra_dirs": extra_dirs,
            "private": CachingConcreteObjectStore.parse_private_from_config_xml(config_xml),
        }
    except Exception:
        # Toss it back up after logging, we can't continue loading at this point.
        log.exception("Malformed iRODS ObjectStore Configuration XML -- unable to continue.")
        raise


class IRODSObjectStore(CachingConcreteObjectStore):
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
        self.envfile = auth_dict.get("envfile")
        # if self.envfile is None:
        #     _config_dict_error("auth->envfile")

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
        self.connection_pool_monitor_interval = connection_dict.get("connection_pool_monitor_interval")
        if self.connection_pool_monitor_interval is None:
            _config_dict_error("connection->connection_pool_monitor_interval")

        cache_dict = config_dict.get("cache") or {}
        self.cache_size = cache_dict.get("size") or self.config.object_store_cache_path
        if self.cache_size is None:
            _config_dict_error("cache->size")
        self.staging_path = cache_dict.get("path") or self.config.object_store_cache_path
        if self.staging_path is None:
            _config_dict_error("cache->path")
        self.cache_updated_data = cache_dict.get("cache_updated_data", True)

        extra_dirs = {e["type"]: e["path"] for e in config_dict.get("extra_dirs", [])}
        if not extra_dirs:
            _config_dict_error("extra_dirs")
        self.extra_dirs.update(extra_dirs)

        if irods is None:
            raise Exception(IRODS_IMPORT_MESSAGE)

        self.home = f"/{self.zone}/home/{self.username}"

        if irods is None:
            raise Exception(IRODS_IMPORT_MESSAGE)
        

        session_params = {
            'host': self.host,
            'port': self.port,
            'user': self.username,
            'password': self.password,
            'zone': self.zone,
            'refresh_time': self.refresh_time,
        }

        # Add the irods_env_file parameter only if self.envfile is not None
        if self.envfile is not None:
            session_params['irods_env_file'] = self.envfile

        self.session = iRODSSession(**session_params)

        # Set connection timeout
        self.session.connection_timeout = self.timeout

        if self.connection_pool_monitor_interval != -1:
            # This Event object is initialized to False
            # It is set to True in shutdown(), causing
            # the connection pool monitor thread to return/terminate
            self.stop_connection_pool_monitor_event = threading.Event()
            self.connection_pool_monitor_thread = None

        log.debug("irods_pt __init__: %s", ipt_timer)

    def shutdown(self):
        # This call will cleanup all the connections in the connection pool
        # OSError sometimes happens on GitHub Actions, after the test has successfully completed. Ignore it if it happens.
        ipt_timer = ExecutionTimer()
        try:
            self.session.cleanup()
        except OSError:
            pass

        if self.connection_pool_monitor_interval != -1:
            # Set to True so the connection pool monitor thread will return/terminate
            self.stop_connection_pool_monitor_event.set()
            if self.connection_pool_monitor_thread is not None:
                self.connection_pool_monitor_thread.join(5)

        log.debug("irods_pt shutdown: %s", ipt_timer)

    @classmethod
    def parse_xml(cls, config_xml):
        return parse_config_xml(config_xml)

    def start_connection_pool_monitor(self):
        self.connection_pool_monitor_thread = threading.Thread(
            target=self._connection_pool_monitor,
            args=(),
            kwargs={
                "refresh_time": self.refresh_time,
                "connection_pool_monitor_interval": self.connection_pool_monitor_interval,
                "stop_connection_pool_monitor_event": self.stop_connection_pool_monitor_event,
            },
            name="ConnectionPoolMonitorThread",
            daemon=True,
        )
        self.connection_pool_monitor_thread.start()
        log.info("Connection pool monitor started")

    def start(self):
        if self.connection_pool_monitor_interval != -1:
            self.start_connection_pool_monitor()

    def _connection_pool_monitor(self, *args, **kwargs):
        refresh_time = kwargs["refresh_time"]
        connection_pool_monitor_interval = kwargs["connection_pool_monitor_interval"]
        stop_connection_pool_monitor_event = kwargs["stop_connection_pool_monitor_event"]

        while not stop_connection_pool_monitor_event.is_set():
            curr_time = datetime.now()
            idle_connection_set = self.session.pool.idle.copy()
            for conn in idle_connection_set:
                # If the connection was created more than 'refresh_time'
                # seconds ago, release the connection (as its stale)
                if (curr_time - conn.create_time).total_seconds() > refresh_time:
                    log.debug(
                        "Idle connection with id %s was created more than %s seconds ago. Releasing the connection.",
                        id(conn),
                        refresh_time,
                    )
                    self.session.pool.release_connection(conn, True)
            stop_connection_pool_monitor_event.wait(connection_pool_monitor_interval)

    def to_dict(self):
        as_dict = super().to_dict()
        as_dict.update(self._config_to_dict())
        return as_dict

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
                "connection_pool_monitor_interval": self.connection_pool_monitor_interval,
            },
            "cache": {
                "size": self.cache_size,
                "path": self.staging_path,
                "cache_updated_data": self.cache_updated_data,
            },
        }

    # rel_path is file or folder?
    def _get_remote_size(self, rel_path):
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
            log.debug("irods_pt _get_remote_size: %s", ipt_timer)

    # rel_path is file or folder?
    def _exists_remotely(self, rel_path):
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
            log.debug("irods_pt _exists_remotely: %s", ipt_timer)

    def _download(self, rel_path):
        ipt_timer = ExecutionTimer()
        cache_path = self._get_cache_path(rel_path)
        log.debug("Pulling data object '%s' into cache to %s", rel_path, cache_path)

        p = Path(rel_path)
        data_object_name = p.stem + p.suffix
        subcollection_name = p.parent

        collection_path = f"{self.home}/{subcollection_name}"
        data_object_path = f"{collection_path}/{data_object_name}"
        # we need to allow irods to override already existing zero-size output files created
        # in object store cache during job setup (see also https://github.com/galaxyproject/galaxy/pull/17025#discussion_r1394517033)
        # TODO: get rid of this flag when Galaxy stops pre-creating those output files in cache
        options = {kw.FORCE_FLAG_KW: "", kw.DEST_RESC_NAME_KW: self.resource}

        try:
            self.session.data_objects.get(data_object_path, cache_path, **options)
            log.debug("Pulled data object '%s' into cache to %s", rel_path, cache_path)
            return True
        except (DataObjectDoesNotExist, CollectionDoesNotExist):
            log.warning("Collection or data object (%s) does not exist", data_object_path)
            return False
        finally:
            log.debug("irods_pt _download: %s", ipt_timer)

    def _push_to_storage(self, rel_path, source_file=None, from_string=None):
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
            log.debug("irods_pt _push_to_storage: %s", ipt_timer)

    def _delete(self, obj, entire_dir: bool = False, **kwargs) -> bool:
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
