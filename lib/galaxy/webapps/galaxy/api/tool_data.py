from typing import Optional

from fastapi import (
    Path,
)
from fastapi.responses import FileResponse

from galaxy import web
from galaxy.managers.context import ProvidesAppContext
from galaxy.managers.tool_data import ToolDataManager
from galaxy.tools.data._schema import (
    ToolDataDetails,
    ToolDataEntryList,
    ToolDataField,
    ToolDataItem,
)
from galaxy.web import (
    expose_api,
    expose_api_raw,
)
from . import (
    BaseGalaxyAPIController,
    depends,
    Router
)

router = Router(tags=['tool data tables'])

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
        '/api/tool_data',
        summary="Lists all available data tables",
        response_description="A list with details on individual data tables.",
        require_admin=True,
    )
    async def index(self) -> ToolDataEntryList:
        """Get the list of all available data tables."""
        return self.tool_data_manager.index()

    @router.get(
        '/api/tool_data/{table_name}',
        summary="Get details of a given data table",
        response_description="A description of the given data table and its content",
        require_admin=True,
    )
    async def show(self, table_name: str = ToolDataTableName) -> ToolDataDetails:
        """Get details of a given tool data table."""
        return self.tool_data_manager.show(table_name)

    @router.get(
        '/api/tool_data/{table_name}/reload',
        summary="Reloads a tool data table",
        response_description="A description of the reloaded data table and its content",
        require_admin=True,
    )
    async def reload(self, table_name: str = ToolDataTableName) -> ToolDataDetails:
        """Reloads a data table and return its details."""
        return self.tool_data_manager.reload(table_name)

    @router.get(
        '/api/tool_data/{table_name}/fields/{field_name}',
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
        '/api/tool_data/{table_name}/fields/{field_name}/files/{file_name}',
        summary="Get information about a particular field in a tool data table",
        response_description="Information about a data table field",
        response_class=FileResponse,
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
        return FileResponse(str(path))

    @router.delete(
        '/api/tool_data/{table_name}',
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


class ToolData(BaseGalaxyAPIController):
    """
    RESTful controller for interactions with tool data
    """
    tool_data_manager: ToolDataManager = depends(ToolDataManager)

    @web.require_admin
    @expose_api
    def index(self, trans: ProvidesAppContext, **kwds):
        """
        GET /api/tool_data

        Return a list tool_data tables.
        """
        return self.tool_data_manager.index()

    @web.require_admin
    @expose_api
    def show(self, trans: ProvidesAppContext, id, **kwds):
        details = self.tool_data_manager.show(id)
        # Here dict(by_alias=True) is required to return
        # `field_value` as `field` since `field` can not be directly
        # used in the pydantic BaseModel and needs to be aliased
        # For more details see: https://github.com/samuelcolvin/pydantic/issues/1250
        return details.dict(by_alias=True)

    @web.require_admin
    @expose_api
    def reload(self, trans, id, **kwd):
        """
        GET /api/tool_data/{id}/reload

        Reloads a tool_data table.
        """
        details = self.tool_data_manager.reload(id)
        # Here dict(by_alias=True) is required to return
        # `field_value` as `field` since `field` can not be directly
        # used in the pydantic BaseModel and needs to be aliased
        # For more details see: https://github.com/samuelcolvin/pydantic/issues/1250
        return details.dict(by_alias=True)

    @web.require_admin
    @expose_api
    def delete(self, trans: ProvidesAppContext, id, **kwd):
        """
        DELETE /api/tool_data/{id}
        Removes an item from a data table

        :type   id:     str
        :param  id:     the id of the data table containing the item to delete
        :type   kwd:    dict
        :param  kwd:    (required) dictionary structure containing:

            * payload:     a dictionary itself containing:
                * values:   <TAB> separated list of column contents, there must be a value for all the columns of the data table
        """
        values: Optional[str] = None
        if kwd.get('payload', None):
            values = kwd['payload'].get('values', '')
        # Here dict(by_alias=True) is required to return
        # `field_value` as `field` since `field` can not be directly
        # used in the pydantic BaseModel and needs to be aliased
        # For more details see: https://github.com/samuelcolvin/pydantic/issues/1250
        return self.tool_data_manager.delete(id, values).dict(by_alias=True)

    @web.require_admin
    @expose_api
    def show_field(self, trans: ProvidesAppContext, id, value, **kwds):
        """
        GET /api/tool_data/<id>/fields/<value>

        Get information about a partiular field in a tool_data table
        """
        field = self.tool_data_manager.show_field(id, value)
        # Here dict(by_alias=True) is required to return
        # `field_value` as `field` since `field` can not be directly
        # used in the pydantic BaseModel and needs to be aliased
        # For more details see: https://github.com/samuelcolvin/pydantic/issues/1250
        return field.dict(by_alias=True)

    @web.require_admin
    @expose_api_raw
    def download_field_file(self, trans: ProvidesAppContext, id: str, value, path, **kwds):
        full_path = self.tool_data_manager.get_field_file_path(id, value, path)
        return open(full_path, "rb")
