
from galaxy import exceptions
from galaxy.app import UniverseApplication
from galaxy.tools.data import TabularToolDataTable
from galaxy.tools.data._schema import (
    ToolDataDetails,
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
        return ToolDataEntryList.parse_obj(data_tables)

    def show(self, name: str) -> ToolDataDetails:
        """Get details of a given data table"""
        table = self._data_table(name)
        element_view = table.to_dict(view='element')
        return ToolDataDetails.parse_obj(element_view)

    def _data_table(self, name: str) -> TabularToolDataTable:
        try:
            return self.data_tables[name]
        except IndexError:
            raise exceptions.ObjectNotFound(f"No such data table {name}")
