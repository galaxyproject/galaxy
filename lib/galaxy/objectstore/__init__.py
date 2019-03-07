"""
objectstore package, abstraction for storing blobs of data for use in Galaxy.

all providers ensure that data can be accessed on the filesystem for running
tools
"""

import logging
import os
import random
import shutil
import threading
import time
from xml.etree import ElementTree

import yaml
try:
    from sqlalchemy.orm import object_session
except ImportError:
    object_session = None

from galaxy.exceptions import ObjectInvalid, ObjectNotFound
from galaxy.util import (
    directory_hash_id,
    force_symlink,
    umask_fix_perms,
)
from galaxy.util.odict import odict
from galaxy.util.path import (
    safe_makedirs,
    safe_relpath,
)
from galaxy.util.sleeper import Sleeper

NO_SESSION_ERROR_MESSAGE = "Attempted to 'create' object store entity in configuration with no database session present."

log = logging.getLogger(__name__)


class ObjectStore(object):

    """ObjectStore abstract interface.

    FIELD DESCRIPTIONS (these apply to all the methods in this class):

    :type obj: StorableObject
    :param obj: A Galaxy object with an assigned database ID accessible via
        the .id attribute.

    :type base_dir: string
    :param base_dir: A key in `self.extra_dirs` corresponding to the base
        directory in which this object should be created, or `None` to specify
        the default directory.

    :type dir_only: boolean
    :param dir_only: If `True`, check only the path where the file identified
        by `obj` should be located, not the dataset itself. This option applies
        to `extra_dir` argument as well.

    :type extra_dir: string
    :param extra_dir: Append `extra_dir` to the directory structure where the
        dataset identified by `obj` should be located. (e.g.,
        000/extra_dir/obj.id). Valid values include 'job_work' (defaulting to
        config.jobs_directory =
        '$GALAXY_ROOT/database/jobs_directory');
        'temp' (defaulting to config.new_file_path =
        '$GALAXY_ROOT/database/tmp').

    :type extra_dir_at_root: boolean
    :param extra_dir_at_root: Applicable only if `extra_dir` is set. If True,
        the `extra_dir` argument is placed at root of the created directory
        structure rather than at the end (e.g., extra_dir/000/obj.id vs.
        000/extra_dir/obj.id)

    :type alt_name: string
    :param alt_name: Use this name as the alternative name for the created
        dataset rather than the default.

    :type obj_dir: boolean
    :param obj_dir: Append a subdirectory named with the object's ID (e.g.
        000/obj.id)
    """

    def __init__(self, config, config_dict={}, **kwargs):
        """
        :type config: object
        :param config: An object, most likely populated from
            `galaxy/config.ini`, having the following attributes:

            * object_store_check_old_style (only used by the
              :class:`DiskObjectStore` subclass)
            * jobs_directory -- Each job is given a unique empty directory
              as its current working directory. This option defines in what
              parent directory those directories will be created.
            * new_file_path -- Used to set the 'temp' extra_dir.
        """
        self.running = True
        self.config = config
        self.check_old_style = config.object_store_check_old_style
        self.store_by = config_dict.get("store_by", None) or getattr(config, "object_store_store_by", "id")
        assert self.store_by in ["id", "uuid"]
        extra_dirs = {}
        extra_dirs['job_work'] = config.jobs_directory
        extra_dirs['temp'] = config.new_file_path
        extra_dirs.update(dict(
            (e['type'], e['path']) for e in config_dict.get('extra_dirs', [])))
        self.extra_dirs = extra_dirs

    def shutdown(self):
        """Close any connections for this ObjectStore."""
        self.running = False

    def exists(self, obj, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None):
        """Return True if the object identified by `obj` exists, False otherwise."""
        raise NotImplementedError()

    def file_ready(self, obj, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False):
        """
        Check if a file corresponding to a dataset is ready to be used.

        Return True if so, False otherwise
        """
        return True

    def create(self, obj, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False):
        """
        Mark the object (`obj`) as existing in the store, but with no content.

        This method will create a proper directory structure for
        the file if the directory does not already exist.
        """
        raise NotImplementedError()

    def empty(self, obj, base_dir=None, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False):
        """
        Test if the object identified by `obj` has content.

        If the object does not exist raises `ObjectNotFound`.
        """
        raise NotImplementedError()

    def size(self, obj, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False):
        """
        Return size of the object identified by `obj`.

        If the object does not exist, return 0.
        """
        raise NotImplementedError()

    def delete(self, obj, entire_dir=False, base_dir=None, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False):
        """
        Delete the object identified by `obj`.

        :type entire_dir: boolean
        :param entire_dir: If True, delete the entire directory pointed to by
                           extra_dir. For safety reasons, this option applies
                           only for and in conjunction with the extra_dir or
                           obj_dir options.
        """
        raise NotImplementedError()

    def get_data(self, obj, start=0, count=-1, base_dir=None, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False):
        """
        Fetch `count` bytes of data offset by `start` bytes using `obj.id`.

        If the object does not exist raises `ObjectNotFound`.

        :type start: int
        :param start: Set the position to start reading the dataset file

        :type count: int
        :param count: Read at most `count` bytes from the dataset
        """
        raise NotImplementedError()

    def get_filename(self, obj, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False):
        """
        Get the expected filename with absolute path for object with id `obj.id`.

        This can be used to access the contents of the object.
        """
        raise NotImplementedError()

    def update_from_file(self, obj, base_dir=None, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False, file_name=None, create=False):
        """
        Inform the store that the file associated with `obj.id` has been updated.

        If `file_name` is provided, update from that file instead of the
        default.
        If the object does not exist raises `ObjectNotFound`.

        :type file_name: string
        :param file_name: Use file pointed to by `file_name` as the source for
                          updating the dataset identified by `obj`

        :type create: boolean
        :param create: If True and the default dataset does not exist, create
            it first.
        """
        raise NotImplementedError()

    def get_object_url(self, obj, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False):
        """
        Return the URL for direct acces if supported, otherwise return None.

        Note: need to be careful to not bypass dataset security with this.
        """
        raise NotImplementedError()

    def get_store_usage_percent(self):
        """Return the percentage indicating how full the store is."""
        raise NotImplementedError()

    @classmethod
    def parse_xml(clazz, config_xml):
        """Parse an XML description of a configuration for this object store.

        Return a configuration dictionary (such as would correspond to the YAML configuration)
        for the object store.
        """
        raise NotImplementedError()

    @classmethod
    def from_xml(clazz, config, config_xml, **kwd):
        config_dict = clazz.parse_xml(config_xml)
        return clazz(config, config_dict, **kwd)

    def to_dict(self):
        extra_dirs = []
        for extra_dir_type, extra_dir_path in self.extra_dirs.items():
            extra_dirs.append({"type": extra_dir_type, "path": extra_dir_path})
        return {
            'config': config_to_dict(self.config),
            'extra_dirs': extra_dirs,
            'store_by': self.store_by,
            'type': self.store_type,
        }

    def _get_object_id(self, obj):
        return getattr(obj, self.store_by)


