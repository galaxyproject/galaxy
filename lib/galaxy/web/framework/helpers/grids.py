from galaxy.model import *
from galaxy.model.orm import *

from galaxy.tags.tag_handler import TagHandler
from galaxy.web import url_for
from galaxy.util.json import from_json_string, to_json_string

import sys, logging, math

log = logging.getLogger( __name__ )

class Grid( object ):
    """
    Specifieds the content and format of a grid (data table).
    """
    title = ""
    exposed = True
    model_class = None
    template = "grid_base.mako"
    global_actions = []
    columns = []
    operations = []
    standard_filters = []
    # Any columns that are filterable (either standard or advanced) should have a default value set in the default filter.
    default_filter = {}
    default_sort_key = None
    preserve_state = False
    
    use_paging = False
    num_rows_per_page = 25
    
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
            pref_name = unicode( self.__class__.__name__ + self.cur_filter_pref_name )
            if pref_name in trans.get_user().preferences:
                saved_filter = from_json_string( trans.get_user().preferences[pref_name] )
                base_filter.update( saved_filter )
            
            pref_name = unicode( self.__class__.__name__ + self.cur_sort_key_pref_name )
            if pref_name in trans.get_user().preferences:
                base_sort_key = from_json_string( trans.get_user().preferences[pref_name] )

        # Build initial query
        query = self.build_initial_query( session )
        query = self.apply_default_filter( trans, query, **kwargs )
        
        # Maintain sort state in generated urls
        extra_url_args = {}
        
        # Determine whether use_default_filter flag is set.
        use_default_filter_str = kwargs.get( 'use_default_filter' )
        use_default_filter = False
        if use_default_filter_str:
            use_default_filter = ( use_default_filter_str.lower() == 'true' )
            
        # Process filtering arguments to (a) build a query that represents the filter and (b) builds a
        # dictionary that denotes the current filter.        
        cur_filter_dict = {}
        for column in self.columns:
            if column.key:
                # Get the filter criterion for the column. Precedence is (a) if using default filter, only look there; otherwise, 
                # (b) look in kwargs; and (c) look in base filter.
                column_filter = None
                if use_default_filter:
                    if self.default_filter:
                        column_filter = self.default_filter.get( column.key )
                elif "f-" + column.key in kwargs:
                    column_filter = kwargs.get( "f-" + column.key )
                elif column.key in base_filter:
                    column_filter = base_filter.get( column.key )
                    
                # Method (1) combines a mix of strings and lists of strings into a single string and (2) attempts to de-jsonify all strings.
                def from_json_string_recurse(item):
                   decoded_list = []
                   if isinstance( item, basestring):
                       try:
                           # Not clear what we're decoding, so recurse to ensure that we catch everything.
                            decoded_item = from_json_string( item ) 
                            if isinstance( decoded_item, list):
                                decoded_list = from_json_string_recurse( decoded_item )
                            else:
                                decoded_list = [ unicode( decoded_item ) ]
                       except ValueError:
                           decoded_list = [ unicode ( item ) ]
                   elif isinstance( item, list):
                       return_val = []
                       for element in item:
                           a_list = from_json_string_recurse( element )
                           decoded_list = decoded_list + a_list
                   return decoded_list
                                        
                # If column filter found, apply it.
                if column_filter is not None:
                    # TextColumns may have a mix of json and strings.
                    if isinstance( column, TextColumn ):
                        column_filter = from_json_string_recurse( column_filter )
                        if len( column_filter ) == 1:
                            column_filter = column_filter[0]
                    # Update query.
                    query = column.filter( trans.sa_session, query, column_filter )
                    # Upate current filter dict.
                    cur_filter_dict[ column.key ] = column_filter
                    # Carry filter along to newly generated urls; make sure filter is a string so
                    # that we can encode to UTF-8 and thus handle user input to filters.
                    if isinstance( column_filter, list ):
                        # Filter is a list; process each item.
                        for filter in column_filter:
                            if not isinstance( filter, basestring ):
                                filter = unicode( filter ).encode("utf-8")
                        extra_url_args[ "f-" + column.key ] = to_json_string( column_filter ) 
                    else:
                        # Process singleton filter.
                        if not isinstance( column_filter, basestring ):
                            column_filter = unicode(column_filter)
                        extra_url_args[ "f-" + column.key ] = column_filter.encode("utf-8")
                    
        # Process sort arguments.
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
                query = query.order_by( self.model_class.table.c.get( sort_key ).desc() )
            else:
                sort_order = 'asc'
                query = query.order_by( self.model_class.table.c.get( sort_key ).asc() )
        extra_url_args['sort'] = encoded_sort_key
        
        # There might be a current row
        current_item = self.get_current_item( trans )
        
        # Process page number.
        if self.use_paging:
            if 'page' in kwargs:
                if kwargs['page'] == 'all':
                    page_num = 0 
                else:
                    page_num = int( kwargs['page'] )
            else:
                page_num = 1
                
            if page_num == 0:
                # Show all rows in page.
                total_num_rows = query.count()
                num_pages = 1
            else:
                # Show a limited number of rows. Before modifying query, get the total number of rows that query 
                # returns so that the total number of pages can be computed.
                total_num_rows = query.count()
                query = query.limit( self.num_rows_per_page ).offset( ( page_num-1 ) * self.num_rows_per_page )
                num_pages = int ( math.ceil( float( total_num_rows ) / self.num_rows_per_page ) )
        else:
            # Defaults.
            page_num = 1
            num_pages = 1
        
        
        # Preserve grid state: save current filter and sort key.
        if self.preserve_state:
            pref_name = unicode( self.__class__.__name__ + self.cur_filter_pref_name )
            trans.get_user().preferences[pref_name] = unicode( to_json_string( cur_filter_dict ) )
            
            if sort_key:
                pref_name = unicode( self.__class__.__name__ + self.cur_sort_key_pref_name )
                trans.get_user().preferences[pref_name] = unicode( to_json_string( sort_key ) )
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
                                    cur_page_num = page_num,
                                    num_pages = num_pages,
                                    default_filter_dict=self.default_filter,
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
    def __init__( self, label, key=None, model_class=None, method=None, format=None, link=None, attach_popup=False, visible=True, ncells=1, 
                    # Valid values for filterable are ['default', 'advanced', None]
                    filterable=None ):
        self.label = label
        self.key = key
        self.model_class = model_class
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
        
