

class ToolCache(object):
    """ Cache tool defintions to allow quickly reloading the whole
    toolbox.
    """

    def __init__(self):
        self._tools_by_path = {}

    def get_tool(self, config_filename):
        """ Get the tool from the cache if the tool is up to date.
        """
        return self._tools_by_path.get(config_filename, None)

    def cache_tool(self, config_filename, tool):
        self._tools_by_path[config_filename] = tool