class DiskObjectStore(ObjectStore):
    """
    Standard Galaxy object store.

    Stores objects in files under a specific directory on disk.

    >>> from galaxy.util.bunch import Bunch
    >>> import tempfile
    >>> file_path=tempfile.mkdtemp()
    >>> obj = Bunch(id=1)
    >>> s = DiskObjectStore(Bunch(umask=0o077, jobs_directory=file_path, new_file_path=file_path, object_store_check_old_style=False), dict(files_dir=file_path))
    >>> s.create(obj)
    >>> s.exists(obj)
    True
    >>> assert s.get_filename(obj) == file_path + '/000/dataset_1.dat'
    """
    store_type = 'disk'

    def __init__(self, config, config_dict):
        """
        :type config: object
        :param config: An object, most likely populated from
            `galaxy/config.ini`, having the same attributes needed by
            :class:`ObjectStore` plus:

            * file_path -- Default directory to store objects to disk in.
            * umask -- the permission bits for newly created files.

        :type file_path: str
        :param file_path: Override for the `config.file_path` value.

        :type extra_dirs: dict
        :param extra_dirs: Keys are string, values are directory paths.
        """
        super(DiskObjectStore, self).__init__(config, config_dict)
        self.file_path = config_dict.get("files_dir") or config.file_path

    @classmethod
    def parse_xml(clazz, config_xml):
        extra_dirs = []
        config_dict = {}
        if config_xml is not None:
            for e in config_xml:
                if e.tag == 'files_dir':
                    config_dict["files_dir"] = e.get('path')
                else:
                    extra_dirs.append({"type": e.get('type'), "path": e.get('path')})

        config_dict["extra_dirs"] = extra_dirs
        return config_dict

    def to_dict(self):
        as_dict = super(DiskObjectStore, self).to_dict()
        as_dict["files_dir"] = self.file_path
        return as_dict

    def _get_filename(self, obj, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False):
        """
        Return the absolute path for the file corresponding to the `obj.id`.

        This is regardless of whether or not the file exists.
        """
        path = self._construct_path(obj, base_dir=base_dir, dir_only=dir_only, extra_dir=extra_dir,
                                    extra_dir_at_root=extra_dir_at_root, alt_name=alt_name,
                                    obj_dir=False, old_style=True)
        # For backward compatibility: check the old style root path first;
        # otherwise construct hashed path.
        if not os.path.exists(path):
            return self._construct_path(obj, base_dir=base_dir, dir_only=dir_only, extra_dir=extra_dir,
                                        extra_dir_at_root=extra_dir_at_root, alt_name=alt_name)

    # TODO: rename to _disk_path or something like that to avoid conflicts with
    # children that'll use the local_extra_dirs decorator, e.g. S3
    def _construct_path(self, obj, old_style=False, base_dir=None, dir_only=False, extra_dir=None, extra_dir_at_root=False, alt_name=None, obj_dir=False, **kwargs):
        """
        Construct the absolute path for accessing the object identified by `obj.id`.

        :type base_dir: string
        :param base_dir: A key in self.extra_dirs corresponding to the base
                         directory in which this object should be created, or
                         None to specify the default directory.

        :type dir_only: boolean
        :param dir_only: If True, check only the path where the file
                         identified by `obj` should be located, not the
                         dataset itself. This option applies to `extra_dir`
                         argument as well.

        :type extra_dir: string
        :param extra_dir: Append the value of this parameter to the expected
            path used to access the object identified by `obj` (e.g.,
            /files/000/<extra_dir>/dataset_10.dat).

        :type alt_name: string
        :param alt_name: Use this name as the alternative name for the returned
                         dataset rather than the default.

        :type old_style: boolean
        param old_style: This option is used for backward compatibility. If
            `True` then the composed directory structure does not include a
            hash id (e.g., /files/dataset_10.dat (old) vs.
            /files/000/dataset_10.dat (new))
        """
        base = os.path.abspath(self.extra_dirs.get(base_dir, self.file_path))
        # extra_dir should never be constructed from provided data but just
        # make sure there are no shenannigans afoot
        if extra_dir and extra_dir != os.path.normpath(extra_dir):
            log.warning('extra_dir is not normalized: %s', extra_dir)
            raise ObjectInvalid("The requested object is invalid")
        # ensure that any parent directory references in alt_name would not
        # result in a path not contained in the directory path constructed here
        if alt_name and not safe_relpath(alt_name):
            log.warning('alt_name would locate path outside dir: %s', alt_name)
            raise ObjectInvalid("The requested object is invalid")
        if old_style:
            if extra_dir is not None:
                path = os.path.join(base, extra_dir)
            else:
                path = base
        else:
            # Construct hashed path
            obj_id = self._get_object_id(obj)
            rel_path = os.path.join(*directory_hash_id(obj_id))
            # Create a subdirectory for the object ID
            if obj_dir:
                rel_path = os.path.join(rel_path, str(obj_id))
            # Optionally append extra_dir
            if extra_dir is not None:
                if extra_dir_at_root:
                    rel_path = os.path.join(extra_dir, rel_path)
                else:
                    rel_path = os.path.join(rel_path, extra_dir)
            path = os.path.join(base, rel_path)
        if not dir_only:
            path = os.path.join(path, alt_name if alt_name else "dataset_%s.dat" % obj_id)
        return os.path.abspath(path)

    def exists(self, obj, **kwargs):
        """Override `ObjectStore`'s stub and check on disk."""
        if self.check_old_style:
            path = self._construct_path(obj, old_style=True, **kwargs)
            # For backward compatibility: check root path first; otherwise
            # construct and check hashed path.
            if os.path.exists(path):
                return True
        return os.path.exists(self._construct_path(obj, **kwargs))

    def create(self, obj, **kwargs):
        """Override `ObjectStore`'s stub by creating any files and folders on disk."""
        if not self.exists(obj, **kwargs):
            path = self._construct_path(obj, **kwargs)
            dir_only = kwargs.get('dir_only', False)
            # Create directory if it does not exist
            dir = path if dir_only else os.path.dirname(path)
            safe_makedirs(dir)
            # Create the file if it does not exist
            if not dir_only:
                open(path, 'w').close()  # Should be rb?
                umask_fix_perms(path, self.config.umask, 0o666)

    def empty(self, obj, **kwargs):
        """Override `ObjectStore`'s stub by checking file size on disk."""
        return self.size(obj, **kwargs) == 0

    def size(self, obj, **kwargs):
        """Override `ObjectStore`'s stub by return file size on disk.

        Returns 0 if the object doesn't exist yet or other error.
        """
        if self.exists(obj, **kwargs):
            try:
                filepath = self.get_filename(obj, **kwargs)
                for _ in range(0, 2):
                    size = os.path.getsize(filepath)
                    if size != 0:
                        break
                    # May be legitimately 0, or there may be an issue with the FS / kernel, so we try again
                    time.sleep(0.01)
                return size
            except OSError:
                return 0
        else:
            return 0

    def delete(self, obj, entire_dir=False, **kwargs):
        """Override `ObjectStore`'s stub; delete the file or folder on disk."""
        path = self.get_filename(obj, **kwargs)
        extra_dir = kwargs.get('extra_dir', None)
        obj_dir = kwargs.get('obj_dir', False)
        try:
            if entire_dir and (extra_dir or obj_dir):
                shutil.rmtree(path)
                return True
            if self.exists(obj, **kwargs):
                os.remove(path)
                return True
        except OSError as ex:
            log.critical('%s delete error %s' % (self._get_filename(obj, **kwargs), ex))
        return False

    def get_data(self, obj, start=0, count=-1, **kwargs):
        """Override `ObjectStore`'s stub; retrieve data directly from disk."""
        data_file = open(self.get_filename(obj, **kwargs), 'r')  # Should be rb?
        data_file.seek(start)
        content = data_file.read(count)
        data_file.close()
        return content

    def get_filename(self, obj, **kwargs):
        """
        Override `ObjectStore`'s stub.

        If `object_store_check_old_style` is set to `True` in config then the
        root path is checked first.
        """
        if self.check_old_style:
            path = self._construct_path(obj, old_style=True, **kwargs)
            # For backward compatibility, check root path first; otherwise,
            # construct and return hashed path
            if os.path.exists(path):
                return path
        return self._construct_path(obj, **kwargs)

    def update_from_file(self, obj, file_name=None, create=False, **kwargs):
        """`create` parameter is not used in this implementation."""
        preserve_symlinks = kwargs.pop('preserve_symlinks', False)
        # FIXME: symlinks and the object store model may not play well together
        # these should be handled better, e.g. registering the symlink'd file
        # as an object
        if create:
            self.create(obj, **kwargs)
        if file_name and self.exists(obj, **kwargs):
            try:
                if preserve_symlinks and os.path.islink(file_name):
                    force_symlink(os.readlink(file_name), self.get_filename(obj, **kwargs))
                else:
                    path = self.get_filename(obj, **kwargs)
                    shutil.copy(file_name, path)
                    umask_fix_perms(path, self.config.umask, 0o666)
            except IOError as ex:
                log.critical('Error copying %s to %s: %s' % (file_name, self._get_filename(obj, **kwargs), ex))
                raise ex

    def get_object_url(self, obj, **kwargs):
        """
        Override `ObjectStore`'s stub.

        Returns `None`, we have no URLs.
        """
        return None

    def get_store_usage_percent(self):
        """Override `ObjectStore`'s stub by return percent storage used."""
        st = os.statvfs(self.file_path)
        return (float(st.f_blocks - st.f_bavail) / st.f_blocks) * 100


