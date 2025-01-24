import logging
import os.path
import threading

try:
    from watchdog.events import FileSystemEventHandler
except ImportError:
    FileSystemEventHandler = object  # type:ignore[assignment, misc, unused-ignore]

from galaxy.util.hash_util import md5_hash_file
from galaxy.util.watcher import (
    BaseWatcher,
    get_observer_class,
    NullWatcher,
)

log = logging.getLogger(__name__)


def get_tool_conf_watcher(reload_callback, tool_cache=None):
    return ToolConfWatcher(reload_callback=reload_callback, tool_cache=tool_cache)


def get_tool_watcher(toolbox, config):
    config_name = "watch_tools"
    config_value = getattr(config, config_name, None)
    observer_class = get_observer_class(config_name, config_value, default="False", monitor_what_str="tools")
    if observer_class is not None:
        return ToolWatcher(observer_class=observer_class, event_handler_class=ToolFileEventHandler, toolbox=toolbox)
    else:
        return NullWatcher()


class ToolFileEventHandler(FileSystemEventHandler):
    def __init__(self, tool_watcher):
        self.tool_watcher = tool_watcher

    def on_any_event(self, event):
        self._handle(event)

    def _handle(self, event):
        # modified events will only have src path, move events will
        # have dest_path and src_path but we only care about dest. So
        # look at dest if it exists else use src.
        path = getattr(event, "dest_path", None) or event.src_path
        path = os.path.abspath(path)
        tool_id = self.tool_watcher.tool_file_ids.get(path, None)
        if tool_id:
            try:
                self.tool_watcher.toolbox.reload_tool_by_id(tool_id)
            except Exception:
                pass
        elif path.endswith(".xml"):
            directory = os.path.dirname(path)
            dir_callback = self.tool_watcher.tool_dir_callbacks.get(directory, None)
            if dir_callback:
                tool_file = event.src_path
                tool_id = dir_callback(tool_file)
                if tool_id:
                    self.tool_watcher.tool_file_ids[tool_file] = tool_id


class ToolConfWatcher:
    def __init__(self, reload_callback, tool_cache=None):
        self.paths = {}
        self.cache = tool_cache
        self._active = False
        self._lock = threading.Lock()
        self.thread = None

        self.reload_callback = reload_callback

    def start(self):
        if not self._active:
            self._active = True
            if self.thread is None:
                self.exit = threading.Event()
                self.thread = threading.Thread(target=self.check)
                self.thread.daemon = True
                self.thread.start()

    def shutdown(self):
        if self._active:
            self._active = False
            if self.thread.is_alive():
                self.exit.set()
                self.thread.join()
            self.thread = None
            self.exit = None

    def check(self):
        """Check for changes in self.paths or self.cache and call the event handler."""
        hashes = {}
        if self.cache:
            self.cache.assert_hashes_initialized()
        while self._active and not self.exit.is_set():
            do_reload = False
            drop_on_next_loop = set()
            drop_now = set()
            with self._lock:
                paths = list(self.paths.keys())
            for path in paths:
                try:
                    if not os.path.exists(path):
                        continue
                    mod_time = self.paths[path]
                    if not hashes.get(path, None):
                        hash = md5_hash_file(path)
                        if hash:
                            hashes[path] = md5_hash_file(path)
                        else:
                            continue
                    new_mod_time = os.path.getmtime(path)
                    # mod_time can be None if a non-required config was just created
                    if not mod_time:
                        self.paths[path] = new_mod_time
                        log.debug("The file '%s' has been created.", path)
                        do_reload = True
                    elif new_mod_time > mod_time:
                        new_hash = md5_hash_file(path)
                        if hashes[path] != new_hash:
                            self.paths[path] = new_mod_time
                            hashes[path] = new_hash
                            log.debug("The file '%s' has changes.", path)
                            do_reload = True
                except OSError:
                    # in rare cases `path` may be deleted between `os.path.exists` calls
                    # and reading the file from the filesystem. We do not want the watcher
                    # thread to die in these cases.
                    if path in drop_now:
                        log.warning("'%s' could not be read, removing from watched files", path)
                        del self.paths[path]
                        if path in hashes:
                            del hashes[path]
                    else:
                        log.debug("'%s could not be read", path)
                        drop_on_next_loop.add(path)
                    if self.cache:
                        self.cache.cleanup()
                    do_reload = True
            if not do_reload and self.cache:
                removed_ids = self.cache.cleanup()
                if removed_ids:
                    do_reload = True
            if do_reload:
                self.reload_callback()
            drop_now = drop_on_next_loop
            drop_on_next_loop = set()
            self.exit.wait(1)

    def monitor(self, path):
        mod_time = None
        if os.path.exists(path):
            mod_time = os.path.getmtime(path)
        with self._lock:
            self.paths[path] = mod_time

    def watch_file(self, tool_conf_file):
        self.monitor(tool_conf_file)


class ToolWatcher(BaseWatcher):
    def __init__(self, observer_class, event_handler_class, toolbox):
        super().__init__(observer_class, event_handler_class)
        self.toolbox = toolbox
        self.tool_file_ids = {}
        self.tool_dir_callbacks = {}

    def watch_file(self, tool_file, tool_id):
        tool_file = os.path.abspath(tool_file)
        self.tool_file_ids[tool_file] = tool_id
        tool_dir = os.path.dirname(tool_file)
        if tool_dir not in self.monitored_dirs:
            self.monitor(tool_dir)

    def watch_directory(self, tool_dir, callback):
        tool_dir = os.path.abspath(tool_dir)
        self.tool_dir_callbacks[tool_dir] = callback
        if tool_dir not in self.monitored_dirs:
            self.monitor(tool_dir)
