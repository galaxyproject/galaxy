import logging
import os.path
import threading
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
from galaxy.web.stack import register_postfork_function

log = logging.getLogger( __name__ )


def get_observer_class(config_value, default, monitor_what_str):
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
        message = "Unrecognized value for watch_tools config option: %s" % config_value
        raise Exception(message)

    if expect_observer and observer_class is None:
        message = "Watchdog library unavailable, cannot monitor %s." % monitor_what_str
        if config_value == "auto":
            log.info(message)
        else:
            raise Exception(message)

    return observer_class


def get_tool_conf_watcher(reload_callback, tool_cache=None):
    return ToolConfWatcher(reload_callback=reload_callback, tool_cache=tool_cache)


def get_tool_data_dir_watcher(tool_data_tables, config):
    config_value = getattr(config, "watch_tool_data_dir", None)
    observer_class = get_observer_class(config_value, default="False", monitor_what_str="tool-data directory")
    if observer_class is not None:
        return ToolDataWatcher(observer_class, tool_data_tables=tool_data_tables)
    else:
        return NullWatcher()


def get_tool_watcher(toolbox, config):
    config_value = getattr(config, "watch_tools", None)
    observer_class = get_observer_class(config_value, default="False", monitor_what_str="tools")

    if observer_class is not None:
        return ToolWatcher(toolbox, observer_class=observer_class)
    else:
        return NullWatcher()


class ToolConfWatcher(object):

    def __init__(self, reload_callback, tool_cache=None):
        self.paths = {}
        self.cache = tool_cache
        self._active = False
        self._lock = threading.Lock()
        self.thread = threading.Thread(target=self.check, name="ToolConfWatcher.thread")
        self.thread.daemon = True
        self.reload_callback = reload_callback

    def start(self):
        if not self._active:
            self._active = True
            register_postfork_function(self.thread.start)

    def shutdown(self):
        if self._active:
            self._active = False
            self.thread.join()

    def check(self):
        """Check for changes in self.paths or self.cache and call the event handler."""
        hashes = { key: None for key in self.paths.keys() }
        while self._active:
            do_reload = False
            with self._lock:
                paths = list(self.paths.keys())
            for path in paths:
                if not os.path.exists(path):
                    continue
                mod_time = self.paths[path]
                if not hashes.get(path, None):
                    hashes[path] = md5_hash_file(path)
                new_mod_time = None
                if os.path.exists(path):
                    new_mod_time = os.path.getmtime(path)
                if new_mod_time > mod_time:
                    new_hash = md5_hash_file(path)
                    if hashes[path] != new_hash:
                        self.paths[path] = new_mod_time
                        hashes[path] = new_hash
                        log.debug("The file '%s' has changes.", path)
                        do_reload = True
            if not do_reload and self.cache:
                removed_ids = self.cache.cleanup()
                if removed_ids:
                    do_reload = True
            if do_reload:
                self.reload_callback()
            time.sleep(1)

    def monitor(self, path):
        mod_time = None
        if os.path.exists(path):
            mod_time = os.path.getmtime(path)
        with self._lock:
            self.paths[path] = mod_time
        if not self._active:
            self.start()

    def watch_file(self, tool_conf_file):
        self.monitor(tool_conf_file)
        if not self._active:
            self.start()


class NullToolConfWatcher(object):

    def start(self):
        pass

    def shutdown(self):
        pass

    def monitor(self, conf_path):
        pass

    def watch_file(self, tool_file, tool_id):
        pass


class ToolWatcher(object):

    def __init__(self, toolbox, observer_class):
        self.toolbox = toolbox
        self.tool_file_ids = {}
        self.tool_dir_callbacks = {}
        self.monitored_dirs = {}
        self.observer = observer_class()
        self.event_handler = ToolFileEventHandler(self)
        self.start()

    def start(self):
        register_postfork_function(self.observer.start)

    def shutdown(self):
        self.observer.stop()
        self.observer.join()

    def monitor(self, dir):
        self.observer.schedule(self.event_handler, dir, recursive=False)

    def watch_file(self, tool_file, tool_id):
        tool_file = os.path.abspath( tool_file )
        self.tool_file_ids[tool_file] = tool_id
        tool_dir = os.path.dirname( tool_file )
        if tool_dir not in self.monitored_dirs:
            self.monitored_dirs[ tool_dir ] = tool_dir
            self.monitor( tool_dir )

    def watch_directory(self, tool_dir, callback):
        tool_dir = os.path.abspath( tool_dir )
        self.tool_dir_callbacks[tool_dir] = callback
        if tool_dir not in self.monitored_dirs:
            self.monitored_dirs[ tool_dir ] = tool_dir
            self.monitor( tool_dir )


class ToolDataWatcher(object):

    def __init__(self, observer_class, tool_data_tables):
        self.tool_data_tables = tool_data_tables
        self.monitored_dirs = {}
        self.path_hash = {}
        self.observer = observer_class()
        self.event_handler = LocFileEventHandler(self)
        self.start()

    def start(self):
        register_postfork_function(self.observer.start)

    def shutdown(self):
        self.observer.stop()
        self.observer.join()

    def monitor(self, dir):
        self.observer.schedule(self.event_handler, dir, recursive=True)

    def watch_directory(self, tool_data_dir):
        tool_data_dir = os.path.abspath( tool_data_dir )
        if tool_data_dir not in self.monitored_dirs:
            self.monitored_dirs[ tool_data_dir ] = tool_data_dir
            self.monitor( tool_data_dir )


class LocFileEventHandler(FileSystemEventHandler):

    def __init__(self, loc_watcher):
        self.loc_watcher = loc_watcher

    def on_any_event(self, event):
        self._handle(event)

    def _handle(self, event):
        # modified events will only have src path, move events will
        # have dest_path and src_path but we only care about dest. So
        # look at dest if it exists else use src.
        path = getattr( event, 'dest_path', None ) or event.src_path
        path = os.path.abspath( path )
        if path.endswith(".loc"):
            cur_hash = md5_hash_file(path)
            if self.loc_watcher.path_hash.get(path) == cur_hash:
                return
            else:
                self.loc_watcher.path_hash[path] = cur_hash
                self.loc_watcher.tool_data_tables.reload_tables(path=path)


class ToolFileEventHandler(FileSystemEventHandler):

    def __init__(self, tool_watcher):
        self.tool_watcher = tool_watcher

    def on_any_event(self, event):
        self._handle(event)

    def _handle(self, event):
        # modified events will only have src path, move events will
        # have dest_path and src_path but we only care about dest. So
        # look at dest if it exists else use src.
        path = getattr( event, 'dest_path', None ) or event.src_path
        path = os.path.abspath( path )
        tool_id = self.tool_watcher.tool_file_ids.get( path, None )
        if tool_id:
            try:
                self.tool_watcher.toolbox.reload_tool_by_id(tool_id)
            except Exception:
                pass
        elif path.endswith(".xml"):
            directory = os.path.dirname( path )
            dir_callback = self.tool_watcher.tool_dir_callbacks.get( directory, None )
            if dir_callback:
                tool_file = event.src_path
                tool_id = dir_callback( tool_file )
                if tool_id:
                    self.tool_watcher.tool_file_ids[ tool_file ] = tool_id


class NullWatcher(object):

    def start(self):
        pass

    def shutdown(self):
        pass

    def watch_file(self, tool_file, tool_id):
        pass

    def watch_directory(self, tool_dir, callback=None):
        pass