class NestedObjectStore(ObjectStore):

    """
    Base for ObjectStores that use other ObjectStores.

    Example: DistributedObjectStore, HierarchicalObjectStore
    """

    def __init__(self, config, config_xml=None):
        """Extend `ObjectStore`'s constructor."""
        super(NestedObjectStore, self).__init__(config)
        self.backends = {}

    def shutdown(self):
        """For each backend, shuts them down."""
        for store in self.backends.values():
            store.shutdown()
        super(NestedObjectStore, self).shutdown()

    def exists(self, obj, **kwargs):
        """Determine if the `obj` exists in any of the backends."""
        return self._call_method('exists', obj, False, False, **kwargs)

    def file_ready(self, obj, **kwargs):
        """Determine if the file for `obj` is ready to be used by any of the backends."""
        return self._call_method('file_ready', obj, False, False, **kwargs)

    def create(self, obj, **kwargs):
        """Create a backing file in a random backend."""
        random.choice(list(self.backends.values())).create(obj, **kwargs)

    def empty(self, obj, **kwargs):
        """For the first backend that has this `obj`, determine if it is empty."""
        return self._call_method('empty', obj, True, False, **kwargs)

    def size(self, obj, **kwargs):
        """For the first backend that has this `obj`, return its size."""
        return self._call_method('size', obj, 0, False, **kwargs)

    def delete(self, obj, **kwargs):
        """For the first backend that has this `obj`, delete it."""
        return self._call_method('delete', obj, False, False, **kwargs)

    def get_data(self, obj, **kwargs):
        """For the first backend that has this `obj`, get data from it."""
        return self._call_method('get_data', obj, ObjectNotFound, True, **kwargs)

    def get_filename(self, obj, **kwargs):
        """For the first backend that has this `obj`, get its filename."""
        return self._call_method('get_filename', obj, ObjectNotFound, True, **kwargs)

    def update_from_file(self, obj, **kwargs):
        """For the first backend that has this `obj`, update it from the given file."""
        if kwargs.get('create', False):
            self.create(obj, **kwargs)
            kwargs['create'] = False
        return self._call_method('update_from_file', obj, ObjectNotFound, True, **kwargs)

    def get_object_url(self, obj, **kwargs):
        """For the first backend that has this `obj`, get its URL."""
        return self._call_method('get_object_url', obj, None, False, **kwargs)

    def _repr_object_for_exception(self, obj):
        try:
            # there are a few objects in python that don't have __class__
            obj_id = self._get_object_id(obj)
            return '{}({}={})'.format(obj.__class__.__name__, self.store_by, obj_id)
        except AttributeError:
            return str(obj)

    def _call_method(self, method, obj, default, default_is_exception,
            **kwargs):
        """Check all children object stores for the first one with the dataset."""
        for key, store in self.backends.items():
            if store.exists(obj, **kwargs):
                return store.__getattribute__(method)(obj, **kwargs)
        if default_is_exception:
            raise default('objectstore, _call_method failed: %s on %s, kwargs: %s'
                          % (method, self._repr_object_for_exception(obj), str(kwargs)))
        else:
            return default


