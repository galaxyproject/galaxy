from functools import wraps
from threading import Lock, Event
from weakref import WeakValueDictionary
from os import walk
from os import curdir
from os import listdir
from os import makedirs
from os import unlink
from os.path import relpath
from os.path import join
from os.path import abspath
from os.path import exists
from errno import ENOENT, EEXIST
import os.path
import hashlib
import shutil
import json
import sys

from six import binary_type

# Variant of base64 compat layer inspired by BSD code from Bcfg2
# https://github.com/Bcfg2/bcfg2/blob/maint/src/lib/Bcfg2/Compat.py
if sys.version_info >= (3, 0):
    from base64 import b64encode as _b64encode, b64decode as _b64decode

    @wraps(_b64encode)
    def b64encode(val, **kwargs):
        try:
            return _b64encode(val, **kwargs)
        except TypeError:
            return _b64encode(val.encode('UTF-8'), **kwargs).decode('UTF-8')

    @wraps(_b64decode)
    def b64decode(val, **kwargs):
        return _b64decode(val.encode('UTF-8'), **kwargs).decode('UTF-8')
else:
    from base64 import b64encode, b64decode


def unique_path_prefix(path):
    m = hashlib.md5()
    m.update(path.encode('utf-8'))
    return m.hexdigest()


def copy(source, destination):
    """ Copy file from source to destination if needed (skip if source
    is destination).
    """
    source = os.path.abspath(source)
    destination = os.path.abspath(destination)
    if source != destination:
        shutil.copyfile(source, destination)


