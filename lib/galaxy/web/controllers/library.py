from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy.datatypes import sniff
from galaxy import model, util
from galaxy.util.odict import odict

log = logging.getLogger( __name__ )

class LibraryListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, library ):
            return library.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, library ):
            if library.description:
                return library.description
            return ''
    # Grid definition
    title = "Data Libraries"
    model_class = model.Library
    template='/library/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    model_class=model.Library,
                    link=( lambda library: dict( operation="browse", id=library.id ) ),
                    attach_popup=False,
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                           key="description",
                           model_class=model.Library,
                           attach_popup=False,
                           filterable="advanced" ),
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    standard_filters = []
    default_filter = dict( name="All", description="All", deleted="False", purged="False" )
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, trans, **kwargs ):
        return trans.sa_session.query( self.model_class ).filter( self.model_class.table.c.deleted == False )
    def apply_query_filter( self, trans, query, **kwd ):
        current_user_role_ids = [ role.id for role in trans.get_current_user_roles() ]
        library_access_action = trans.app.security_agent.permitted_actions.LIBRARY_ACCESS.action
        restricted_library_ids = [ lp.library_id for lp in trans.sa_session.query( trans.model.LibraryPermissions ) \
                                                                           .filter( trans.model.LibraryPermissions.table.c.action == library_access_action ) \
                                                                           .distinct() ]
        accessible_restricted_library_ids = [ lp.library_id for lp in trans.sa_session.query( trans.model.LibraryPermissions ) \
                                                                                      .filter( and_( trans.model.LibraryPermissions.table.c.action == library_access_action,
                                                                                                     trans.model.LibraryPermissions.table.c.role_id.in_( current_user_role_ids ) ) ) ]
        if not trans.user:
            # Filter to get only public libraries, a library whose id 
            # is not in restricted_library_ids is a public library
            return query.filter( not_( trans.model.Library.table.c.id.in_( restricted_library_ids ) ) )
        else:
            # Filter to get libraries accessible by the current user, get both 
            # public libraries and restricted libraries accessible by the current user.
            return query.filter( or_( not_( trans.model.Library.table.c.id.in_( restricted_library_ids ) ),
                                      trans.model.Library.table.c.id.in_( accessible_restricted_library_ids ) ) )
class Library( BaseController ):
    
    library_list_grid = LibraryListGrid()

    @web.expose
    def index( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        return trans.fill_template( "/library/index.mako",
                                    default_action=params.get( 'default_action', None ),
                                    message=message,
                                    status=status )
    @web.expose
    def browse_libraries( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "browse":
                return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                  action='browse_library',
                                                                  cntrller='library',
                                                                  **kwd ) )
        # Render the list view
        return self.library_list_grid( trans, **kwd )
