from fastapi import (
    Body,
    Path,
)
from pydantic import (
    BaseModel,
    Field,
)

from galaxy.celery.tasks import import_data_bundle
from galaxy.managers.tool_data import ToolDataManager
from galaxy.schema.schema import (
    AsyncTaskResultSummary,
    ImportToolDataBundleSource,
)
from galaxy.tool_util.data._schema import (
    ToolDataDetails,
    ToolDataEntryList,
    ToolDataField,
    ToolDataItem,
)
from galaxy.webapps.base.api import GalaxyFileResponse
from galaxy.webapps.galaxy.services.base import async_task_summary
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


class ImportToolDataBundle(BaseModel):
    source: ImportToolDataBundleSource = Field(..., discriminator="src")


class FastAPIToolData:
    @router.get(
        "/api/tool_data",
        summary="Lists all available data tables",
        response_description="A list with details on individual data tables.",
        require_admin=False,
    )
    async def index(tool_data_manager: ToolDataManager = depends(ToolDataManager)) -> ToolDataEntryList:
        """Get the list of all available data tables."""
        return tool_data_manager.index()

    @router.post(
        "/api/tool_data",
        summary="Import a data manager bundle",
        require_admin=True,
    )
    async def create(
        tool_data_file_path=None, import_bundle_model: ImportToolDataBundle = Body(...)
    ) -> AsyncTaskResultSummary:
        source = import_bundle_model.source
        result = import_data_bundle.delay(tool_data_file_path=tool_data_file_path, **source.dict())
        summary = async_task_summary(result)
        return summary

    @router.get(
        "/api/tool_data/{table_name}",
        summary="Get details of a given data table",
        response_description="A description of the given data table and its content",
        require_admin=True,
    )
    async def show(
        table_name: str = ToolDataTableName, tool_data_manager: ToolDataManager = depends(ToolDataManager)
    ) -> ToolDataDetails:
        """Get details of a given tool data table."""
        return tool_data_manager.show(table_name)

    @router.get(
        "/api/tool_data/{table_name}/reload",
        summary="Reloads a tool data table",
        response_description="A description of the reloaded data table and its content",
        require_admin=True,
    )
    async def reload(
        table_name: str = ToolDataTableName, tool_data_manager: ToolDataManager = depends(ToolDataManager)
    ) -> ToolDataDetails:
        """Reloads a data table and return its details."""
        return tool_data_manager.reload(table_name)

    @router.get(
        "/api/tool_data/{table_name}/fields/{field_name}",
        summary="Get information about a particular field in a tool data table",
        response_description="Information about a data table field",
        require_admin=True,
    )
    async def show_field(
        table_name: str = ToolDataTableName,
        field_name: str = ToolDataTableFieldName,
        tool_data_manager: ToolDataManager = depends(ToolDataManager),
    ) -> ToolDataField:
        """Reloads a data table and return its details."""
        return tool_data_manager.show_field(table_name, field_name)

    @router.get(
        "/api/tool_data/{table_name}/fields/{field_name}/files/{file_name}",
        summary="Get information about a particular field in a tool data table",
        response_description="Information about a data table field",
        response_class=GalaxyFileResponse,
        require_admin=True,
    )
    async def download_field_file(
        table_name: str = ToolDataTableName,
        field_name: str = ToolDataTableFieldName,
        file_name: str = Path(
            ...,  # Mark this field as required
            title="File name",
            description="The name of a file associated with this data table field",
        ),
        tool_data_manager: ToolDataManager = depends(ToolDataManager),
    ):
        """Download a file associated with the data table field."""
        path = tool_data_manager.get_field_file_path(table_name, field_name, file_name)
        return GalaxyFileResponse(str(path))

    @router.delete(
        "/api/tool_data/{table_name}",
        summary="Removes an item from a data table",
        response_description="A description of the affected data table and its content",
        require_admin=True,
    )
    async def delete(
        payload: ToolDataItem,
        table_name: str = ToolDataTableName,
        tool_data_manager: ToolDataManager = depends(ToolDataManager),
    ) -> ToolDataDetails:
        """Removes an item from a data table and reloads it to return its updated details."""
        return tool_data_manager.delete(table_name, payload.values)