class DistributedObjectStore(NestedObjectStore):

    """
    ObjectStore that defers to a list of backends.

    When getting objects the first store where the object exists is used.
    When creating objects they are created in a store selected randomly, but
    with weighting.
    """
    store_type = 'distributed'

    def __init__(self, config, config_dict, fsmon=False):
        """
        :type config: object
        :param config: An object, most likely populated from
            `galaxy/config.ini`, having the same attributes needed by
            :class:`NestedObjectStore` plus:

            * distributed_object_store_config_file

        :type config_xml: ElementTree

        :type fsmon: bool
        :param fsmon: If True, monitor the file system for free space,
            removing backends when they get too full.
        """
        super(DistributedObjectStore, self).__init__(config, config_dict)

        self.backends = {}
        self.weighted_backend_ids = []
        self.original_weighted_backend_ids = []
        self.max_percent_full = {}
        self.global_max_percent_full = config_dict.get("global_max_percent_full", 0)
        random.seed()

        backends_def = config_dict["backends"]
        for backend_def in backends_def:
            backened_id = backend_def["id"]
            file_path = backend_def["files_dir"]
            extra_dirs = backend_def.get("extra_dirs", [])
            maxpctfull = backend_def.get("max_percent_full", 0)
            weight = backend_def["weight"]
            disk_config_dict = dict(files_dir=file_path, extra_dirs=extra_dirs)
            self.backends[backened_id] = DiskObjectStore(config, disk_config_dict)
            self.max_percent_full[backened_id] = maxpctfull
            log.debug("Loaded disk backend '%s' with weight %s and file_path: %s" % (backened_id, weight, file_path))

            for i in range(0, weight):
                # The simplest way to do weighting: add backend ids to a
                # sequence the number of times equalling weight, then randomly
                # choose a backend from that sequence at creation
                self.weighted_backend_ids.append(backened_id)
        self.original_weighted_backend_ids = self.weighted_backend_ids

        self.sleeper = None
        if fsmon and (self.global_max_percent_full or [_ for _ in self.max_percent_full.values() if _ != 0.0]):
            self.sleeper = Sleeper()
            self.filesystem_monitor_thread = threading.Thread(target=self.__filesystem_monitor)
            self.filesystem_monitor_thread.setDaemon(True)
            self.filesystem_monitor_thread.start()
            log.info("Filesystem space monitor started")

    @classmethod
    def parse_xml(clazz, config_xml, legacy=False):
        if legacy:
            backends_root = config_xml
        else:
            backends_root = config_xml.find('backends')

        backends = []
        config_dict = {
            'global_max_percent_full': float(backends_root.get('maxpctfull', 0)),
            'backends': backends,
        }

        for elem in [e for e in backends_root if e.tag == 'backend']:
            id = elem.get('id')
            weight = int(elem.get('weight', 1))
            maxpctfull = float(elem.get('maxpctfull', 0))
            elem_type = elem.get('type', 'disk')

            if elem_type:
                path = None
                extra_dirs = []
                for sub in elem:
                    if sub.tag == 'files_dir':
                        path = sub.get('path')
                    elif sub.tag == 'extra_dir':
                        type = sub.get('type')
                        extra_dirs.append({"type": type, "path": sub.get('path')})

                backend_dict = {
                    'id': id,
                    'weight': weight,
                    'max_percent_full': maxpctfull,
                    'files_dir': path,
                    'extra_dirs': extra_dirs,
                    'type': elem_type,
                }
                backends.append(backend_dict)

        return config_dict

    @classmethod
    def from_xml(clazz, config, config_xml, fsmon=False):
        legacy = False
        if config_xml is None:
            distributed_config = config.distributed_object_store_config_file
            assert distributed_config is not None, \
                "distributed object store ('object_store = distributed') " \
                "requires a config file, please set one in " \
                "'distributed_object_store_config_file')"

            log.debug('Loading backends for distributed object store from %s', distributed_config)
            config_xml = ElementTree.parse(distributed_config).getroot()
            legacy = True
        else:
            log.debug('Loading backends for distributed object store from %s', config_xml.get('id'))

        config_dict = clazz.parse_xml(config_xml, legacy=legacy)
        return clazz(config, config_dict, fsmon=fsmon)

    def to_dict(self):
        as_dict = super(DistributedObjectStore, self).to_dict()
        as_dict["global_max_percent_full"] = self.global_max_percent_full
        backends = []
        for backend_id, backend in self.backends.items():
            backend_as_dict = backend.to_dict()
            backend_as_dict["id"] = backend_id
            backend_as_dict["max_percent_full"] = self.max_percent_full[backend_id]
            backend_as_dict["weight"] = len([i for i in self.original_weighted_backend_ids if i == backend_id])
            backends.append(backend_as_dict)
        as_dict["backends"] = backends
        return as_dict

    def shutdown(self):
        """Shut down. Kill the free space monitor if there is one."""
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
                    new_weighted_backend_ids = [_ for _ in new_weighted_backend_ids if _ != id]
            self.weighted_backend_ids = new_weighted_backend_ids
            self.sleeper.sleep(120)  # Test free space every 2 minutes

    def create(self, obj, **kwargs):
        """The only method in which obj.object_store_id may be None."""
        if obj.object_store_id is None or not self.exists(obj, **kwargs):
            if obj.object_store_id is None or obj.object_store_id not in self.backends:
                try:
                    obj.object_store_id = random.choice(self.weighted_backend_ids)
                except IndexError:
                    raise ObjectInvalid('objectstore.create, could not generate '
                                        'obj.object_store_id: %s, kwargs: %s'
                                        % (str(obj), str(kwargs)))
                _create_object_in_session(obj)
                log.debug("Selected backend '%s' for creation of %s %s"
                          % (obj.object_store_id, obj.__class__.__name__, obj.id))
            else:
                log.debug("Using preferred backend '%s' for creation of %s %s"
                          % (obj.object_store_id, obj.__class__.__name__, obj.id))
            self.backends[obj.object_store_id].create(obj, **kwargs)

    def _call_method(self, method, obj, default, default_is_exception, **kwargs):
        object_store_id = self.__get_store_id_for(obj, **kwargs)
        if object_store_id is not None:
            return self.backends[object_store_id].__getattribute__(method)(obj, **kwargs)
        if default_is_exception:
            raise default('objectstore, _call_method failed: %s on %s, kwargs: %s'
                          % (method, self._repr_object_for_exception(obj), str(kwargs)))
        else:
            return default

    def __get_store_id_for(self, obj, **kwargs):
        if obj.object_store_id is not None:
            if obj.object_store_id in self.backends:
                return obj.object_store_id
            else:
                log.warning('The backend object store ID (%s) for %s object with ID %s is invalid'
                            % (obj.object_store_id, obj.__class__.__name__, obj.id))
        # if this instance has been switched from a non-distributed to a
        # distributed object store, or if the object's store id is invalid,
        # try to locate the object
        for id, store in self.backends.items():
            if store.exists(obj, **kwargs):
                log.warning('%s object with ID %s found in backend object store with ID %s'
                            % (obj.__class__.__name__, obj.id, id))
                obj.object_store_id = id
                _create_object_in_session(obj)
                return id
        return None


