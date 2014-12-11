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

    @web.require_admin
    @web.expose_api
    def delete( self, trans, id, **kwd ):
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
            data_table = trans.app.tool_data_tables.data_tables.get(decoded_tool_data_id)
        except:
            data_table = None
        if not data_table:
            trans.response.status = 400
            return "Invalid data table id ( %s ) specified." % str( decoded_tool_data_id )
        
        values = None
        if kwd.get( 'payload', None ):
            values = kwd['payload'].get( 'values', '' )

        if not values:
            trans.response.status = 400
            return "Invalid data table item ( %s ) specified." % str( values )
        
        split_values = values.split("\t")
        
        if len(split_values) != len(data_table.get_column_name_list()):
            trans.response.status = 400
            return "Invalid data table item ( %s ) specified. Wrong number of columns (%s given, %s required)." % ( str( values ), str(len(split_values)), str(len(data_table.get_column_name_list())))

        return data_table.remove_entry(split_values)
