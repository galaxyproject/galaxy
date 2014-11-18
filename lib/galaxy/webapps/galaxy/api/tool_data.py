from galaxy import web
from galaxy.web.base.controller import BaseAPIController


class ToolData( BaseAPIController ):
    """
    RESTful controller for interactions with tool data
    """

    @web.require_admin
    @web.expose_api
    def index( self, trans, **kwds ):
        """
        GET /api/tool_data: returns a list tool_data tables::

        """
        return list( a.to_dict() for a in trans.app.tool_data_tables.data_tables.values() )

    @web.require_admin
    @web.expose_api
    def show( self, trans, id, **kwds ):
        return trans.app.tool_data_tables.data_tables[id].to_dict(view='element')