class HierarchicalObjectStore(NestedObjectStore):

    """
    ObjectStore that defers to a list of backends.

    When getting objects the first store where the object exists is used.
    When creating objects only the first store is used.
    """
    store_type = 'hierarchical'

    def __init__(self, config, config_dict, fsmon=False):
        """The default contructor. Extends `NestedObjectStore`."""
        super(HierarchicalObjectStore, self).__init__(config, config_dict)

        backends = odict()
        for order, backend_def in enumerate(config_dict["backends"]):
            backends[order] = build_object_store_from_config(config, config_dict=backend_def, fsmon=fsmon)

        self.backends = backends

    @classmethod
    def parse_xml(clazz, config_xml):
        backends_list = []
        for b in sorted(config_xml.find('backends'), key=lambda b: int(b.get('order'))):
            store_type = b.get("type")
            objectstore_class, _ = type_to_object_store_class(store_type)
            backend_config_dict = objectstore_class.parse_xml(b)
            backend_config_dict["type"] = store_type
            backends_list.append(backend_config_dict)

        return {"backends": backends_list}

    def to_dict(self):
        as_dict = super(HierarchicalObjectStore, self).to_dict()
        backends = []
        for backend_id, backend in self.backends.items():
            backend_as_dict = backend.to_dict()
            backends.append(backend_as_dict)
        as_dict["backends"] = backends
        return as_dict

    def exists(self, obj, **kwargs):
        """Check all child object stores."""
        for store in self.backends.values():
            if store.exists(obj, **kwargs):
                return True
        return False

    def create(self, obj, **kwargs):
        """Call the primary object store."""
        self.backends[0].create(obj, **kwargs)