def ensure_directory(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


def directory_files(directory):
    """

    >>> from tempfile import mkdtemp
    >>> from shutil import rmtree
    >>> from os.path import join
    >>> from os import makedirs
    >>> tempdir = mkdtemp()
    >>> with open(join(tempdir, "moo"), "w") as f: pass
    >>> directory_files(tempdir)
    ['moo']
    >>> subdir = join(tempdir, "cow", "sub1")
    >>> makedirs(subdir)
    >>> with open(join(subdir, "subfile1"), "w") as f: pass
    >>> with open(join(subdir, "subfile2"), "w") as f: pass
    >>> sorted(directory_files(tempdir))
    ['cow/sub1/subfile1', 'cow/sub1/subfile2', 'moo']
    >>> rmtree(tempdir)
    """
    contents = []
    for path, _, files in walk(directory):
        relative_path = relpath(path, directory)
        for name in files:
            # Return file1.txt, dataset_1_files/image.png, etc... don't
            # include . in path.
            if relative_path != curdir:
                contents.append(join(relative_path, name))
            else:
                contents.append(name)
    return contents


def filter_destination_params(destination_params, prefix):
    destination_params = destination_params or {}
    return dict([(key[len(prefix):], destination_params[key])
                 for key in destination_params
                 if key.startswith(prefix)])


def to_base64_json(data):
    """

    >>> enc = to_base64_json(dict(a=5))
    >>> dec = from_base64_json(enc)
    >>> dec["a"]
    5
    """
    dumped = json_dumps(data)
    return b64encode(dumped)


def from_base64_json(data):
    return json.loads(b64decode(data))


class PathHelper(object):
    '''

    >>> import posixpath
    >>> # Forcing local path to posixpath because Pulsar designed to be used with
    >>> # posix client.
    >>> posix_path_helper = PathHelper("/", local_path_module=posixpath)
    >>> windows_slash = "\\\\"
    >>> len(windows_slash)
    1
    >>> nt_path_helper = PathHelper(windows_slash, local_path_module=posixpath)
    >>> posix_path_helper.remote_name("moo/cow")
    'moo/cow'
    >>> nt_path_helper.remote_name("moo/cow")
    'moo\\\\cow'
    >>> posix_path_helper.local_name("moo/cow")
    'moo/cow'
    >>> nt_path_helper.local_name("moo\\\\cow")
    'moo/cow'
    >>> posix_path_helper.from_posix_with_new_base("/galaxy/data/bowtie/hg19.fa", "/galaxy/data/", "/work/galaxy/data")
    '/work/galaxy/data/bowtie/hg19.fa'
    >>> posix_path_helper.from_posix_with_new_base("/galaxy/data/bowtie/hg19.fa", "/galaxy/data", "/work/galaxy/data")
    '/work/galaxy/data/bowtie/hg19.fa'
    >>> posix_path_helper.from_posix_with_new_base("/galaxy/data/bowtie/hg19.fa", "/galaxy/data", "/work/galaxy/data/")
    '/work/galaxy/data/bowtie/hg19.fa'
    '''

    def __init__(self, separator, local_path_module=os.path):
        self.separator = separator
        self.local_join = local_path_module.join
        self.local_sep = local_path_module.sep

    def remote_name(self, local_name):
        return self.remote_join(*local_name.split(self.local_sep))

    def local_name(self, remote_name):
        return self.local_join(*remote_name.split(self.separator))

    def remote_join(self, *args):
        return self.separator.join(args)

    def from_posix_with_new_base(self, posix_path, old_base, new_base):
        # TODO: Test with new_base as a windows path against nt_path_helper.
        if old_base.endswith("/"):
            old_base = old_base[:-1]
        if not posix_path.startswith(old_base):
            message_template = "Cannot compute new path for file %s, does not start with %s."
            message = message_template % (posix_path, old_base)
            raise Exception(message)
        stripped_path = posix_path[len(old_base):]
        while stripped_path.startswith("/"):
            stripped_path = stripped_path[1:]
        path_parts = stripped_path.split(self.separator)
        if new_base.endswith(self.separator):
            new_base = new_base[:-len(self.separator)]
        return self.remote_join(new_base, *path_parts)


class TransferEventManager(object):

    def __init__(self):
        self.events = WeakValueDictionary(dict())
        self.events_lock = Lock()

    def acquire_event(self, path, force_clear=False):
        with self.events_lock:
            if path in self.events:
                event_holder = self.events[path]
            else:
                event_holder = EventHolder(Event(), path, self)
                self.events[path] = event_holder
        if force_clear:
            event_holder.event.clear()
        return event_holder


class EventHolder(object):

    def __init__(self, event, path, condition_manager):
        self.event = event
        self.path = path
        self.condition_manager = condition_manager
        self.failed = False

    def release(self):
        self.event.set()

    def fail(self):
        self.failed = True


def json_loads(obj):
    if isinstance(obj, binary_type):
        obj = obj.decode("utf-8")
    return json.loads(obj)


def json_dumps(obj):
    if isinstance(obj, binary_type):
        obj = obj.decode("utf-8")
    return json.dumps(obj, cls=ClientJsonEncoder)


class ClientJsonEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, binary_type):
            return obj.decode("utf-8")
        return json.JSONEncoder.default(self, obj)


class MessageQueueUUIDStore(object):
    """Persistent dict-like object for persisting message queue UUIDs that are
    awaiting acknowledgement or that have been operated on.
    """

    def __init__(self, persistence_directory, subdirs=None):
        if subdirs is None:
            subdirs = ['acknowledge_uuids']
        self.__store = abspath(join(persistence_directory, *subdirs))
        try:
            makedirs(self.__store)
        except (OSError, IOError) as exc:
            if exc.errno != EEXIST:
                raise

    def __path(self, item):
        return join(self.__store, item)

    def __contains__(self, item):
        return exists(self.__path(item))

    def __setitem__(self, key, value):
        open(self.__path(key), 'w').write(json.dumps(value))

    def __getitem__(self, key):
        return json.loads(open(self.__path(key)).read())

    def __delitem__(self, key):
        try:
            unlink(self.__path(key))
        except (OSError, IOError) as exc:
            if exc.errno == ENOENT:
                raise KeyError(key)
            raise

    def keys(self):
        return iter(listdir(self.__store))

    def get_time(self, key):
        try:
            return os.stat(self.__path(key)).st_mtime
        except (OSError, IOError) as exc:
            if exc.errno == ENOENT:
                raise KeyError(key)
            raise

    def set_time(self, key):
        try:
            os.utime(self.__path(key), None)
        except (OSError, IOError) as exc:
            if exc.errno == ENOENT:
                raise KeyError(key)
            raise
