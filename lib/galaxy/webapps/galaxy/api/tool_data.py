from fastapi import (
    Depends,
    Path,
)
from fastapi.responses import FileResponse
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter as APIRouter

from galaxy import (
    exceptions,
    web,
)
from galaxy.managers.context import ProvidesAppContext
from galaxy.app import UniverseApplication
from galaxy.managers.tool_data import ToolDataManager
from galaxy.tools.data._schema import (
    ToolDataDetails,
    ToolDataEntryList,
    ToolDataField,
)
from galaxy.web import (
    expose_api,
    expose_api_raw,
)
from galaxy.webapps.base.controller import BaseAPIController
from . import (
    get_admin_user,
    get_app,
)

router = APIRouter(tags=['tool data'])

AdminUserRequired = Depends(get_admin_user)

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


def get_tool_data_manager(app: UniverseApplication = Depends(get_app)) -> ToolDataManager:
    return ToolDataManager(app)


@cbv(router)
class FastAPIToolData:
    tool_data_manager: ToolDataManager = Depends(get_tool_data_manager)

    @router.get(
        '/api/tool_data',
        summary="Lists all available data tables",
        response_description="A list with details on individual data tables.",
        dependencies=[
            AdminUserRequired
        ],
    )
    async def index(self) -> ToolDataEntryList:
        """Get the list of all available data tables."""
        return self.tool_data_manager.index()

    @router.get(
        '/api/tool_data/{name}',
        summary="Get details of a given data table",
        response_description="A description of the given data table and its content",
        dependencies=[
            AdminUserRequired
        ],
    )
    async def show(self, name: str = ToolDataTableName) -> ToolDataDetails:
        """Get details of a given tool data table."""
        return self.tool_data_manager.show(name)

    @router.get(
        '/api/tool_data/{name}/reload',
        summary="Reloads a tool data table",
        response_description="A description of the reloaded data table and its content",
        dependencies=[
            AdminUserRequired
        ],
    )
    async def reload(self, name: str = ToolDataTableName) -> ToolDataDetails:
        """Reloads a data table and return its details."""
        return self.tool_data_manager.reload(name)

    @router.get(
        '/api/tool_data/{table_name}/fields/{field_name}',
        summary="Get information about a particular field in a tool data table",
        response_description="Information about a data table field",
        dependencies=[
            AdminUserRequired
        ],
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
        dependencies=[
            AdminUserRequired
        ],
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


class ToolData(BaseAPIController):
    """
    RESTful controller for interactions with tool data
    """

    def __init__(self, app):
        super().__init__(app)
        self.tool_data_manager = ToolDataManager(app)

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
        decoded_tool_data_id = id

        try:
            data_table = self.app.tool_data_tables.data_tables.get(decoded_tool_data_id)
        except Exception:
            data_table = None
        if not data_table:
            raise exceptions.RequestParameterInvalidException("Invalid data table id ( %s ) specified." % str(decoded_tool_data_id))

        values = None
        if kwd.get('payload', None):
            values = kwd['payload'].get('values', '')

        if not values:
            raise exceptions.RequestParameterInvalidException("Invalid data table item ( %s ) specified." % str(values))

        split_values = values.split("\t")

        if len(split_values) != len(data_table.get_column_name_list()):
            raise exceptions.RequestParameterInvalidException("Invalid data table item ( {} ) specified. Wrong number of columns ({} given, {} required).".format(str(values), str(len(split_values)), str(len(data_table.get_column_name_list()))))

        data_table.remove_entry(split_values)
        self.app.queue_worker.send_control_task(
            'reload_tool_data_tables',
            noop_self=True,
            kwargs={'table_name': decoded_tool_data_id}
        )
        return self._data_table(decoded_tool_data_id).to_dict(view='element')

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

    def _data_table_field(self, id, value):
        out = self._data_table(id).get_field(value)
        if out is None:
            raise exceptions.ObjectNotFound(f"No such field {value} in data table {id}.")
        return out

    def _data_table(self, id):
        try:
            return self._data_tables[id]
        except IndexError:
            raise exceptions.ObjectNotFound("No such data table %s" % id)

    @property
    def _data_tables(self):
        return self.app.tool_data_tables.data_tables