def type_to_object_store_class(store, fsmon=False):
    objectstore_class = None
    objectstore_constructor_kwds = {}
    if store == 'disk':
        objectstore_class = DiskObjectStore
    elif store == 's3':
        from .s3 import S3ObjectStore
        objectstore_class = S3ObjectStore
    elif store == 'cloud':
        from .cloud import Cloud
        objectstore_class = Cloud
    elif store == 'swift':
        from .s3 import SwiftObjectStore
        objectstore_class = SwiftObjectStore
    elif store == 'distributed':
        objectstore_class = DistributedObjectStore
        objectstore_constructor_kwds["fsmon"] = fsmon
    elif store == 'hierarchical':
        objectstore_class = HierarchicalObjectStore
        objectstore_constructor_kwds["fsmon"] = fsmon
    elif store == 'irods':
        from .rods import IRODSObjectStore
        objectstore_class = IRODSObjectStore
    elif store == 'azure_blob':
        from .azure_blob import AzureBlobObjectStore
        objectstore_class = AzureBlobObjectStore
    elif store == 'pithos':
        from .pithos import PithosObjectStore
        objectstore_class = PithosObjectStore
    # Disable the Pulsar object store for now until it receives some attention
    # elif store == 'pulsar':
    #    from .pulsar import PulsarObjectStore
    #    return PulsarObjectStore(config=config, config_xml=config_xml)

    return objectstore_class, objectstore_constructor_kwds


