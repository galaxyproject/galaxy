import urllib, urllib2

from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy.datatypes import sniff
from galaxy import model, util
from galaxy.util.odict import odict
import library_common

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
                    link=( lambda library: dict( operation="browse", id=library.id ) ),
                    attach_popup=False ),
        DescriptionColumn( "Description",
                           key="description",
                           attach_popup=False ),
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
        if 'f-free-text-search' in kwd:
            use_fulltext = trans.app.config.config_dict.get("use_fulltext", "False")
            search_url = trans.app.config.config_dict.get("fulltext_find_url", "")
            if use_fulltext.lower() not in ["false", "no"] and search_url:
                return self._fulltext_search(trans, kwd["f-free-text-search"],
                                             search_url, kwd)
        # Render the list view
        return self.library_list_grid( trans, **kwd )

    def _fulltext_search(self, trans, search_term, search_url, kwd):
        """Return display of results from a full-text search of data libraries.
        """
        full_url = "%s?%s" % (search_url, urllib.urlencode(
                              {"kwd" : search_term}))
        response = urllib2.urlopen(full_url)
        ids = util.json.from_json_string(response.read())["ids"]
        response.close()
        datasets = [trans.app.model.LibraryDataset.get(i) for i in ids]
        roles = trans.get_current_user_roles()
        library = _FullTextSearchLibrary(search_term, datasets)
        return trans.fill_template('/library/common/browse_library.mako',
                                   library=library,
                                   cntrller='library_search',
                                   current_user_roles=roles,
                                   created_ldda_ids=[], hidden_folder_ids=[],
                                   use_panels=False, show_deleted=False,
                                   comptypes=library_common.comptypes,
                                   message=util.restore_text(kwd.get('message', '')),
                                   status=kwd.get('status', 'done'))

class _FullTextSearchLibrary:
    """Mimic a library object with results retrieved from full-text search.
    """
    def __init__(self, search_term, datasets):
        self.name = "Full text search: %s" % search_term
        self.active_library_datasets = datasets
        self.id = "f-free-text-search=%s" % search_term
        self.actions = []
        self.root_folder = self
        self.parent = None
        self.deleted = False
        self.purged = False
        self.synopsis = None

    def get_info_association(self, restrict=False, inherited=False):
        return None, False
