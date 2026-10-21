# TODO: this is largely copied from galaxy.tool_util.toolbox.galaxy and generalized, the tool-oriented watchers in that
# module should probably be updated to use this where possible


import logging
import os.path
import threading
import time
from typing import (
    Any,
)

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
    from watchdog.observers.polling import PollingObserver

    can_watch = True
except ImportError:
    Observer = None  # type: ignore[assignment, unused-ignore]
    FileSystemEventHandler = object  # type: ignore[assignment,misc, unused-ignore]
    PollingObserver = None  # type: ignore[assignment, misc, unused-ignore]
    can_watch = False

from galaxy.util.hash_util import md5_hash_file

log = logging.getLogger(__name__)


def get_observer_class(config_name, config_value, default, monitor_what_str):
    """ """
    config_value = config_value or default
    config_value = str(config_value).lower()
    if config_value in ("true", "yes", "on", "auto"):
        expect_observer = True
        observer_class = Observer
    elif config_value == "polling":
        expect_observer = True
        observer_class = PollingObserver
    elif config_value in ("false", "no", "off"):
        expect_observer = False
        observer_class = None
    else:
        message = f"Unrecognized value for {config_name} config option: {config_value}"
        raise Exception(message)

    if expect_observer and observer_class is None:
        message = f"Watchdog library unavailable, cannot monitor {monitor_what_str}."
        if config_value == "auto":
            log.info(message)
        else:
            raise Exception(message)

    return observer_class


def get_watcher(
    config, config_name, default="False", monitor_what_str=None, watcher_class=None, event_handler_class=None, **kwargs
):
    config_value = getattr(config, config_name, None)
    observer_class = get_observer_class(config_name, config_value, default=default, monitor_what_str=monitor_what_str)
    if observer_class is not None:
        watcher_class = watcher_class or Watcher
        event_handler_class = event_handler_class or EventHandler
        return watcher_class(observer_class, event_handler_class, **kwargs)
    else:
        return NullWatcher()


class _SharedObserver:
    """An observer shared by all watchers in this process that use the same observer class.

    Every watched directory costs a native observer an inotify instance and watch (on Linux), and every
    observer costs a thread, so giving each watcher (or, as TPV does, each watched file) its own observer
    quickly exhausts ``fs.inotify.max_user_instances`` and ``fs.inotify.max_user_watches`` on hosts running
    many Galaxy processes. A shared observer creates one emitter per watched directory, no matter how many
    watchers schedule a handler for it, and removes the emitter once the last of those handlers is gone.
    """

    def __init__(self, observer_class):
        self.observer_class = observer_class
        self.observer = observer_class()
        # watchdog holds this (reentrant) lock while dispatching events, so a callback can register new
        # watches; using it to guard our bookkeeping too avoids lock-order inversions with the dispatch thread.
        self.lock = self.observer._lock
        self.users = 0
        self.watch_users = {}

    def schedule(self, event_handler, dir_path, recursive):
        with self.lock:
            watch = self.observer.schedule(event_handler, dir_path, recursive=recursive)
            self.watch_users[watch] = self.watch_users.get(watch, 0) + 1
            return watch

    def unschedule(self, event_handler, watch):
        with self.lock:
            self.observer.remove_handler_for_watch(event_handler, watch)
            self.watch_users[watch] -= 1
            if not self.watch_users[watch]:
                del self.watch_users[watch]
                self.observer.unschedule(watch)


_shared_observers: dict[Any, _SharedObserver] = {}
_shared_observers_lock = threading.Lock()


def _acquire_observer(observer_class):
    with _shared_observers_lock:
        shared = _shared_observers.get(observer_class)
        if shared is None:
            shared = _shared_observers[observer_class] = _SharedObserver(observer_class)
            shared.observer.start()
        shared.users += 1
        return shared


def _release_observer(shared):
    with _shared_observers_lock:
        shared.users -= 1
        if shared.users:
            return
        del _shared_observers[shared.observer_class]
    shared.observer.stop()
    shared.observer.join()


class _ExceptionLoggingEventHandler(FileSystemEventHandler):
    """Dispatch events to a watcher's current event handler, logging instead of raising exceptions.

    An exception escaping an event handler terminates the observer thread, which would stop
    every watcher sharing the observer.
    """

    def __init__(self, watcher):
        self.watcher = watcher

    def dispatch(self, event):
        try:
            self.watcher.event_handler.dispatch(event)
        except Exception:
            log.exception("Error handling file system event %s", event)


