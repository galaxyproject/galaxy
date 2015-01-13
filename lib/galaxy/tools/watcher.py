import os.path
try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
    can_watch = True
except ImportError:
    FileSystemEventHandler = object
    can_watch = False

import logging
log = logging.getLogger( __name__ )


def get_watcher(toolbox, config):
    watch_tools = getattr(config, "watch_tools", False)
    if watch_tools:
        return ToolWatcher(toolbox)
    else:
        return NullWatcher()


class ToolWatcher(object):

    def __init__(self, toolbox):
        if not can_watch:
            raise Exception("Watchdog library unavailble, cannot watch tools.")
        self.toolbox = toolbox
        self.tool_file_ids = {}
        self.tool_dir_callbacks = {}
        self.monitored_dirs = {}
        self.observer = Observer()
        self.event_handler = ToolFileEventHandler(self)
        self.start()

    def start(self):
        self.observer.start()

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
