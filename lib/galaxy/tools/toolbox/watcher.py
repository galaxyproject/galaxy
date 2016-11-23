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
from galaxy.util.postfork import register_postfork_function

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


def get_tool_conf_watcher(reload_callback):
    return ToolConfWatcher(reload_callback)


def get_tool_watcher(toolbox, config):
    config_value = getattr(config, "watch_tools", None)
    observer_class = get_observer_class(config_value, default="False", monitor_what_str="tools")

    if observer_class is not None:
        return ToolWatcher(toolbox, observer_class=observer_class)
    else:
        return NullWatcher()


class ToolConfWatcher(object):

    def __init__(self, reload_callback):
        self.paths = {}
        self._active = False
        self._lock = threading.Lock()
        self.thread = threading.Thread(target=self.check, name="ToolConfWatcher.thread")
        self.thread.daemon = True
        self.event_handler = ToolConfFileEventHandler(reload_callback)

    def start(self):
        if not self._active:
            self._active = True
            register_postfork_function(self.thread.start)

    def shutdown(self):
        if self._active:
            self._active = False
            self.thread.join()

    def check(self):
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
                    new_mod_time = time.ctime(os.path.getmtime(path))
                if new_mod_time != mod_time:
                    if hashes[path] != md5_hash_file(path):
                        self.paths[path] = new_mod_time
                        log.debug("The file '%s' has changes.", path)
                        do_reload = True

            if do_reload:
                with self._lock:
                    t = threading.Thread(target=self.event_handler.on_any_event)
                    t.daemon = True
                    t.start()
            time.sleep(1)

    def monitor(self, path):
        mod_time = None
        if os.path.exists(path):
            mod_time = time.ctime(os.path.getmtime(path))
        with self._lock:
            self.paths[path] = mod_time
        self.start()

    def watch_file(self, tool_conf_file):
        self.monitor(tool_conf_file)
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


class ToolConfFileEventHandler(FileSystemEventHandler):

    def __init__(self, reload_callback):
        self.reload_callback = reload_callback

    def on_any_event(self, event=None):
        self._handle(event)

    def _handle(self, event):
        self.reload_callback()


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

    def watch_directory(self, tool_dir, callback):
        pass
