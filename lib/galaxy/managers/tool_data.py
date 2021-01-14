
from pydantic.tools import parse_obj_as

from galaxy.app import UniverseApplication
from galaxy.tools.data._schema import (
    ToolDataEntryList
)


class ToolDataManager:
    """
    Interface/service object for interacting with tool data.
    """

    def __init__(self, app: UniverseApplication):
        self._app = app

    @property
    def data_tables(self):
        return self._app.tool_data_tables.data_tables

    def index(self) -> ToolDataEntryList:
        """Return all tool data tables."""
        data_tables = [table.to_dict() for table in self.data_tables.values()]
        return parse_obj_as(ToolDataEntryList, data_tables)
