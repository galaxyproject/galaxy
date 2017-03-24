import os
import time

from galaxy.util.hash_util import md5_hash_file


class ToolCache(object):
    """
    Cache tool definitions to allow quickly reloading the whole
    toolbox.
    """

    def __init__(self):
        self._hash_by_tool_paths = {}
        self._tools_by_path = {}
        self._tool_paths_by_id = {}
        self._mod_time_by_path = {}

    def cleanup(self):
        """
        Remove uninstalled tools from tool cache if they are not on disk anymore or if their content has changed.

        Returns list of tool_ids that have been removed.
        """
        paths_to_cleanup = {path: tool.all_ids for path, tool in self._tools_by_path.items() if self._should_cleanup(path)}
        removed_tool_ids = []
        for config_filename, tool_ids in paths_to_cleanup.items():
            removed_tool_ids.extend(tool_ids)
            del self._hash_by_tool_paths[config_filename]
            del self._tools_by_path[config_filename]
            for tool_id in tool_ids:
                if tool_id in self._tool_paths_by_id:
                    del self._tool_paths_by_id[tool_id]
        return removed_tool_ids

    def _should_cleanup(self, config_filename):
        """Return True of `config_filename` does not exist or if modtime and hash have changes, else return False."""
        if not os.path.exists(config_filename):
            return True
        new_mtime = time.ctime(os.path.getmtime(config_filename))
        if self._mod_time_by_path[config_filename] != new_mtime:
            if md5_hash_file(config_filename) != self._hash_by_tool_paths[config_filename]:
                return True
        return False

    def get_tool(self, config_filename):
        """ Get the tool from the cache if the tool is up to date.
        """
        return self._tools_by_path.get(config_filename, None)

    def expire_tool(self, tool_id):
        if tool_id in self._tool_paths_by_id:
            config_filename = self._tool_paths_by_id[tool_id]
            del self._hash_by_tool_paths[config_filename]
            del self._tool_paths_by_id[tool_id]
            del self._tools_by_path[config_filename]
            del self._mod_time_by_path[config_filename]

    def cache_tool(self, config_filename, tool):
        tool_hash = md5_hash_file(config_filename)
        tool_id = str( tool.id )
        self._hash_by_tool_paths[config_filename] = tool_hash
        self._mod_time_by_path[config_filename] = time.ctime(os.path.getmtime(config_filename))
        self._tool_paths_by_id[tool_id] = config_filename
        self._tools_by_path[config_filename] = tool