def build_object_store_from_config(config, fsmon=False, config_xml=None, config_dict=None):
    """
    Invoke the appropriate object store.

    Will use the `object_store_config_file` attribute of the `config` object to
    configure a new object store from the specified XML file.

    Or you can specify the object store type in the `object_store` attribute of
    the `config` object. Currently 'disk', 's3', 'swift', 'distributed',
    'hierarchical', 'irods', and 'pulsar' are supported values.
    """
    from_object = 'xml'

    if config_xml is None and config_dict is None:
        config_file = config.object_store_config_file
        if os.path.exists(config_file):
            if config_file.endswith(".xml") or config_file.endswith(".xml.sample"):
                # This is a top level invocation of build_object_store_from_config, and
                # we have an object_store_conf.xml -- read the .xml and build
                # accordingly
                config_xml = ElementTree.parse(config.object_store_config_file).getroot()
                store = config_xml.get('type')
            else:
                with open(config_file, "rt") as f:
                    config_dict = yaml.safe_load(f)
                from_object = 'dict'
                store = config_dict.get('type')
        else:
            store = config.object_store
    elif config_xml is not None:
        store = config_xml.get('type')
    elif config_dict is not None:
        from_object = 'dict'
        store = config_dict.get('type')

    objectstore_class, objectstore_constructor_kwds = type_to_object_store_class(store, fsmon=fsmon)
    if objectstore_class is None:
        log.error("Unrecognized object store definition: {0}".format(store))

    if from_object == 'xml':
        return objectstore_class.from_xml(config=config, config_xml=config_xml, **objectstore_constructor_kwds)
    else:
        return objectstore_class(config=config, config_dict=config_dict, **objectstore_constructor_kwds)


