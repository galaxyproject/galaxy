from pathlib import Path
from typing import (
    cast,
    Dict,
    Optional,
)

from galaxy import exceptions
from galaxy.files import ConfiguredFileSources
from galaxy.files.uris import stream_url_to_file
from galaxy.model import DatasetInstance
from galaxy.structured_app import (
    MinimalManagerApp,
    StructuredApp,
)
from galaxy.tool_util.data import BundleProcessingOptions
from galaxy.tool_util.data._schema import (
    ToolDataDetails,
    ToolDataEntryList,
    ToolDataField,
)
from galaxy.tools.data import (
    TabularToolDataField,
    TabularToolDataTable,
    ToolDataTable,
    ToolDataTableManager,
)


class ToolDataManager:
    """
    Interface/service object for interacting with tool data.
    """

    def __init__(self, app: StructuredApp):
        self._app = app

    @property
    def data_tables(self) -> Dict[str, ToolDataTable]:
        return self._app.tool_data_tables.data_tables

    def index(self) -> ToolDataEntryList:
        """Return all tool data tables."""
        return self._app.tool_data_tables.index()

    def show(self, table_name: str) -> ToolDataDetails:
        """Get details of a given data table"""
        data_table = self._data_table(table_name)
        element_view = data_table.to_dict(view="element")
        return ToolDataDetails.construct(**element_view)

    def show_field(self, table_name: str, field_name: str) -> ToolDataField:
        """Get information about a partiular field in a tool data table"""
        field = self._data_table_field(table_name, field_name)
        return ToolDataField.construct(**field.to_dict())

    def reload(self, table_name: str) -> ToolDataDetails:
        """Reloads a tool data table."""
        data_table = self._data_table(table_name)
        data_table.reload_from_files()
        return self._reload_data_table(table_name)

    def get_field_file_path(self, table_name: str, field_name: str, file_name: str) -> Path:
        """Get the absolute path to a given file name in the table field"""
        field_value = self._data_table_field(table_name, field_name)
        base_dir = Path(field_value.get_base_dir())
        full_path = base_dir / file_name
        if str(full_path) not in field_value.get_files():
            raise exceptions.ObjectNotFound("No such path in data table field.")
        return full_path.absolute()

    def delete(self, table_name: str, values: Optional[str] = None) -> ToolDataDetails:
        """Removes an item from a data table"""
        data_table = self._tabular_data_table(table_name)
        if not values:
            raise exceptions.RequestParameterInvalidException("Invalid values for data table item specified.")

        split_values = values.split("\t")

        if len(split_values) != len(data_table.get_column_name_list()):
            raise exceptions.RequestParameterInvalidException(
                f"Invalid data table item ( {values} ) specified. Wrong number of columns ({len(split_values)} given, {len(data_table.get_column_name_list())} required)."
            )

        data_table.remove_entry(split_values)
        return self._reload_data_table(table_name)

    def _tabular_data_table(self, table_name: str) -> TabularToolDataTable:
        return cast(TabularToolDataTable, self._data_table(table_name))

    def _data_table(self, table_name: str) -> ToolDataTable:
        try:
            return self.data_tables[table_name]
        except KeyError:
            raise exceptions.ObjectNotFound(f"No such data table {table_name}")

    def _data_table_field(self, table_name: str, field_name: str) -> TabularToolDataField:
        out = self._tabular_data_table(table_name).get_field(field_name)
        if out is None:
            raise exceptions.ObjectNotFound(f"No such field {field_name} in data table {table_name}.")
        return out

    def _reload_data_table(self, name: str) -> ToolDataDetails:
        self._app.queue_worker.send_control_task("reload_tool_data_tables", noop_self=True, kwargs={"table_name": name})
        return self.show(name)


class ToolDataImportManager:
    file_sources: ConfiguredFileSources
    tool_data_tables: ToolDataTableManager

    def __init__(self, app: MinimalManagerApp):
        self.file_sources = app.file_sources
        self.tool_data_tables = app.tool_data_tables

    def import_data_bundle_by_uri(self, config, uri: str):
        # an admin-only task - so allow file:// uris
        if uri.startswith("file://"):
            target = uri[len("file://") :]
        else:
            target = stream_url_to_file(
                uri,
                self.file_sources,
            )
        options = BundleProcessingOptions(
            what="data import",  # An alternative to this is sticking this in the bundle, only used for logging.
            data_manager_path=config.galaxy_data_manager_data_path,
            target_config_file=config.data_manager_config_file,
        )
        self.tool_data_tables.import_bundle(
            target,
            options,
        )

    def import_data_bundle_by_dataset(self, config, dataset: DatasetInstance):
        options = BundleProcessingOptions(
            what="data import",  # An alternative to this is sticking this in the bundle, only used for logging.
            data_manager_path=config.galaxy_data_manager_data_path,
            target_config_file=config.data_manager_config_file,
        )
        self.tool_data_tables.import_bundle(
            dataset.extra_files_path,
            options,
        )
