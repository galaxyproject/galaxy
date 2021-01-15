
from typing import Dict

from galaxy import exceptions
from galaxy.app import UniverseApplication
from galaxy.queue_worker import GalaxyQueueWorker
from galaxy.tools.data import (
    TabularToolDataField,
    TabularToolDataTable,
)
from galaxy.tools.data._schema import (
    ToolDataDetails,
    ToolDataEntryList,
    ToolDataField,
)


class ToolDataManager:
    """
    Interface/service object for interacting with tool data.
    """

    def __init__(self, app: UniverseApplication):
        self._app = app

    @property
    def data_tables(self) -> Dict[str, TabularToolDataTable]:
        return self._app.tool_data_tables.data_tables

    @property
    def queue_worker(self) -> GalaxyQueueWorker:
        return self._app.queue_worker

    def index(self) -> ToolDataEntryList:
        """Return all tool data tables."""
        data_tables = [table.to_dict() for table in self.data_tables.values()]
        return ToolDataEntryList.parse_obj(data_tables)

    def show(self, name: str) -> ToolDataDetails:
        """Get details of a given data table"""
        data_table = self._data_table(name)
        element_view = data_table.to_dict(view='element')
        return ToolDataDetails.parse_obj(element_view)

    def show_field(self, table_name: str, field_name: str) -> ToolDataField:
        """Get information about a partiular field in a tool data table"""
        field = self._data_table_field(table_name, field_name)
        return ToolDataField.parse_obj(field.to_dict())

    def reload(self, name: str) -> ToolDataDetails:
        """Reloads a tool data table."""
        data_table = self._data_table(name)
        data_table.reload_from_files()
        self.queue_worker.send_control_task(
            'reload_tool_data_tables',
            noop_self=True,
            kwargs={'table_name': name}
        )
        return self.show(name)

    def _data_table(self, name: str) -> TabularToolDataTable:
        try:
            return self.data_tables[name]
        except KeyError:
            raise exceptions.ObjectNotFound(f"No such data table {name}")

    def _data_table_field(self, table_name: str, field_name: str) -> TabularToolDataField:
        out = self._data_table(table_name).get_field(field_name)
        if out is None:
            raise exceptions.ObjectNotFound(f"No such field {field_name} in data table {table_name}.")
        return out
