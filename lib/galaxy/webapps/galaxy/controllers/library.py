import logging
from galaxy import model, util
from galaxy import web
from galaxy.model.orm import and_, not_, or_
from galaxy.web.base.controller import BaseUIController
from galaxy.web.framework.helpers import grids
from library_common import get_comptypes, lucene_search, whoosh_search


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
        NameColumn( "Data library name",
                    key="name",
                    link=( lambda library: dict( operation="browse", id=library.id ) ),
                    attach_popup=False,
                    filterable="advanced" ),
        DescriptionColumn( "Data library description",
                           key="description",
                           attach_popup=False,
                           filterable="advanced" ),
    ]
    columns.append( grids.MulticolFilterColumn( "search dataset name, info, message, dbkey",
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


class Library( BaseUIController ):

    library_list_grid = LibraryListGrid()

    
    @web.expose
    def list( self, trans, **kwd ):
        params = util.Params( kwd )
        # define app configuration for generic mako template
        app = {
            'jscript'       : "galaxy.library"
        }
        # fill template
        return trans.fill_template('galaxy.panels.mako', config = {'app' : app})

    @web.expose
    def index( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        default_action = params.get( 'default_action', None )
        return trans.fill_template( "/library/index.mako",
                                    default_action=default_action,
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
        if 'f-free-text-search' in kwd:
            search_term = kwd[ "f-free-text-search" ]
            if trans.app.config.enable_lucene_library_search:
                indexed_search_enabled = True
                search_url = trans.app.config.config_dict.get( "fulltext_url", "" )
                if search_url:
                    indexed_search_enabled = True
                    status, message, lddas = lucene_search( trans, 'library', search_term, search_url, **kwd )
            elif trans.app.config.enable_whoosh_library_search:
                indexed_search_enabled = True
                status, message, lddas = whoosh_search( trans, 'library', search_term, **kwd )
            else:
                indexed_search_enabled = False
            if indexed_search_enabled:
                comptypes = get_comptypes( trans )
                show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
                use_panels = util.string_as_bool( kwd.get( 'use_panels', False ) )
                return trans.fill_template( '/library/common/library_dataset_search_results.mako',
                                            cntrller='library',
                                            search_term=search_term,
                                            comptypes=comptypes,
                                            lddas=lddas,
                                            current_user_roles=trans.get_current_user_roles(),
                                            show_deleted=show_deleted,
                                            use_panels=use_panels,
                                            message=message,
                                            status=status )
        # Render the list view
        return self.library_list_grid( trans, **kwd )
