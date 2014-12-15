from galaxy import exceptions
from galaxy import web
from galaxy.web import _future_expose_api as expose_api
from galaxy.web.base.controller import BaseAPIController


class ToolData( BaseAPIController ):
    """
    RESTful controller for interactions with tool data
    """

    @web.require_admin
    @expose_api
    def index( self, trans, **kwds ):
        """
        GET /api/tool_data: returns a list tool_data tables::

        """
        return list( a.to_dict() for a in self._data_tables.values() )

    @web.require_admin
    @expose_api
    def show( self, trans, id, **kwds ):
        return self._data_table(id).to_dict(view='element')

    @web.require_admin
    @expose_api
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

    @web.require_admin
    @expose_api
    def show_field( self, trans, id, value, **kwds ):
        """
        GET /api/tool_data/<id>/fields/<value>

        Get information about a partiular field in a tool_data table
        """
        return self._data_table_field( id, value ).to_dict()

    def _data_table_field( self, id, value ):
        out = self._data_table(id).get_field(value)
        if out is None:
            raise exceptions.ObjectNotFound("No such field %s in data table %s." % (value, id))
        return out

    def _data_table( self, id ):
        try:
            return self._data_tables[id]
        except IndexError:
            raise exceptions.ObjectNotFound("No such data table %s" % id)

    @property
    def _data_tables( self ):
        return self.app.tool_data_tables.data_tables
