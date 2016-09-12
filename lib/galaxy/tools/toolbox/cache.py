

class ToolCache(object):
    """
    Cache tool definitions to allow quickly reloading the whole
    toolbox.
    """

    def __init__(self):
        self._tools_by_path = {}
        self._tool_paths_by_id = {}

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
        tool_id = str( tool.id )
        self._tool_paths_by_id[tool_id] = config_filename
        self._tools_by_path[config_filename] = tool
