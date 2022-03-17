# TODO: this is largely copied from galaxy.tool_util.toolbox.galaxy and generalized, the tool-oriented watchers in that
# module should probably be updated to use this where possible


import logging
import os.path
import time


try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
    from watchdog.observers.polling import PollingObserver
    can_watch = True
except ImportError:
    Observer = None
    FileSystemEventHandler = object
    PollingObserver = None
    can_watch = False

from galaxy.util.hash_util import md5_hash_file

log = logging.getLogger(__name__)


def get_observer_class(config_name, config_value, default, monitor_what_str):
    """
    """
    config_value = config_value or default
    config_value = str(config_value).lower()
    if config_value in ("true", "yes", "on", "auto"):
        expect_observer = True
        observer_class = Observer
    elif config_value == "polling":
        expect_observer = True
        observer_class = PollingObserver
    elif config_value in ('false', 'no', 'off'):
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


def get_watcher(config, config_name, default="False", monitor_what_str=None, watcher_class=None,
                event_handler_class=None, **kwargs):
    config_value = getattr(config, config_name, None)
    observer_class = get_observer_class(config_name, config_value, default=default, monitor_what_str=monitor_what_str)
    if observer_class is not None:
        watcher_class = watcher_class or Watcher
        event_handler_class = event_handler_class or EventHandler
        return watcher_class(observer_class, event_handler_class, **kwargs)
    else:
        return NullWatcher()


class BaseWatcher:

    def __init__(self, observer_class, event_handler_class, **kwargs):
        self.observer = None
        self.observer_class = observer_class
        self.event_handler = event_handler_class(self)
        self.monitored_dirs = {}

    def start(self):
        if self.observer is None:
            self.observer = self.observer_class()
            self.observer.start()
            self.resume_watching()

    def monitor(self, dir_path, recursive=False):
        self.monitored_dirs[dir_path] = recursive
        if self.observer is not None:
            self.observer.schedule(self.event_handler, dir_path, recursive=recursive)

    def resume_watching(self):
        for dir_path, recursive in self.monitored_dirs.items():
            self.monitor(dir_path, recursive)

    def shutdown(self):
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None


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
        if dir_path not in self.monitored_dirs:
            if callback is not None:
                self.file_callbacks[file_path] = callback
            self.monitor(dir_path)
            log.debug("Watching for changes to file: %s", file_path)

    def watch_directory(self, dir_path, callback=None, recursive=False, ignore_extensions=None, require_extensions=None):
        dir_path = os.path.abspath(dir_path)
        if dir_path not in self.monitored_dirs:
            if callback is not None:
                self.dir_callbacks[dir_path] = callback
            if ignore_extensions:
                self.ignore_extensions[dir_path] = ignore_extensions
            if require_extensions:
                self.require_extensions[dir_path] = require_extensions
            self.monitor(dir_path, recursive=recursive)
            log.debug("Watching for changes in directory%s: %s", ' (recursively)' if recursive else '', dir_path)


class EventHandler(FileSystemEventHandler):

    def __init__(self, watcher):
        self.watcher = watcher

    def on_any_event(self, event):
        self._handle(event)

    def _extension_check(self, key, path):
        required_extensions = self.watcher.require_extensions.get(key)
        if required_extensions:
            return any(filter(path.endswith, required_extensions))
        return not any(filter(path.endswith, self.watcher.ignore_extensions.get(key, [])))

    def _handle(self, event):
        # modified events will only have src path, move events will
        # have dest_path and src_path but we only care about dest. So
        # look at dest if it exists else use src.
        path = getattr(event, 'dest_path', None) or event.src_path
        path = os.path.abspath(path)
        callback = self.watcher.file_callbacks.get(path)
        if os.path.basename(path).startswith('.'):
            return
        if callback:
            ext_ok = self._extension_check(path, path)
        else:
            # reversed sort for getting the most specific dir first
            for key in reversed(sorted(self.watcher.dir_callbacks.keys())):
                if os.path.commonprefix([path, key]) == key:
                    callback = self.watcher.dir_callbacks[key]
                    ext_ok = self._extension_check(key, path)
                    break
        if not callback or not ext_ok:
            return
        cur_hash = md5_hash_file(path)
        if cur_hash:
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
