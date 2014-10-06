"""
objectstore package, abstraction for storing blobs of data for use in Galaxy,
all providers ensure that data can be accessed on the filesystem for running
tools
"""

import os
import random
import shutil
import logging
import threading
from xml.etree import ElementTree

from galaxy.util import umask_fix_perms, force_symlink
from galaxy.exceptions import ObjectInvalid, ObjectNotFound
from galaxy.util.sleeper import Sleeper
from galaxy.util.directory_hash import directory_hash_id
from galaxy.util.odict import odict
try:
    from sqlalchemy.orm import object_session
except ImportError:
    object_session = None

NO_SESSION_ERROR_MESSAGE = "Attempted to 'create' object store entity in configuration with no database session present."

log = logging.getLogger( __name__ )


class ObjectStore(object):
    """
    ObjectStore abstract interface
    """
    def __init__(self, config, config_xml=None, **kwargs):
        self.running = True
        self.extra_dirs = {}

    def shutdown(self):
        self.running = False

    def exists(self, obj, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """
        Returns True if the object identified by `obj` exists in this file
        store, False otherwise.

        FIELD DESCRIPTIONS (these apply to all the methods in this class):

        :type obj: object
        :param obj: A Galaxy object with an assigned database ID accessible via
                    the .id attribute.

        :type base_dir: string
        :param base_dir: A key in self.extra_dirs corresponding to the base
                         directory in which this object should be created, or
                         None to specify the default directory.

        :type dir_only: bool
        :param dir_only: If True, check only the path where the file
                         identified by `obj` should be located, not the dataset
                         itself. This option applies to `extra_dir` argument as
                         well.

        :type extra_dir: string
        :param extra_dir: Append `extra_dir` to the directory structure where
                          the dataset identified by `obj` should be located.
                          (e.g., 000/extra_dir/obj.id)

        :type extra_dir_at_root: bool
        :param extra_dir_at_root: Applicable only if `extra_dir` is set.
                                  If True, the `extra_dir` argument is placed at
                                  root of the created directory structure rather
                                  than at the end (e.g., extra_dir/000/obj.id
                                  vs. 000/extra_dir/obj.id)

        :type alt_name: string
        :param alt_name: Use this name as the alternative name for the created
                         dataset rather than the default.
        """
        raise NotImplementedError()

    def file_ready(self, obj, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """ A helper method that checks if a file corresponding to a dataset
        is ready and available to be used. Return True if so, False otherwise."""
        return True

    def create(self, obj, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """
        Mark the object identified by `obj` as existing in the store, but with
        no content. This method will create a proper directory structure for
        the file if the directory does not already exist.
        See `exists` method for the description of other fields.
        """
        raise NotImplementedError()

    def empty(self, obj, base_dir=None, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """
        Test if the object identified by `obj` has content.
        If the object does not exist raises `ObjectNotFound`.
        See `exists` method for the description of the fields.
        """
        raise NotImplementedError()

    def size(self, obj, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """
        Return size of the object identified by `obj`.
        If the object does not exist, return 0.
        See `exists` method for the description of the fields.
        """
        raise NotImplementedError()

    def delete(self, obj, entire_dir=False, base_dir=None, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """
        Deletes the object identified by `obj`.
        See `exists` method for the description of other fields.

        :type entire_dir: bool
        :param entire_dir: If True, delete the entire directory pointed to by
                           extra_dir. For safety reasons, this option applies
                           only for and in conjunction with the extra_dir option.
        """
        raise NotImplementedError()

    def get_data(self, obj, start=0, count=-1, base_dir=None, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """
        Fetch `count` bytes of data starting at offset `start` from the
        object identified uniquely by `obj`.
        If the object does not exist raises `ObjectNotFound`.
        See `exists` method for the description of other fields.

        :type start: int
        :param start: Set the position to start reading the dataset file

        :type count: int
        :param count: Read at most `count` bytes from the dataset
        """
        raise NotImplementedError()

    def get_filename(self, obj, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """
        Get the expected filename (including the absolute path) which can be used
        to access the contents of the object uniquely identified by `obj`.
        See `exists` method for the description of the fields.
        """
        raise NotImplementedError()

    def update_from_file(self, obj, base_dir=None, extra_dir=None, extra_dir_at_root=False, alt_name=None, file_name=None, create=False):
        """
        Inform the store that the file associated with the object has been
        updated. If `file_name` is provided, update from that file instead
        of the default.
        If the object does not exist raises `ObjectNotFound`.
        See `exists` method for the description of other fields.

        :type file_name: string
        :param file_name: Use file pointed to by `file_name` as the source for
                          updating the dataset identified by `obj`

        :type create: bool
        :param create: If True and the default dataset does not exist, create it first.
        """
        raise NotImplementedError()

    def get_object_url(self, obj, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """
        If the store supports direct URL access, return a URL. Otherwise return
        None.
        Note: need to be careful to to bypass dataset security with this.
        See `exists` method for the description of the fields.
        """
        raise NotImplementedError()

    def get_store_usage_percent(self):
        """
        Return the percentage indicating how full the store is
        """
        raise NotImplementedError()

    ## def get_staging_command( id ):
    ##     """
    ##     Return a shell command that can be prepended to the job script to stage the
    ##     dataset -- runs on worker nodes.
    ##
    ##     Note: not sure about the interface here. Should this return a filename, command
    ##     tuple? Is this even a good idea, seems very useful for S3, other object stores?
    ##     """


class DiskObjectStore(ObjectStore):
    """
    Standard Galaxy object store, stores objects in files under a specific
    directory on disk.

    >>> from galaxy.util.bunch import Bunch
    >>> import tempfile
    >>> file_path=tempfile.mkdtemp()
    >>> obj = Bunch(id=1)
    >>> s = DiskObjectStore(Bunch(umask=077, job_working_directory=file_path, new_file_path=file_path, object_store_check_old_style=False), file_path=file_path)
    >>> s.create(obj)
    >>> s.exists(obj)
    True
    >>> assert s.get_filename(obj) == file_path + '/000/dataset_1.dat'
    """
    def __init__(self, config, config_xml=None, file_path=None, extra_dirs=None):
        super(DiskObjectStore, self).__init__(config, config_xml=None, file_path=file_path, extra_dirs=extra_dirs)
        self.file_path = file_path or config.file_path
        self.config = config
        self.check_old_style = config.object_store_check_old_style
        self.extra_dirs['job_work'] = config.job_working_directory
        self.extra_dirs['temp'] = config.new_file_path
        #The new config_xml overrides universe settings.
        if config_xml is not None:
            for e in config_xml:
                if e.tag == 'files_dir':
                    self.file_path = e.get('path')
                else:
                    self.extra_dirs[e.tag] = e.get('path')
        if extra_dirs is not None:
            self.extra_dirs.update( extra_dirs )

    def _get_filename(self, obj, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """Class method that returns the absolute path for the file corresponding
        to the `obj`.id regardless of whether the file exists.
        """
        path = self._construct_path(obj, base_dir=base_dir, dir_only=dir_only, extra_dir=extra_dir, extra_dir_at_root=extra_dir_at_root, alt_name=alt_name, old_style=True)
        # For backward compatibility, check the old style root path first; otherwise,
        # construct hashed path
        if not os.path.exists(path):
            return self._construct_path(obj, base_dir=base_dir, dir_only=dir_only, extra_dir=extra_dir, extra_dir_at_root=extra_dir_at_root, alt_name=alt_name)

    # TODO: rename to _disk_path or something like that to avoid conflicts with children that'll use the local_extra_dirs decorator, e.g. S3
    def _construct_path(self, obj, old_style=False, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None, **kwargs):
        """ Construct the expected absolute path for accessing the object
            identified by `obj`.id.

        :type base_dir: string
        :param base_dir: A key in self.extra_dirs corresponding to the base
                         directory in which this object should be created, or
                         None to specify the default directory.

        :type dir_only: bool
        :param dir_only: If True, check only the path where the file
                         identified by `obj` should be located, not the
                         dataset itself. This option applies to `extra_dir`
                         argument as well.

        :type extra_dir: string
        :param extra_dir: Append the value of this parameter to the expected path
                          used to access the object identified by `obj`
                          (e.g., /files/000/<extra_dir>/dataset_10.dat).

        :type alt_name: string
        :param alt_name: Use this name as the alternative name for the returned
                         dataset rather than the default.

        :type old_style: bool
        param old_style: This option is used for backward compatibility. If True
                         the composed directory structure does not include a hash id
                         (e.g., /files/dataset_10.dat (old) vs. /files/000/dataset_10.dat (new))
        """
        base = self.extra_dirs.get(base_dir, self.file_path)
        if old_style:
            if extra_dir is not None:
                path = os.path.join(base, extra_dir)
            else:
                path = base
        else:
            # Construct hashed path
            rel_path = os.path.join(*directory_hash_id(obj.id))
            # Optionally append extra_dir
            if extra_dir is not None:
                if extra_dir_at_root:
                    rel_path = os.path.join(extra_dir, rel_path)
                else:
                    rel_path = os.path.join(rel_path, extra_dir)
            path = os.path.join(base, rel_path)
        if not dir_only:
            path = os.path.join(path, alt_name if alt_name else "dataset_%s.dat" % obj.id)
        return os.path.abspath(path)

    def exists(self, obj, **kwargs):
        if self.check_old_style:
            path = self._construct_path(obj, old_style=True, **kwargs)
            # For backward compatibility, check root path first; otherwise, construct
            # and check hashed path
            if os.path.exists(path):
                return True
        return os.path.exists(self._construct_path(obj, **kwargs))

    def create(self, obj, **kwargs):
        if not self.exists(obj, **kwargs):
            path = self._construct_path(obj, **kwargs)
            dir_only = kwargs.get('dir_only', False)
            # Create directory if it does not exist
            dir = path if dir_only else os.path.dirname(path)
            if not os.path.exists(dir):
                os.makedirs(dir)
            # Create the file if it does not exist
            if not dir_only:
                open(path, 'w').close()  # Should be rb?
                umask_fix_perms(path, self.config.umask, 0666)

    def empty(self, obj, **kwargs):
        return os.path.getsize(self.get_filename(obj, **kwargs)) == 0

    def size(self, obj, **kwargs):
        if self.exists(obj, **kwargs):
            try:
                return os.path.getsize(self.get_filename(obj, **kwargs))
            except OSError:
                return 0
        else:
            return 0

    def delete(self, obj, entire_dir=False, **kwargs):
        path = self.get_filename(obj, **kwargs)
        extra_dir = kwargs.get('extra_dir', None)
        try:
            if entire_dir and extra_dir:
                shutil.rmtree(path)
                return True
            if self.exists(obj, **kwargs):
                os.remove(path)
                return True
        except OSError, ex:
            log.critical('%s delete error %s' % (self._get_filename(obj, **kwargs), ex))
        return False

    def get_data(self, obj, start=0, count=-1, **kwargs):
        data_file = open(self.get_filename(obj, **kwargs), 'r')  # Should be rb?
        data_file.seek(start)
        content = data_file.read(count)
        data_file.close()
        return content

    def get_filename(self, obj, **kwargs):
        if self.check_old_style:
            path = self._construct_path(obj, old_style=True, **kwargs)
            # For backward compatibility, check root path first; otherwise, construct
            # and return hashed path
            if os.path.exists(path):
                return path
        return self._construct_path(obj, **kwargs)

    def update_from_file(self, obj, file_name=None, create=False, **kwargs):
        """ `create` parameter is not used in this implementation """
        preserve_symlinks = kwargs.pop( 'preserve_symlinks', False )
        #FIXME: symlinks and the object store model may not play well together
        #these should be handled better, e.g. registering the symlink'd file as an object
        if create:
            self.create(obj, **kwargs)
        if file_name and self.exists(obj, **kwargs):
            try:
                if preserve_symlinks and os.path.islink( file_name ):
                    force_symlink( os.readlink( file_name ), self.get_filename( obj, **kwargs ) )
                else:
                    shutil.copy( file_name, self.get_filename( obj, **kwargs ) )
            except IOError, ex:
                log.critical('Error copying %s to %s: %s' % (file_name,
                    self._get_filename(obj, **kwargs), ex))
                raise ex

    def get_object_url(self, obj, **kwargs):
        return None

    def get_store_usage_percent(self):
        st = os.statvfs(self.file_path)
        return ( float( st.f_blocks - st.f_bavail ) / st.f_blocks ) * 100


class CachingObjectStore(ObjectStore):
    """
    Object store that uses a directory for caching files, but defers and writes
    back to another object store.
    """

    def __init__(self, path, backend):
        super(CachingObjectStore, self).__init__(self, path, backend)


class NestedObjectStore(ObjectStore):
    """
    Base for ObjectStores that use other ObjectStores
    (DistributedObjectStore, HierarchicalObjectStore)
    """

    def __init__(self, config, config_xml=None):
        super(NestedObjectStore, self).__init__(config, config_xml=config_xml)
        self.backends = {}

    def shutdown(self):
        for store in self.backends.values():
            store.shutdown()
        super(NestedObjectStore, self).shutdown()

    def exists(self, obj, **kwargs):
        return self.__call_method('exists', obj, False, False, **kwargs)

    def file_ready(self, obj, **kwargs):
        return self.__call_method('file_ready', obj, False, False, **kwargs)

    def create(self, obj, **kwargs):
        random.choice(self.backends.values()).create(obj, **kwargs)

    def empty(self, obj, **kwargs):
        return self.__call_method('empty', obj, True, False, **kwargs)

    def size(self, obj, **kwargs):
        return self.__call_method('size', obj, 0, False, **kwargs)

    def delete(self, obj, **kwargs):
        return self.__call_method('delete', obj, False, False, **kwargs)

    def get_data(self, obj, **kwargs):
        return self.__call_method('get_data', obj, ObjectNotFound, True, **kwargs)

    def get_filename(self, obj, **kwargs):
        return self.__call_method('get_filename', obj, ObjectNotFound, True, **kwargs)

    def update_from_file(self, obj, **kwargs):
        if kwargs.get('create', False):
            self.create(obj, **kwargs)
            kwargs['create'] = False
        return self.__call_method('update_from_file', obj, ObjectNotFound, True, **kwargs)

    def get_object_url(self, obj, **kwargs):
        return self.__call_method('get_object_url', obj, None, False, **kwargs)

    def __call_method(self, method, obj, default, default_is_exception, **kwargs):
        """
        Check all children object stores for the first one with the dataset
        """
        for key, store in self.backends.items():
            if store.exists(obj, **kwargs):
                return store.__getattribute__(method)(obj, **kwargs)
        if default_is_exception:
            raise default( 'objectstore, __call_method failed: %s on %s, kwargs: %s'
                % ( method, str( obj ), str( kwargs ) ) )
        else:
            return default


class DistributedObjectStore(NestedObjectStore):
    """
    ObjectStore that defers to a list of backends, for getting objects the
    first store where the object exists is used, objects are created in a
    store selected randomly, but with weighting.
    """

    def __init__(self, config, config_xml=None, fsmon=False):
        super(DistributedObjectStore, self).__init__(config, config_xml=config_xml)
        if config_xml is None:
            self.distributed_config = config.distributed_object_store_config_file
            assert self.distributed_config is not None, "distributed object store ('object_store = distributed') " \
                                                        "requires a config file, please set one in " \
                                                        "'distributed_object_store_config_file')"
        self.backends = {}
        self.weighted_backend_ids = []
        self.original_weighted_backend_ids = []
        self.max_percent_full = {}
        self.global_max_percent_full = 0.0
        random.seed()
        self.__parse_distributed_config(config, config_xml)
        self.sleeper = None
        if fsmon and ( self.global_max_percent_full or filter( lambda x: x != 0.0, self.max_percent_full.values() ) ):
            self.sleeper = Sleeper()
            self.filesystem_monitor_thread = threading.Thread(target=self.__filesystem_monitor)
            self.filesystem_monitor_thread.setDaemon( True )
            self.filesystem_monitor_thread.start()
            log.info("Filesystem space monitor started")

    def __parse_distributed_config(self, config, config_xml=None):
        if config_xml is None:
            root = ElementTree.parse(self.distributed_config).getroot()
            log.debug('Loading backends for distributed object store from %s' % self.distributed_config)
        else:
            root = config_xml.find('backends')
            log.debug('Loading backends for distributed object store from %s' % config_xml.get('id'))
        self.global_max_percent_full = float(root.get('maxpctfull', 0))
        for elem in [ e for e in root if e.tag == 'backend' ]:
            id = elem.get('id')
            weight = int(elem.get('weight', 1))
            maxpctfull = float(elem.get('maxpctfull', 0))
            if elem.get('type', 'disk'):
                path = None
                extra_dirs = {}
                for sub in elem:
                    if sub.tag == 'files_dir':
                        path = sub.get('path')
                    elif sub.tag == 'extra_dir':
                        type = sub.get('type')
                        extra_dirs[type] = sub.get('path')
                self.backends[id] = DiskObjectStore(config, file_path=path, extra_dirs=extra_dirs)
                self.max_percent_full[id] = maxpctfull
                log.debug("Loaded disk backend '%s' with weight %s and file_path: %s" % (id, weight, path))
                if extra_dirs:
                    log.debug("    Extra directories:")
                    for type, dir in extra_dirs.items():
                        log.debug("        %s: %s" % (type, dir))
            for i in range(0, weight):
                # The simplest way to do weighting: add backend ids to a
                # sequence the number of times equalling weight, then randomly
                # choose a backend from that sequence at creation
                self.weighted_backend_ids.append(id)
        self.original_weighted_backend_ids = self.weighted_backend_ids

    def shutdown(self):
        super(DistributedObjectStore, self).shutdown()
        if self.sleeper is not None:
            self.sleeper.wake()

    def __filesystem_monitor(self):
        while self.running:
            new_weighted_backend_ids = self.original_weighted_backend_ids
            for id, backend in self.backends.items():
                maxpct = self.max_percent_full[id] or self.global_max_percent_full
                pct = backend.get_store_usage_percent()
                if pct > maxpct:
                    new_weighted_backend_ids = filter(lambda x: x != id, new_weighted_backend_ids)
            self.weighted_backend_ids = new_weighted_backend_ids
            self.sleeper.sleep(120)  # Test free space every 2 minutes

    def create(self, obj, **kwargs):
        """
        create() is the only method in which obj.object_store_id may be None
        """
        if obj.object_store_id is None or not self.exists(obj, **kwargs):
            if obj.object_store_id is None or obj.object_store_id not in self.weighted_backend_ids:
                try:
                    obj.object_store_id = random.choice(self.weighted_backend_ids)
                except IndexError:
                    raise ObjectInvalid( 'objectstore.create, could not generate obj.object_store_id: %s, kwargs: %s'
                        % ( str( obj ), str( kwargs ) ) )
                create_object_in_session( obj )
                log.debug("Selected backend '%s' for creation of %s %s" % (obj.object_store_id, obj.__class__.__name__, obj.id))
            else:
                log.debug("Using preferred backend '%s' for creation of %s %s" % (obj.object_store_id, obj.__class__.__name__, obj.id))
            self.backends[obj.object_store_id].create(obj, **kwargs)

    def __call_method(self, method, obj, default, default_is_exception, **kwargs):
        object_store_id = self.__get_store_id_for(obj, **kwargs)
        if object_store_id is not None:
            return self.backends[object_store_id].__getattribute__(method)(obj, **kwargs)
        if default_is_exception:
            raise default( 'objectstore, __call_method failed: %s on %s, kwargs: %s'
                % ( method, str( obj ), str( kwargs ) ) )
        else:
            return default

    def __get_store_id_for(self, obj, **kwargs):
        if obj.object_store_id is not None and obj.object_store_id in self.backends:
            return obj.object_store_id
        else:
            # if this instance has been switched from a non-distributed to a
            # distributed object store, or if the object's store id is invalid,
            # try to locate the object
            log.warning('The backend object store ID (%s) for %s object with ID %s is invalid' % (obj.object_store_id, obj.__class__.__name__, obj.id))
            for id, store in self.backends.items():
                if store.exists(obj, **kwargs):
                    log.warning('%s object with ID %s found in backend object store with ID %s' % (obj.__class__.__name__, obj.id, id))
                    obj.object_store_id = id
                    create_object_in_session( obj )
                    return id
        return None


class HierarchicalObjectStore(NestedObjectStore):
    """
    ObjectStore that defers to a list of backends, for getting objects the
    first store where the object exists is used, objects are always created
    in the first store.
    """

    def __init__(self, config, config_xml=None, fsmon=False):
        super(HierarchicalObjectStore, self).__init__(config, config_xml=config_xml)
        self.backends = odict()
        for b in sorted(config_xml.find('backends'), key=lambda b: int(b.get('order'))):
            self.backends[int(b.get('order'))] = build_object_store_from_config(config, fsmon=fsmon, config_xml=b)

    def exists(self, obj, **kwargs):
        """
        Exists must check all child object stores
        """
        for store in self.backends.values():
            if store.exists(obj, **kwargs):
                return True
        return False

    def create(self, obj, **kwargs):
        """
        Create will always be called by the primary object_store
        """
        self.backends[0].create(obj, **kwargs)


def build_object_store_from_config(config, fsmon=False, config_xml=None):
    """
    Depending on the configuration setting, invoke the appropriate object store
    """

    if config_xml is None and os.path.exists( config.object_store_config_file ):
        # This is a top level invocation of build_object_store_from_config, and
        # we have an object_store_conf.xml -- read the .xml and build
        # accordingly
        root = ElementTree.parse(config.object_store_config_file).getroot()
        store = root.get('type')
        config_xml = root
    elif config_xml is not None:
        store = config_xml.get('type')
    else:
        store = config.object_store

    if store == 'disk':
        return DiskObjectStore(config=config, config_xml=config_xml)
    elif store == 's3':
        from .s3 import S3ObjectStore
        return S3ObjectStore(config=config, config_xml=config_xml)
    elif store == 'swift':
        from .s3 import SwiftObjectStore
        return SwiftObjectStore(config=config, config_xml=config_xml)
    elif store == 'distributed':
        return DistributedObjectStore(config=config, fsmon=fsmon, config_xml=config_xml)
    elif store == 'hierarchical':
        return HierarchicalObjectStore(config=config, config_xml=config_xml)
    elif store == 'irods':
        from .rods import IRODSObjectStore
        return IRODSObjectStore(config=config, config_xml=config_xml)
    elif store == 'pulsar':
        from .pulsar import PulsarObjectStore
        return PulsarObjectStore(config=config, config_xml=config_xml)
    else:
        log.error("Unrecognized object store definition: {0}".format(store))


def local_extra_dirs( func ):
    """ A decorator for non-local plugins to utilize local directories for their extra_dirs (job_working_directory and temp).
    """
    def wraps( self, *args, **kwargs ):
        if kwargs.get( 'base_dir', None ) is None:
            return func( self, *args, **kwargs )
        else:
            for c in self.__class__.__mro__:
                if c.__name__ == 'DiskObjectStore':
                    return getattr( c, func.__name__ )( self, *args, **kwargs )
            raise Exception( "Could not call DiskObjectStore's %s method, does your Object Store plugin inherit from DiskObjectStore?" % func.__name__ )
    return wraps


def convert_bytes(bytes):
    """ A helper function used for pretty printing disk usage """
    if bytes is None:
        bytes = 0
    bytes = float(bytes)

    if bytes >= 1099511627776:
        terabytes = bytes / 1099511627776
        size = '%.2fTB' % terabytes
    elif bytes >= 1073741824:
        gigabytes = bytes / 1073741824
        size = '%.2fGB' % gigabytes
    elif bytes >= 1048576:
        megabytes = bytes / 1048576
        size = '%.2fMB' % megabytes
    elif bytes >= 1024:
        kilobytes = bytes / 1024
        size = '%.2fKB' % kilobytes
    else:
        size = '%.2fb' % bytes
    return size


def create_object_in_session( obj ):
    session = object_session( obj ) if object_session is not None else None
    if session is not None:
        object_session( obj ).add( obj )
        object_session( obj ).flush()
    else:
        raise Exception( NO_SESSION_ERROR_MESSAGE )
