import os

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

    def cleanup(self):
        """Remove uninstalled tools from tool cache if they are not on disk anymore or if their content has changed."""
        clean_paths = {path: tool.all_ids for path, tool in self._tools_by_path.items() if not os.path.exists(path) or md5_hash_file(path) != self._hash_by_tool_paths[path]}
        for path, tool_ids in clean_paths.items():
            del self._hash_by_tool_paths[path]
            del self._tools_by_path[path]
            for tool_id in tool_ids:
                if tool_id in self._tool_paths_by_id:
                    del self._tool_paths_by_id[tool_id]

    def get_tool(self, config_filename):
        """ Get the tool from the cache if the tool is up to date.
        """
        return self._tools_by_path.get(config_filename, None)

    def expire_tool(self, tool_id):
        if tool_id in self._tool_paths_by_id:
            config_filename = self._tool_paths_by_id[tool_id]
            del self._tool_paths_by_id[tool_id]
            del self._tools_by_path[config_filename]

    def cache_tool(self, config_filename, tool):
        tool_hash = md5_hash_file(config_filename)
        tool_id = str( tool.id )
        self._hash_by_tool_paths[config_filename] = tool_hash
        self._tool_paths_by_id[tool_id] = config_filename
        self._tools_by_path[config_filename] = tool