# Generic column that employs freetext and, hence, supports freetext, case-independent filtering.
class TextColumn( GridColumn ):
    def filter( self, db_session, query, column_filter ):
        """ Modify query to filter using free text, case independence. """
        if column_filter == "All":
            pass
        elif column_filter:
            query = query.filter( self.get_filter( column_filter ) )
        return query
    def get_filter( self, column_filter ):
        """ Returns a SQLAlchemy criterion derived from column_filter. """
        # This is a pretty ugly way to get the key attribute of model_class. TODO: Can this be fixed?
        model_class_key_field = eval( "self.model_class." + self.key )
        
        if isinstance( column_filter, basestring ):
            return func.lower( model_class_key_field ).like( "%" + column_filter.lower() + "%" )
        elif isinstance( column_filter, list ):
            clause_list = []
            for filter in column_filter:
                clause_list.append( func.lower( model_class_key_field ).like( "%" + filter.lower() + "%" ) )
            return and_( *clause_list )

# Generic column that supports tagging.        
class TagsColumn( TextColumn ):
    def __init__( self, col_name, key, model_class, model_tag_association_class, filterable ):
        GridColumn.__init__(self, col_name, key=key, model_class=model_class, filterable=filterable)
        self.model_tag_association_class = model_tag_association_class
        # Tags cannot be sorted.
        self.sortable = False
        self.tag_elt_id_gen = 0
    def get_value( self, trans, grid, item ):
        self.tag_elt_id_gen += 1
        elt_id="tagging-elt" + str( self.tag_elt_id_gen )
        div_elt = "<div id=%s></div>" % elt_id
        return div_elt + trans.fill_template( "/tagging_common.mako", trans=trans, tagged_item=item, 
                                                elt_id = elt_id, in_form="true", input_size="20", tag_click_fn="add_tag_to_grid_filter" )
    def filter( self, db_session, query, column_filter ):
        """ Modify query to filter model_class by tag. Multiple filters are ANDed. """
        if column_filter == "All":
            pass
        elif column_filter:
            query = query.filter( self.get_filter( column_filter ) )
        return query
    def get_filter( self, column_filter ):
            # Parse filter to extract multiple tags.
            tag_handler = TagHandler()
            if isinstance( column_filter, list ):
                # Collapse list of tags into a single string; this is redundant but effective. TODO: fix this by iterating over tags.
                column_filter = ",".join( column_filter )
            raw_tags = tag_handler.parse_tags( column_filter.encode("utf-8") )
            clause_list = []
            for name, value in raw_tags.items():
                if name:
                    # Search for tag names.
                    clause_list.append( self.model_class.tags.any( func.lower( self.model_tag_association_class.user_tname ).like( "%" + name.lower() + "%" ) ) )
                    if value:
                        # Search for tag values.
                        clause_list.append( self.model_class.tags.any( func.lower( self.model_tag_association_class.user_value ).like( "%" + value.lower() + "%" ) ) )
            return and_( *clause_list )
            
# Column that performs multicolumn filtering.
class MulticolFilterColumn( TextColumn ):
    def __init__( self, col_name, cols_to_filter, key, visible, filterable="default" ):
        GridColumn.__init__( self, col_name, key=key, visible=visible, filterable=filterable)
        self.cols_to_filter = cols_to_filter
    def filter( self, db_session, query, column_filter ):
        """ Modify query to filter model_class by tag. Multiple filters are ANDed. """
        if column_filter == "All":
            return query
        if isinstance( column_filter, list):
            clause_list = []
            for filter in column_filter:
                part_clause_list = []
                for column in self.cols_to_filter:
                    part_clause_list.append( column.get_filter( filter ) )
                clause_list.append( or_( *part_clause_list ) )
            complete_filter = and_( *clause_list )
        else:
            clause_list = []
            for column in self.cols_to_filter:
                clause_list.append( column.get_filter( column_filter ) )
            complete_filter = or_( *clause_list )
        
        return query.filter( complete_filter )

class GridOperation( object ):
    def __init__( self, label, key=None, condition=None, allow_multiple=True, allow_popup=True, target=None, url_args=None ):
        self.label = label
        self.key = key
        self.allow_multiple = allow_multiple
        self.allow_popup = allow_popup
        self.condition = condition
        self.target = target
        self.url_args = url_args
    def get_url_args( self, item ):
        if self.url_args:
            temp = dict( self.url_args )
            temp['id'] = item.id
            return temp
        else:
            return dict( operation=self.label, id=item.id )
        
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
        
