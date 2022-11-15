from fastapi import Path

from galaxy.managers.tool_data import ToolDataManager
from galaxy.tools.data._schema import (
    ToolDataDetails,
    ToolDataEntryList,
    ToolDataField,
    ToolDataItem,
)
from galaxy.webapps.base.api import GalaxyFileResponse
from . import (
    depends,
    Router,
)

router = Router(tags=["tool data tables"])

ToolDataTableName = Path(
    ...,  # Mark this field as required
    title="Data table name",
    description="The name of the tool data table",
    example="all_fasta",
)

ToolDataTableFieldName = Path(
    ...,  # Mark this field as required
    title="Field name",
    description="The name of the tool data table field",
)


@router.cbv
class FastAPIToolData:
    tool_data_manager: ToolDataManager = depends(ToolDataManager)

    @router.get(
        "/api/tool_data",
        summary="Lists all available data tables",
        response_description="A list with details on individual data tables.",
        require_admin=True,
    )
    async def index(self) -> ToolDataEntryList:
        """Get the list of all available data tables."""
        return self.tool_data_manager.index()

    @router.get(
        "/api/tool_data/{table_name}",
        summary="Get details of a given data table",
        response_description="A description of the given data table and its content",
        require_admin=True,
    )
    async def show(self, table_name: str = ToolDataTableName) -> ToolDataDetails:
        """Get details of a given tool data table."""
        return self.tool_data_manager.show(table_name)

    @router.get(
        "/api/tool_data/{table_name}/reload",
        summary="Reloads a tool data table",
        response_description="A description of the reloaded data table and its content",
        require_admin=True,
    )
    async def reload(self, table_name: str = ToolDataTableName) -> ToolDataDetails:
        """Reloads a data table and return its details."""
        return self.tool_data_manager.reload(table_name)

    @router.get(
        "/api/tool_data/{table_name}/fields/{field_name}",
        summary="Get information about a particular field in a tool data table",
        response_description="Information about a data table field",
        require_admin=True,
    )
    async def show_field(
        self,
        table_name: str = ToolDataTableName,
        field_name: str = ToolDataTableFieldName,
    ) -> ToolDataField:
        """Reloads a data table and return its details."""
        return self.tool_data_manager.show_field(table_name, field_name)

    @router.get(
        "/api/tool_data/{table_name}/fields/{field_name}/files/{file_name}",
        summary="Get information about a particular field in a tool data table",
        response_description="Information about a data table field",
        response_class=GalaxyFileResponse,
        require_admin=True,
    )
    async def download_field_file(
        self,
        table_name: str = ToolDataTableName,
        field_name: str = ToolDataTableFieldName,
        file_name: str = Path(
            ...,  # Mark this field as required
            title="File name",
            description="The name of a file associated with this data table field",
        ),
    ):
        """Download a file associated with the data table field."""
        path = self.tool_data_manager.get_field_file_path(table_name, field_name, file_name)
        return GalaxyFileResponse(str(path))

    @router.delete(
        "/api/tool_data/{table_name}",
        summary="Removes an item from a data table",
        response_description="A description of the affected data table and its content",
        require_admin=True,
    )
    async def delete(
        self,
        payload: ToolDataItem,
        table_name: str = ToolDataTableName,
    ) -> ToolDataDetails:
        """Removes an item from a data table and reloads it to return its updated details."""
        return self.tool_data_manager.delete(table_name, payload.values)
