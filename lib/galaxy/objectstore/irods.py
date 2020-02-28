"""
Object Store plugin for the Integrated Rule-Oriented Data Store (iRODS)
"""
from datetime import datetime
import logging
import os
from pathlib import Path
import shutil
import threading
import time

try:
    import irods
    import irods.keywords as kw
    from irods.exception import CollectionDoesNotExist
    from irods.exception import DataObjectDoesNotExist
    from irods.exception import NetworkException
    from irods.session import iRODSSession
except ImportError:
    irods = None

from galaxy.exceptions import (
    ObjectInvalid,
    ObjectNotFound
)
from galaxy.util import (
    bytesize,
    directory_hash_id,
    umask_fix_perms,
)
from galaxy.util.path import safe_relpath
from galaxy.util.sleeper import Sleeper
from ..objectstore import (
    DiskObjectStore,
    local_extra_dirs,
    convert_bytes
)

IRODS_IMPORT_MESSAGE = ('The Python irods package is required to use this feature, please install it')

log = logging.getLogger(__name__)

def _config_xml_error(tag):
    msg = 'No {tag} element in config XML tree'.format(tag=tag)
    raise Exception(msg)

def _config_dict_error(key):
    msg = 'No {key} key in config dictionary'.forma(key=key)
    raise Exception(msg)

def parse_config_xml(config_xml):
    try:
        a_xml = config_xml.findall('auth')
        if not a_xml:
            _config_xml_error('auth')
        username = a_xml[0].get('username')
        password = a_xml[0].get('password')

        r_xml = config_xml.findall('resource')
        if not r_xml:
            _config_xml_error('resource')
        resource_name = r_xml[0].get('name')

        z_xml = config_xml.findall('zone')
        if not z_xml:
            _config_xml_error('zone')
        zone_name = z_xml[0].get('name')

        c_xml = config_xml.findall('connection')
        if not c_xml:
            _config_xml_error('connection')
        host = c_xml[0].get('host', None)
        port = int(c_xml[0].get('port', 0))

        c_xml = config_xml.findall('cache')
        if not c_xml:
            _config_xml_error('cache')
        cache_size = float(c_xml[0].get('size', -1))
        staging_path = c_xml[0].get('path', None)

        attrs = ('type', 'path')
        e_xml = config_xml.findall('extra_dir')
        if not e_xml:
            _config_xml_error('extra_dir')
        extra_dirs = [dict(((k, e.get(k)) for k in attrs)) for e in e_xml]

        return {
            'auth': {
                'username': username,
                'password': password,
            },
            'resource': {
                'name': resource_name,
            },
            'zone': {
                'name': zone_name,
            },
            'connection': {
                'host': host,
                'port': port,
            },
            'cache': {
                'size': cache_size,
                'path': staging_path,
            },
            'extra_dirs': extra_dirs,
        }
    except Exception:
        # Toss it back up after logging, we can't continue loading at this point.
        log.exception("Malformed iRODS ObjectStore Configuration XML -- unable to continue.")
        raise

class CloudConfigMixin(object):

    def _config_to_dict(self):
        return {
            'auth': {
                'username': self.username,
                'password': self.password,
            },
            'resource': {
                'name': self.resource,
            },
            'zone': {
                'name': self.zone,
            },
            'connection': {
                'host': self.host,
                'port': self.port,
            },
            'cache': {
                'size': self.cache_size,
                'path': self.staging_path,
            }
        }

