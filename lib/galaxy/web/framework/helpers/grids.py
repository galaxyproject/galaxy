from galaxy.model import *
from galaxy.model.orm import *

from galaxy.web import url_for

import sys, logging

log = logging.getLogger( __name__ )

class Grid( object ):
    """
    Specifieds the content and format of a grid (data table).
    """
    title = ""
    exposed = True
    model_class = None
    template = None
    columns = []
    standard_filters = []
    default_filter = None
    default_sort_key = None
    pass_through_operations = {}
    def __init__( self ):
        pass
    def __call__( self, trans, **kwargs ):
        status = kwargs.get( 'status', None )
        message = kwargs.get( 'message', None )
        template = kwargs.get( 'template', None )
        session = trans.sa_session
        # Build initial query
        query = self.build_initial_query( session )
        query = self.apply_default_filter( trans, query )
        # Maintain sort state in generated urls
        extra_url_args = {}
        # Process filtering arguments
        filter_args = {}
        if self.default_filter:
            filter_args.update( self.default_filter )
        for column in self.columns:
            if column.key:
                if "f-" + column.key in kwargs:
                    column_filter = kwargs.get( "f-" + column.key )
                    query = column.filter( query, column_filter, filter_args )
                    # Carry filter along to newly generated urls
                    extra_url_args[ "f-" + column.key ] = column_filter
        if filter_args:
            query = query.filter_by( **filter_args )
        # Process sort arguments
        sort_key = sort_order = None
        if 'sort' in kwargs:
            sort_key = kwargs['sort']
        elif self.default_sort_key:
            sort_key = self.default_sort_key
        encoded_sort_key = sort_key
        if sort_key:
            if sort_key.startswith( "-" ):
                sort_key = sort_key[1:]
                sort_order = 'desc'
                query = query.order_by( self.model_class.c.get( sort_key ).desc() )
            else:
                sort_order = 'asc'
                query = query.order_by( self.model_class.c.get( sort_key ).asc() )
        extra_url_args['sort'] = encoded_sort_key
        # There might be a current row
        current_item = self.get_current_item( trans )
        # Render
        def url( *args, **kwargs ):
            new_kwargs = dict( extra_url_args )
            if len(args) > 0:
                new_kwargs.update( args[0] )
            new_kwargs.update( kwargs )
            # We need to encode item ids
            if 'id' in new_kwargs:
                id = new_kwargs[ 'id' ]
                if isinstance( id, list ):
                    new_args[ 'id' ] = [ trans.security.encode_id( i ) for i in id ]
                else:
                    new_kwargs[ 'id' ] = trans.security.encode_id( id )
            return url_for( **new_kwargs )
        return trans.fill_template( template,
                                    grid=self,
                                    query=query,
                                    sort_key=sort_key,
                                    encoded_sort_key=encoded_sort_key,
                                    sort_order=sort_order,
                                    current_item=current_item,
                                    ids = kwargs.get( 'id', [] ),
                                    url = url,
                                    message_type = status,
                                    message = message )
    def get_ids( self, **kwargs ):
        id = []
        if 'id' in kwargs:
            id = kwargs['id']
            # Coerce ids to list
            if not isinstance( id, list ):
                id = id.split( "," )
            # Ensure ids are integers
            try:
                id = map( int, id )
            except:
                error( "Invalid id" )
        return id
        
    # ---- Override these ----------------------------------------------------
    def handle_operation( self, trans, operation, ids ):
        pass
    def get_current_item( self, trans ):
        return None
    def build_initial_query( self, session ):
        return session.query( self.model_class )
    def apply_default_filter( self, trans, query ):
        return query
    
class GridColumn( object ):
    def __init__( self, label, key=None, method=None, format=None, link=None, attach_popup=False, visible=True, ncells=1 ):
        self.label = label
        self.key = key
        self.method = method
        self.format = format
        self.link = link
        self.attach_popup = attach_popup
        self.visible = visible
        self.ncells = ncells
        # Currently can only sort of columns that have a database
        # representation, not purely derived.
        if self.key:
            self.sortable = True
        else:
            self.sortable = False
    def get_value( self, trans, grid, item ):
        if self.method:
            value = getattr( grid, self.method )( trans, item )
        elif self.key:
            value = getattr( item, self.key )
        else:
            value = None
        if self.format:
            value = self.format( value )
        return value
    def get_link( self, trans, grid, item ):
        if self.link and self.link( item ):
            return self.link( item )
        return None
    def filter( self, query, column_filter, filter_args ):
        """
        Must modify filter_args for carrying forward, and return query
        (possibly filtered).
        """
        if column_filter == "True":
            filter_args[self.key] = True
            query = query.filter_by( **{ self.key: True } )
        elif column_filter == "False":
            filter_args[self.key] = False
            query = query.filter_by( **{ self.key: False } )
        elif column_filter == "All":
            del filter_args[self.key]
        return query
        
        
    
class GridOperation( object ):
    def __init__( self, label, key=None, condition=None, allow_multiple=True ):
        self.label = label
        self.key = key
        self.allow_multiple = allow_multiple
        self.condition = condition
    def allowed( self, item ):
        if self.condition:
            return self.condition( item )
        else:
            return True
        
class GridColumnFilter( object ):
    def __init__( self, label, args=None ):
        self.label = label
        self.args = args
    def get_url_args( self ):
        rval = {}
        for k, v in self.args.items():
            rval[ "f-" + k ] = v
        return rval
        