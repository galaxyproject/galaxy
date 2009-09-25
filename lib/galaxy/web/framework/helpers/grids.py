from galaxy.model import *
from galaxy.model.orm import *

from galaxy.web import url_for
from galaxy.util.json import from_json_string, to_json_string

import sys, logging

log = logging.getLogger( __name__ )

class Grid( object ):
    """
    Specifieds the content and format of a grid (data table).
    """
    title = ""
    exposed = True
    model_class = None
    template = "grid.mako"
    global_actions = []
    columns = []
    operations = []
    standard_filters = []
    default_filter = None
    default_sort_key = None
    preserve_state = True
    # Set preference names.
    cur_filter_pref_name = ".filter"
    cur_sort_key_pref_name = ".sort_key"    
    pass_through_operations = {}
    def __init__( self ):
        # Determine if any multiple row operations are defined
        self.has_multiple_item_operations = False
        for operation in self.operations:
            if operation.allow_multiple:
                self.has_multiple_item_operations = True
                break
                
    def __call__( self, trans, **kwargs ):
        status = kwargs.get( 'status', None )
        message = kwargs.get( 'message', None )
        session = trans.sa_session
        
        # Build a base filter and sort key that is the combination of the saved state and defaults. Saved state takes preference over defaults.
        base_filter = {}
        if self.default_filter:
            base_filter = self.default_filter.copy()
        base_sort_key = self.default_sort_key            
        if self.preserve_state:
            saved_filter_pref = trans.sa_session.query( UserPreference ).\
                                    filter_by( name=self.__class__.__name__ + self.cur_filter_pref_name, user_id=trans.get_user().id ).first()
            if saved_filter_pref:
                saved_filter = from_json_string( saved_filter_pref.value )
                base_filter.update( saved_filter )
            
            saved_sort_key_pref = trans.sa_session.query( UserPreference ).\
                                    filter_by( name=self.__class__.__name__ + self.cur_sort_key_pref_name, user_id=trans.get_user().id ).first()
            if saved_sort_key_pref:
                base_sort_key = from_json_string( saved_sort_key_pref.value )
        
        # Build initial query
        query = self.build_initial_query( session )
        query = self.apply_default_filter( trans, query, **kwargs )
        
        # Maintain sort state in generated urls
        extra_url_args = {}
        
        # Process filtering arguments to (a) build a query that represents the filter and (b) builds a
        # dictionary that denotes the current filter.
        cur_filter_dict = {}
        for column in self.columns:
            if column.key:
                # Look for filter criterion in kwargs; if not found, look in base filter.
                column_filter = None
                if "f-" + column.key in kwargs:
                    column_filter = kwargs.get( "f-" + column.key )
                elif column.key in base_filter:
                    column_filter = base_filter.get( column.key )

                # If column filter found, apply it.
                if column_filter is not None:
                    # Update query.
                    query = column.filter( trans.sa_session, query, column_filter )
                    # Upate current filter dict.
                    cur_filter_dict[ column.key ] = column_filter
                    # Carry filter along to newly generated urls; make sure filter is a string so 
                    # that we can encode to UTF-8 and thus handle user input to filters.
                    if not isinstance( column_filter, basestring ):
                        column_filter = unicode(column_filter)
                    extra_url_args[ "f-" + column.key ] = column_filter.encode("utf-8")
                    
        # Process sort arguments
        sort_key = sort_order = None
        if 'sort' in kwargs:
            sort_key = kwargs['sort']
        elif base_sort_key:
            sort_key = base_sort_key
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
        
        # Save current filter and sort key.
        if self.preserve_state:
            pref_name = self.__class__.__name__ + self.cur_filter_pref_name
            if not saved_filter_pref:
                saved_filter_pref = UserPreference( name=pref_name )
                trans.get_user().preferences.append( saved_filter_pref )
            saved_filter_pref.value = to_json_string( cur_filter_dict )
            if not saved_sort_key_pref:
                pref_name = self.__class__.__name__ + self.cur_sort_key_pref_name
                if not saved_sort_key_pref:
                    saved_sort_key_pref = UserPreference( name=pref_name )
                    trans.get_user().preferences.append( saved_sort_key_pref )
            saved_sort_key_pref.value = to_json_string( sort_key )
            trans.sa_session.flush()
        
        # Render grid.
        def url( *args, **kwargs ):
            # Only include sort/filter arguments if not linking to another
            # page. This is a bit of a hack.
            if 'action' in kwargs:
                new_kwargs = dict()
            else:
                new_kwargs = dict( extra_url_args )
            # Extend new_kwargs with first argument if found
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
        return trans.fill_template( self.template,
                                    grid=self,
                                    query=query,
                                    cur_filter_dict=cur_filter_dict,
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
    def apply_default_filter( self, trans, query, **kwargs):
        return query
    
class GridColumn( object ):
    def __init__( self, label, key=None, method=None, format=None, link=None, attach_popup=False, visible=True, ncells=1, filterable=False ):
        self.label = label
        self.key = key
        self.method = method
        self.format = format
        self.link = link
        self.attach_popup = attach_popup
        self.visible = visible
        self.ncells = ncells
        self.filterable = filterable
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
    def filter( self, db_session, query, column_filter ):
        """ Modify query to reflect the column filter. """
        if column_filter == "All":
            pass
        if column_filter == "True":
            query = query.filter_by( **{ self.key: True } )
        elif column_filter == "False":
            query = query.filter_by( **{ self.key: False } )
        return query
    def get_accepted_filters( self ):
        """ Returns a list of accepted filters for this column. """
        accepted_filters_vals = [ "False", "True", "All" ]
        accepted_filters = []
        for val in accepted_filters_vals:
            args = { self.key: val }
            accepted_filters.append( GridColumnFilter( val, args) )
        return accepted_filters

class GridOperation( object ):
    def __init__( self, label, key=None, condition=None, allow_multiple=True, target=None, url_args=None ):
        self.label = label
        self.key = key
        self.allow_multiple = allow_multiple
        self.condition = condition
        self.target = target
        self.url_args = url_args
    def get_url_args( self, item ):
        if self.url_args:
            temp = dict( self.url_args )
            temp['id'] = item.id
            return temp
        else:
            return dict( operation=operation.label, id=item.id )
        
    def allowed( self, item ):
        if self.condition:
            return self.condition( item )
        else:
            return True
        
class GridAction( object ):
    def __init__( self, label=None, url_args=None ):
        self.label = label
        self.url_args = url_args
        
class GridColumnFilter( object ):
    def __init__( self, label, args=None ):
        self.label = label
        self.args = args
    def get_url_args( self ):
        rval = {}
        for k, v in self.args.items():
            rval[ "f-" + k ] = v
        return rval
        