class IRODSObjectStore(DiskObjectStore, CloudConfigMixin):
    """
    Object store that stores objects as data objects in an iRODS collections. A local cache 
    exists that is used as an intermediate location for files between Galaxy and iRODS.
    """
    
    store_type = 'irods'
    
    def __init__(self, config, config_dict):
        super(IRODSObjectStore, self).__init__(config, config_dict)

        auth_dict = config_dict.get('auth')
        if auth_dict is None:
            _config_dict_error('auth')

        self.username = auth_dict.get('username')
        if self.username is None:
            _config_dict_error('auth->username')
        self.password = auth_dict.get('password')
        if self.password is None:
            _config_dict_error('auth->password')

        resource_dict = config_dict['resource']
        if resource_dict is None:
            _config_dict_error('resource')
        self.resource = resource_dict.get('name')
        if self.resource is None:
            _config_dict_error('resource->name')

        zone_dict = config_dict['zone']
        if zone_dict is None:
            _config_dict_error('zone')
        self.zone = zone_dict.get('name')
        if self.zone is None:
            _config_dict_error('zone->name')

        connection_dict = config_dict['connection']
        if connection_dict is None:
            _config_dict_error('connection')
        self.host = connection_dict.get('host')
        if self.host is None:
            _config_dict_error('connection->host')
        self.port = connection_dict.get('port')
        if self.port is None:
            _config_dict_error('connection->port')

        cache_dict = config_dict['cache']
        if cache_dict is None:
            _config_dict_error('cache')
        self.cache_size = cache_dict.get('size', -1)
        if self.cache_size is None:
            _config_dict_error('cache->size')
        self.staging_path = cache_dict.get('path') or self.config.object_store_cache_path
        if self.staging_path is None:
            _config_dict_error('cache->path')

        extra_dirs = dict((e['type'], e['path']) for e in config_dict.get('extra_dirs', []))
        if not extra_dirs:
            _config_dict_error('extra_dirs')
        self.extra_dirs.update(extra_dirs)

        self._initialize()
        
    def __del__(self):
        self.session.cleanup()

    def _initialize(self):
        if irods is None:
            raise Exception(IRODS_IMPORT_MESSAGE)

        self.home =  "/" + self.zone + "/home/" + self.username

        self.session = self._configure_connection(host=self.host, port=self.port, user=self.username, password=self.password, zone=self.zone)
        # Clean cache only if value is set in galaxy config file
        if self.cache_size != -1:
            # Convert GBs to bytes for comparison
            self.cache_size = self.cache_size * bytesize.SUFFIX_TO_BYTES['GI']
            # Helper for interruptable sleep
            self.sleeper = Sleeper()
            self.cache_monitor_thread = threading.Thread(target=self.__cache_monitor)
            self.cache_monitor_thread.start()
            log.info("Cache cleaner manager started")

    def _configure_connection(self, host='localhost', port='1247', user='rods', password='rods', zone='tempZone'):
        with iRODSSession(host=host, port=port, user=user, password=password, zone=zone) as session:
            # Throws NetworkException if connection fails
            try:  
                session.pool.get_connection()
            except NetworkException as e:
                log.error('Could not create iRODS session: ' + str(e))
                raise
            return session

    @classmethod
    def parse_xml(cls, config_xml):
        return parse_config_xml(config_xml)

    def to_dict(self):
        as_dict = super(IRODSObjectStore, self).to_dict()
        as_dict.update(self._config_to_dict())
        return as_dict

    def __cache_monitor(self):
        time.sleep(5)  # Wait for things to load before starting the monitor
        while self.running:
            total_size = 0
            # Is this going to be too expensive of an operation to be done frequently?
            file_list = []
            for dirpath, _, filenames in os.walk(self.staging_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    file_size = os.path.getsize(filepath)
                    total_size += file_size
                    # Get the time given file was last accessed
                    last_access_time = time.localtime(os.stat(filepath)[7])
                    # Compose a tuple of the access time and the file path
                    file_tuple = last_access_time, filepath, file_size
                    file_list.append(file_tuple)
            # Sort the file list (based on access time)
            file_list.sort()
            # Initiate cleaning once within 10% of the defined cache size?
            cache_limit = self.cache_size * 0.9
            if total_size > cache_limit:
                log.info("Initiating cache cleaning: current cache size: %s; clean until smaller than: %s",
                         convert_bytes(total_size), convert_bytes(cache_limit))
                # How much to delete? If simply deleting up to the cache-10% limit,
                # is likely to be deleting frequently and may run the risk of hitting
                # the limit - maybe delete additional #%?
                # For now, delete enough to leave at least 10% of the total cache free
                delete_this_much = total_size - cache_limit
                self.__clean_cache(file_list, delete_this_much)
            self.sleeper.sleep(30)  # Test cache size every 30 seconds?

    def __clean_cache(self, file_list, delete_this_much):
        """ Keep deleting files from the file_list until the size of the deleted
        files is greater than the value in delete_this_much parameter.

        :type file_list: list
        :param file_list: List of candidate files that can be deleted. This method
            will start deleting files from the beginning of the list so the list
            should be sorted accordingly. The list must contains 3-element tuples,
            positioned as follows: position 0 holds file last accessed timestamp
            (as time.struct_time), position 1 holds file path, and position 2 has
            file size (e.g., (<access time>, /mnt/data/dataset_1.dat), 472394)

        :type delete_this_much: int
        :param delete_this_much: Total size of files, in bytes, that should be deleted.
        """
        # Keep deleting datasets from file_list until deleted_amount does not
        # exceed delete_this_much; start deleting from the front of the file list,
        # which assumes the oldest files come first on the list.
        deleted_amount = 0
        for entry in file_list:
            if deleted_amount < delete_this_much:
                deleted_amount += entry[2]
                os.remove(entry[1])
                # Debugging code for printing deleted files' stats
                # folder, file_name = os.path.split(f[1])
                # file_date = time.strftime("%m/%d/%y %H:%M:%S", f[0])
                # log.debug("%s. %-25s %s, size %s (deleted %s/%s)" \
                #     % (i, file_name, convert_bytes(f[2]), file_date, \
                #     convert_bytes(deleted_amount), convert_bytes(delete_this_much)))
            else:
                log.debug("Cache cleaning done. Total space freed: %s", convert_bytes(deleted_amount))
                return

    def _fix_permissions(self, rel_path):
        """ Set permissions on rel_path"""
        for basedir, _, files in os.walk(rel_path):
            umask_fix_perms(basedir, self.config.umask, 0o777, self.config.gid)
            for filename in files:
                path = os.path.join(basedir, filename)
                # Ignore symlinks
                if os.path.islink(path):
                    continue
                umask_fix_perms(path, self.config.umask, 0o666, self.config.gid)

    def _construct_path(self, obj, base_dir=None, dir_only=None, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False, **kwargs):
        # extra_dir should never be constructed from provided data but just
        # make sure there are no shenannigans afoot
        if extra_dir and extra_dir != os.path.normpath(extra_dir):
            log.warning('extra_dir is not normalized: %s', extra_dir)
            raise ObjectInvalid("The requested object is invalid")
        # ensure that any parent directory references in alt_name would not
        # result in a path not contained in the directory path constructed here
        if alt_name:
            if not safe_relpath(alt_name):
                log.warning('alt_name would locate path outside dir: %s', alt_name)
                raise ObjectInvalid("The requested object is invalid")
            # alt_name can contain parent directory references, but S3 will not
            # follow them, so if they are valid we normalize them out
            alt_name = os.path.normpath(alt_name)
        rel_path = os.path.join(*directory_hash_id(obj.id))
        if extra_dir is not None:
            if extra_dir_at_root:
                rel_path = os.path.join(extra_dir, rel_path)
            else:
                rel_path = os.path.join(rel_path, extra_dir)

        # for JOB_WORK directory
        if obj_dir:
            rel_path = os.path.join(rel_path, str(obj.id))
        if base_dir:
            base = self.extra_dirs.get(base_dir)
            return os.path.join(base, rel_path)

        if not dir_only:
            rel_path = os.path.join(rel_path, alt_name if alt_name else "dataset_%s.dat" % obj.id)
        return rel_path

    def _get_cache_path(self, rel_path):
        return os.path.abspath(os.path.join(self.staging_path, rel_path))

    # rel_path is file or folder?
    def _get_size_in_irods(self, rel_path):
        p = Path(rel_path)
        data_object_name =  p.stem + p.suffix
        subcollection_name = p.parent

        collection_path = self.home + "/" + str(subcollection_name)
        data_object_path = collection_path + "/" + str(data_object_name) 

        try:
            data_obj = self.session.data_objects.get(data_object_path)
            return data_obj.__sizeof__()
        except (DataObjectDoesNotExist, CollectionDoesNotExist):
            log.warn("Collection or data object (%s) does not exist", data_object_path)
            return -1

    # rel_path is file or folder?
    def _data_object_exists(self, rel_path):
        p = Path(rel_path)
        data_object_name =  p.stem + p.suffix
        subcollection_name = p.parent

        collection_path = self.home + "/" + str(subcollection_name)
        data_object_path = collection_path + "/" + str(data_object_name) 

        try:
            self.session.data_objects.get(data_object_path)
            return True 
        except (DataObjectDoesNotExist, CollectionDoesNotExist):
            log.warn("Collection or data object (%s) does not exist", data_object_path)
            return False 

    def _in_cache(self, rel_path):
        """ Check if the given dataset is in the local cache and return True if so. """
        cache_path = self._get_cache_path(rel_path)
        return os.path.exists(cache_path)
        # TODO: Part of checking if a file is in cache should be to ensure the
        # size of the cached file matches that on S3. Once the upload tool explicitly
        # creates, this check sould be implemented- in the mean time, it's not
        # looking likely to be implementable reliably.
        # if os.path.exists(cache_path):
        #     # print("***1 %s exists" % cache_path)
        #     if self._key_exists(rel_path):
        #         # print("***2 %s exists in S3" % rel_path)
        #         # Make sure the size in cache is available in its entirety
        #         # print("File '%s' cache size: %s, S3 size: %s" % (cache_path, os.path.getsize(cache_path), self._get_size_in_s3(rel_path)))
        #         if os.path.getsize(cache_path) == self._get_size_in_s3(rel_path):
        #             # print("***2.1 %s exists in S3 and the size is the same as in cache (in_cache=True)" % rel_path)
        #             exists = True
        #         else:
        #             # print("***2.2 %s exists but differs in size from cache (in_cache=False)" % cache_path)
        #             exists = False
        #     else:
        #         # Although not perfect decision making, this most likely means
        #         # that the file is currently being uploaded
        #         # print("***3 %s found in cache but not in S3 (in_cache=True)" % cache_path)
        #         exists = True
        # else:

    def _pull_into_cache(self, rel_path):
        # Ensure the cache directory structure exists (e.g., dataset_#_files/)
        rel_path_dir = os.path.dirname(rel_path)
        if not os.path.exists(self._get_cache_path(rel_path_dir)):
            os.makedirs(self._get_cache_path(rel_path_dir))
        # Now pull in the file
        file_ok = self._download(rel_path)
        self._fix_permissions(self._get_cache_path(rel_path_dir))
        return file_ok

    def _download(self, rel_path):
        log.debug("Pulling data object '%s' into cache to %s", rel_path, self._get_cache_path(rel_path))

        p = Path(rel_path)
        data_object_name =  p.stem + p.suffix
        subcollection_name = p.parent

        collection_path = self.home + "/" + str(subcollection_name)
        data_object_path = collection_path + "/" + str(data_object_name) 
        data_obj = None

        try:
            data_obj = self.session.data_objects.get(data_object_path)
        except (DataObjectDoesNotExist, CollectionDoesNotExist):
            log.warn("Collection or data object (%s) does not exist", data_object_path)
            return False 

        if self.cache_size > 0 and data_obj.__sizeof__() > self.cache_size:
            log.critical("File %s is larger (%s) than the cache size (%s). Cannot download.",
                         rel_path, data_obj.__sizeof__(), self.cache_size)
            return False

        log.debug("Pulled data object '%s' into cache to %s", rel_path, self._get_cache_path(rel_path))
        
        with data_obj.open('rb') as data_obj_fp, open(self._get_cache_path(rel_path), "wb") as cache_fp:
            content = data_obj_fp.read()
            cache_fp.write(content)
        return True

    def _push_to_os(self, rel_path, source_file=None, from_string=None):
        """
        Push the file pointed to by ``rel_path`` to the iRODS. Extract folder name 
        from rel_path as iRODS collection name, and extract file name from rel_path
        as iRODS data object name.
        If ``source_file`` is provided, push that file instead while
        still using ``rel_path`` for collection and object store names.
        If ``from_string`` is provided, set contents of the file to the value of the string.
        """
        p = Path(rel_path)
        data_object_name =  p.stem + p.suffix
        subcollection_name = p.parent

        source_file = source_file if source_file else self._get_cache_path(rel_path)
        options = {kw.FORCE_FLAG_KW: ''}

        if os.path.exists(source_file):
            # Check if the data object exists in iRODS
            collection_path = self.home + "/" + str(subcollection_name)
            data_object_path = collection_path + "/" + str(data_object_name) 
            exists = self.session.data_objects.exists(data_object_path)
            if os.path.getsize(source_file) == 0 and exists:
                log.debug("Wanted to push file '%s' to iRODS collection '%s' but its size is 0; skipping.", source_file, rel_path)
                return True
            if from_string:
                data_obj = self.session.data_objects.create(data_object_path, recurse=True, **options)
                with data_obj.open('w') as data_obj_fp:
                    data_obj_fp.write(from_string)
                log.debug("Pushed data from string '%s' to collection '%s'", from_string, data_object_path)
            else:
                start_time = datetime.now()
                log.debug("Pushing cache file '%s' of size %s bytes to collection '%s'", source_file, os.path.getsize(source_file), rel_path)
                
                # Create sub-collection first
                self.session.collections.create(collection_path, recurse=True)

                file_content = None
                with open(source_file, 'rb') as content_file:
                    file_content = content_file.read()
                
                # Write to file in subcollection created above
                data_obj = self.session.data_objects.create(data_object_path, recurse=True, **options)
                with data_obj.open('w') as data_obj_fp:
                    data_obj_fp.write(file_content)

                end_time = datetime.now()
                log.debug("Pushed cache file '%s' to collection '%s' (%s bytes transfered in %s sec)",
                          source_file, rel_path, os.path.getsize(source_file), end_time - start_time)
            return True
        else:
            log.error("Tried updating key '%s' from source file '%s', but source file does not exist.",
                      rel_path, source_file)
        return False

    def file_ready(self, obj, **kwargs):
        """
        A helper method that checks if a file corresponding to a dataset is
        ready and available to be used. Return ``True`` if so, ``False`` otherwise.
        """
        rel_path = self._construct_path(obj, **kwargs)
        # Make sure the size in cache is available in its entirety
        if self._in_cache(rel_path):
            if os.path.getsize(self._get_cache_path(rel_path)) == self._get_size_in_irods(rel_path):
                return True
            log.debug("Waiting for dataset %s to transfer from OS: %s/%s", rel_path,
                      os.path.getsize(self._get_cache_path(rel_path)), self._get_size_in_irods(rel_path))
        return False

    def exists(self, obj, **kwargs):
        in_cache = in_irods = False
        rel_path = self._construct_path(obj, **kwargs)

        # Check cache
        if self._in_cache(rel_path):
            in_cache = True
        # Check iRODS 
        in_irods = self._data_object_exists(rel_path)

        # dir_only does not get synced so shortcut the decision
        dir_only = kwargs.get('dir_only', False)
        base_dir = kwargs.get('base_dir', None)
        if dir_only:
            if in_cache or in_irods:
                return True
            # for JOB_WORK directory
            elif base_dir:
                if not os.path.exists(rel_path):
                    os.makedirs(rel_path)
                return True
            else:
                return False

        # TODO: Sync should probably not be done here. Add this to an async upload stack?
        if in_cache and not in_irods:
            self._push_to_os(rel_path, source_file=self._get_cache_path(rel_path))
            return True
        elif in_irods:
            return True
        else:
            return False

    def create(self, obj, **kwargs):
        if not self.exists(obj, **kwargs):

            # Pull out locally used fields
            extra_dir = kwargs.get('extra_dir', None)
            extra_dir_at_root = kwargs.get('extra_dir_at_root', False)
            dir_only = kwargs.get('dir_only', False)
            alt_name = kwargs.get('alt_name', None)

            # Construct hashed path
            rel_path = os.path.join(*directory_hash_id(obj.id))

            # Optionally append extra_dir
            if extra_dir is not None:
                if extra_dir_at_root:
                    rel_path = os.path.join(extra_dir, rel_path)
                else:
                    rel_path = os.path.join(rel_path, extra_dir)

            # Create given directory in cache
            cache_dir = os.path.join(self.staging_path, rel_path)
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)

            if not dir_only:
                rel_path = os.path.join(rel_path, alt_name if alt_name else "dataset_%s.dat" % obj.id)
                open(os.path.join(self.staging_path, rel_path), 'w').close()
                self._push_to_os(rel_path, from_string='')

    def empty(self, obj, **kwargs):
        if self.exists(obj, **kwargs):
            return bool(self.size(obj, **kwargs) > 0)
        else:
            raise ObjectNotFound('objectstore.empty, object does not exist: %s, kwargs: %s'
                                 % (str(obj), str(kwargs)))

    def size(self, obj, **kwargs):
        rel_path = self._construct_path(obj, **kwargs)
        if self._in_cache(rel_path):
            try:
                return os.path.getsize(self._get_cache_path(rel_path))
            except OSError as ex:
                log.info("Could not get size of file '%s' in local cache, will try S3. Error: %s", rel_path, ex)
        elif self.exists(obj, **kwargs):
            return self._get_size_in_irods(rel_path)
        log.warning("Did not find dataset '%s', returning 0 for size", rel_path)
        return 0

    def delete(self, obj, entire_dir=False, **kwargs):
        rel_path = self._construct_path(obj, **kwargs)
        extra_dir = kwargs.get('extra_dir', None)
        base_dir = kwargs.get('base_dir', None)
        dir_only = kwargs.get('dir_only', False)
        obj_dir = kwargs.get('obj_dir', False)
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
                shutil.rmtree(self._get_cache_path(rel_path))

                col_path = self.home + "/" + str(rel_path)
                col = None
                try:
                    col = self.session.collections.get(col_path)
                except CollectionDoesNotExist:
                    log.warn("Collection (%s) does not exist!", col_path)
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
                os.unlink(self._get_cache_path(rel_path))
                # Delete from irods as well
                p = Path(rel_path)
                data_object_name =  p.stem + p.suffix
                subcollection_name = p.parent

                collection_path = self.home + "/" + str(subcollection_name)
                data_object_path = collection_path + "/" + str(data_object_name) 

                try:
                    data_obj = self.session.data_objects.get(data_object_path)
                    # remove object
                    data_obj.unlink(force=True)
                    return True
                except (DataObjectDoesNotExist, CollectionDoesNotExist):
                    log.info("Collection or data object (%s) does not exist", data_object_path)
                    return True 

        except OSError:
            log.exception('%s delete error', self.get_filename(obj, **kwargs))
        return False

    def get_data(self, obj, start=0, count=-1, **kwargs):
        rel_path = self._construct_path(obj, **kwargs)
        # Check cache first and get file if not there
        if not self._in_cache(rel_path):
            self._pull_into_cache(rel_path)
        # Read the file content from cache
        data_file = open(self._get_cache_path(rel_path), 'r')
        data_file.seek(start)
        content = data_file.read(count)
        data_file.close()
        return content

    def get_filename(self, obj, **kwargs):
        base_dir = kwargs.get('base_dir', None)
        dir_only = kwargs.get('dir_only', False)
        obj_dir = kwargs.get('obj_dir', False)
        rel_path = self._construct_path(obj, **kwargs)

        # for JOB_WORK directory
        if base_dir and dir_only and obj_dir:
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
            return cache_path
        # Check if the file exists in persistent storage and, if it does, pull it into cache
        elif self.exists(obj, **kwargs):
            if dir_only:  # Directories do not get pulled into cache
                return cache_path
            else:
                if self._pull_into_cache(rel_path):
                    return cache_path
        # For the case of retrieving a directory only, return the expected path
        # even if it does not exist.
        # if dir_only:
        #     return cache_path
        raise ObjectNotFound('objectstore.get_filename, no cache_path: %s, kwargs: %s'
                             % (str(obj), str(kwargs)))
        # return cache_path # Until the upload tool does not explicitly create the dataset, return expected path

    def update_from_file(self, obj, file_name=None, create=False, **kwargs):
        if create:
            self.create(obj, **kwargs)
        if self.exists(obj, **kwargs):
            rel_path = self._construct_path(obj, **kwargs)
            # Chose whether to use the dataset file itself or an alternate file
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
            self._push_to_os(rel_path, source_file)
        else:
            raise ObjectNotFound('objectstore.update_from_file, object does not exist: %s, kwargs: %s'
                                 % (str(obj), str(kwargs)))

    # Unlike S3, url is not really applicable to iRODS
    def get_object_url(self, obj, **kwargs):
        if self.exists(obj, **kwargs):
            rel_path = self._construct_path(obj, **kwargs)

            p = Path(rel_path)
            data_object_name =  p.stem + p.suffix
            subcollection_name = p.parent

            collection_path = self.home + "/" + str(subcollection_name)
            data_object_path = collection_path + "/" + str(data_object_name)
            
            return data_object_path

    def get_store_usage_percent(self):
        return 0.0