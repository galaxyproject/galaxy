from threading import Lock, Event
from weakref import WeakValueDictionary
from os import walk
from os import curdir
from os.path import relpath
from os.path import join
import os.path
import hashlib


def unique_path_prefix(path):
    m = hashlib.md5()
    m.update(path)
    return m.hexdigest()


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


class PathHelper(object):
    '''

    >>> import posixpath
    >>> # Forcing local path to posixpath because LWR designed to be used with
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