def local_extra_dirs(func):
    """Non-local plugin decorator using local directories for the extra_dirs (job_work and temp)."""

    def wraps(self, *args, **kwargs):
        if kwargs.get('base_dir', None) is None:
            return func(self, *args, **kwargs)
        else:
            for c in self.__class__.__mro__:
                if c.__name__ == 'DiskObjectStore':
                    return getattr(c, func.__name__)(self, *args, **kwargs)
            raise Exception("Could not call DiskObjectStore's %s method, does your "
                            "Object Store plugin inherit from DiskObjectStore?"
                            % func.__name__)
    return wraps


def convert_bytes(bytes):
    """A helper function used for pretty printing disk usage."""
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


def config_to_dict(config):
    """Dict-ify the portion of a config object consumed by the ObjectStore class and its subclasses.
    """
    return {
        'object_store_check_old_style': config.object_store_check_old_style,
        'file_path': config.file_path,
        'umask': config.umask,
        'jobs_directory': config.jobs_directory,
        'new_file_path': config.new_file_path,
        'object_store_cache_path': config.object_store_cache_path,
        'gid': config.gid,
    }


def _create_object_in_session(obj):
    session = object_session(obj) if object_session is not None else None
    if session is not None:
        object_session(obj).add(obj)
        object_session(obj).flush()
    else:
        raise Exception(NO_SESSION_ERROR_MESSAGE)


class ObjectStorePopulator(object):
    """ Small helper for interacting with the object store and making sure all
    datasets from a job end up with the same object_store_id.
    """

    def __init__(self, app):
        self.object_store = app.object_store
        self.object_store_id = None

    def set_object_store_id(self, data):
        # Create an empty file immediately.  The first dataset will be
        # created in the "default" store, all others will be created in
        # the same store as the first.
        data.dataset.object_store_id = self.object_store_id
        try:
            self.object_store.create(data.dataset)
        except ObjectInvalid:
            raise Exception('Unable to create output dataset: object store is full')
        self.object_store_id = data.dataset.object_store_id  # these will be the same thing after the first output