class BaseWatcher:
    def __init__(self, observer_class, event_handler_class, **kwargs):
        self.observer = None
        self.observer_class = observer_class
        self.event_handler = event_handler_class(self)
        self.monitored_dirs = {}
        self._shared_observer: _SharedObserver | None = None
        self._dispatch_handler = _ExceptionLoggingEventHandler(self)
        self._watches = {}

    def start(self):
        if self._shared_observer is None:
            self._shared_observer = _acquire_observer(self.observer_class)
            self.observer = self._shared_observer.observer
            self.resume_watching()

    def monitor(self, dir_path, recursive=False):
        self.monitored_dirs[dir_path] = recursive
        shared = self._shared_observer
        if shared is None:
            return
        with shared.lock:
            if self._shared_observer is not shared:
                # shut down while we were waiting for the lock
                return
            watch = self._watches.get(dir_path)
            if watch is not None:
                if watch.is_recursive == recursive:
                    return
                shared.unschedule(self._dispatch_handler, watch)
                del self._watches[dir_path]
            self._watches[dir_path] = shared.schedule(self._dispatch_handler, dir_path, recursive)

    def resume_watching(self):
        for dir_path, recursive in list(self.monitored_dirs.items()):
            self.monitor(dir_path, recursive)

    def shutdown(self):
        shared = self._shared_observer
        if shared is None:
            return
        with shared.lock:
            if self._shared_observer is not shared:
                # concurrently shut down by another thread
                return
            for watch in self._watches.values():
                shared.unschedule(self._dispatch_handler, watch)
            self._watches.clear()
            self._shared_observer = None
            self.observer = None
        _release_observer(shared)


class Watcher(BaseWatcher):
    def __init__(self, observer_class, event_handler_class, **kwargs):
        super().__init__(observer_class, event_handler_class, **kwargs)
        self.path_hash = {}
        self.file_callbacks = {}
        self.dir_callbacks = {}
        self.ignore_extensions = {}
        self.require_extensions = {}
        self.event_handler = event_handler_class(self)

    def watch_file(self, file_path, callback=None):
        file_path = os.path.abspath(file_path)
        dir_path = os.path.dirname(file_path)
        if callback is not None:
            self.file_callbacks[file_path] = callback
        if dir_path not in self.monitored_dirs:
            self.monitor(dir_path)
        log.debug("Watching for changes to file: %s", file_path)

    def watch_directory(
        self, dir_path, callback=None, recursive=False, ignore_extensions=None, require_extensions=None
    ):
        dir_path = os.path.abspath(dir_path)
        if dir_path not in self.monitored_dirs:
            if callback is not None:
                self.dir_callbacks[dir_path] = callback
            if ignore_extensions:
                self.ignore_extensions[dir_path] = ignore_extensions
            if require_extensions:
                self.require_extensions[dir_path] = require_extensions
            self.monitor(dir_path, recursive=recursive)
            log.debug("Watching for changes in directory%s: %s", " (recursively)" if recursive else "", dir_path)


class EventHandler(FileSystemEventHandler):
    def __init__(self, watcher):
        self.watcher = watcher

    # this effectively excludes on_opened and on_closed
    def on_moved(self, event):
        self._handle(event)

    def on_created(self, event):
        self._handle(event)

    def on_deleted(self, event):
        self._handle(event)

    def on_modified(self, event):
        self._handle(event)

    def _extension_check(self, key, path):
        if required_extensions := self.watcher.require_extensions.get(key):
            return any(filter(path.endswith, required_extensions))
        return not any(filter(path.endswith, self.watcher.ignore_extensions.get(key, [])))

    def _handle(self, event):
        # modified events will only have src path, move events will
        # have dest_path and src_path but we only care about dest. So
        # look at dest if it exists else use src.
        path = getattr(event, "dest_path", None) or event.src_path
        path = os.path.abspath(path)
        callback = self.watcher.file_callbacks.get(path)
        if os.path.basename(path).startswith("."):
            return
        if callback:
            ext_ok = self._extension_check(path, path)
        else:
            # reversed sort for getting the most specific dir first
            for key in sorted(self.watcher.dir_callbacks.keys(), reverse=True):
                if os.path.commonprefix([path, key]) == key:
                    callback = self.watcher.dir_callbacks[key]
                    ext_ok = self._extension_check(key, path)
                    break
        if not callback or not ext_ok:
            return
        if cur_hash := md5_hash_file(path):
            if self.watcher.path_hash.get(path) == cur_hash:
                return
            else:
                time.sleep(0.5)
                if cur_hash != md5_hash_file(path):
                    # We're still modifying the file, it'll be picked up later
                    return
                self.watcher.path_hash[path] = cur_hash
                callback(path=path)


class NullWatcher:
    def start(self):
        pass

    def shutdown(self):
        pass

    def watch_file(self, *args, **kwargs):
        pass

    def watch_directory(self, *args, **kwargs):
        pass
