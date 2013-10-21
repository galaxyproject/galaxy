import logging

import galaxy.model
import galaxy.util

from galaxy import web
from galaxy.web.base.controller import BaseUIController
from galaxy.web.framework.helpers import grids, time_ago
from library_common import get_comptypes, lucene_search, whoosh_search
# from galaxy.model.orm import *

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
    class StatusColumn( grids.GridColumn ):
        def get_value( self, trans, grid, library ):
            if library.purged:
                return "purged"
            elif library.deleted:
                return "deleted"
            return ""
    # Grid definition
    title = "Data Libraries"
    model_class = galaxy.model.Library
    template='/admin/library/grid.mako'
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
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        StatusColumn( "Status", attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted", key="deleted", visible=False, filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "search dataset name, info, message, dbkey",
                                                cols_to_filter=[ columns[0], columns[1] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    global_actions = [
        grids.GridAction( "Create new data library", dict( controller='library_admin', action='create_library' ) )
    ]
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True, purged=False ) ),
        grids.GridColumnFilter( "Purged", args=dict( purged=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    default_filter = dict( name="All", description="All", deleted="False", purged="False" )
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True

class LibraryAdmin( BaseUIController ):

    library_list_grid = LibraryListGrid()

    @web.expose
    @web.require_admin
    def browse_libraries( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "browse":
                return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                  action='browse_library',
                                                                  cntrller='library_admin',
                                                                  **kwd ) )
            elif operation == "delete":
                return self.delete_library( trans, **kwd )
            elif operation == "undelete":
                return self.undelete_library( trans, **kwd )
        self.library_list_grid.operations = []
        if 'f-deleted' in kwd:
            if kwd[ 'f-deleted' ] != 'All':
                if galaxy.util.string_as_bool( kwd[ 'f-deleted' ] ):
                    # We're viewing deleted data libraries, so add a GridOperation
                    # enabling one or more of them to be undeleted.
                    self.library_list_grid.operations = [
                        grids.GridOperation( "Undelete",
                                             condition=( lambda item: item.deleted ),
                                             allow_multiple=True,
                                             allow_popup=False,
                                             url_args=dict( webapp="galaxy" ) )
                    ]
                else:
                    # We're viewing active data libraries, so add a GridOperation
                    # enabling one or more of them to be deleted.
                    self.library_list_grid.operations = [
                        grids.GridOperation( "Delete",
                                             condition=( lambda item: not item.deleted ),
                                             allow_multiple=True,
                                             allow_popup=False,
                                             url_args=dict( webapp="galaxy" ) )
                    ]
        else:
            # We're viewing active data libraries, so add a GridOperation
            # enabling one or more of them to be deleted.
            self.library_list_grid.operations = [
                grids.GridOperation( "Delete",
                                     condition=( lambda item: not item.deleted ),
                                     allow_multiple=True,
                                     allow_popup=False,
                                     url_args=dict( webapp="galaxy" ) )
            ]
        if 'f-free-text-search' in kwd:
            search_term = kwd[ "f-free-text-search" ]
            if trans.app.config.enable_lucene_library_search:
                indexed_search_enabled = True
                search_url = trans.app.config.config_dict.get( "fulltext_find_url", "" )
                if search_url:
                    status, message, lddas = lucene_search( trans, 'library_admin', search_term, search_url, **kwd )
            elif trans.app.config.enable_whoosh_library_search:
                indexed_search_enabled = True
                status, message, lddas = whoosh_search( trans, 'library_admin', search_term, **kwd )
            else:
                indexed_search_enabled = False
            if indexed_search_enabled:
                comptypes = get_comptypes( trans )
                show_deleted = galaxy.util.string_as_bool( kwd.get( 'show_deleted', False ) )
                use_panels = galaxy.util.string_as_bool( kwd.get( 'use_panels', False ) )
                return trans.fill_template( '/library/common/library_dataset_search_results.mako',
                                            cntrller='library_admin',
                                            search_term=search_term,
                                            comptypes=comptypes,
                                            lddas=lddas,
                                            show_deleted=show_deleted,
                                            use_panels=use_panels,
                                            message=message,
                                            status=status )
        # Render the list view
        return self.library_list_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def create_library( self, trans, **kwd ):
        params = galaxy.util.Params( kwd )
        message = galaxy.util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if params.get( 'create_library_button', False ):
            name = galaxy.util.restore_text( params.get( 'name', 'No name' ) )
            description = galaxy.util.restore_text( params.get( 'description', '' ) )
            synopsis = galaxy.util.restore_text( params.get( 'synopsis', '' ) )
            if synopsis in [ 'None', None ]:
                synopsis = ''
            library = trans.app.model.Library( name=name, description=description, synopsis=synopsis )
            root_folder = trans.app.model.LibraryFolder( name=name, description='' )
            library.root_folder = root_folder
            trans.sa_session.add_all( ( library, root_folder ) )
            trans.sa_session.flush()
            message = "The new library named '%s' has been created" % library.name
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller='library_admin',
                                                              id=trans.security.encode_id( library.id ),
                                                              message=galaxy.util.sanitize_text( message ),
                                                              status='done' ) )
        return trans.fill_template( '/admin/library/new_library.mako', message=message, status=status )
    @web.expose
    @web.require_admin
    def delete_library( self, trans, id, **kwd  ):
        # Used by the Delete grid operation in the LibrarylistGrid.
        return trans.response.send_redirect( web.url_for( controller='library_common',
                                                          action='delete_library_item',
                                                          cntrller='library_admin',
                                                          library_id=id,
                                                          item_id=id,
                                                          item_type='library' ) )
    @web.expose
    @web.require_admin
    def undelete_library( self, trans, id, **kwd  ):
        # Used by the Undelete grid operation in the LibrarylistGrid.
        return trans.response.send_redirect( web.url_for( controller='library_common',
                                                          action='undelete_library_item',
                                                          cntrller='library_admin',
                                                          library_id=id,
                                                          item_id=id,
                                                          item_type='library' ) )
    @web.expose
    @web.require_admin
    def purge_library( self, trans, **kwd ):
        # TODO: change this function to purge_library_item, behaving similar to delete_library_item
        # assuming we want the ability to purge libraries.
        # This function is currently only used by the functional tests.
        params = galaxy.util.Params( kwd )
        library = trans.sa_session.query( trans.app.model.Library ).get( trans.security.decode_id( params.id ) )
        def purge_folder( library_folder ):
            for lf in library_folder.folders:
                purge_folder( lf )
            trans.sa_session.refresh( library_folder )
            for library_dataset in library_folder.datasets:
                trans.sa_session.refresh( library_dataset )
                ldda = library_dataset.library_dataset_dataset_association
                if ldda:
                    trans.sa_session.refresh( ldda )
                    dataset = ldda.dataset
                    trans.sa_session.refresh( dataset )
                    # If the dataset is not associated with any additional undeleted folders, then we can delete it.
                    # We don't set dataset.purged to True here because the cleanup_datasets script will do that for
                    # us, as well as removing the file from disk.
                    #if not dataset.deleted and len( dataset.active_library_associations ) <= 1: # This is our current ldda
                    dataset.deleted = True
                    ldda.deleted = True
                    trans.sa_session.add_all( ( dataset, ldda ) )
                library_dataset.deleted = True
                trans.sa_session.add( library_dataset )
            library_folder.deleted = True
            library_folder.purged = True
            trans.sa_session.add( library_folder )
            trans.sa_session.flush()
        if not library.deleted:
            message = "Library '%s' has not been marked deleted, so it cannot be purged" % ( library.name )
            return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                              action='browse_libraries',
                                                              message=galaxy.util.sanitize_text( message ),
                                                              status='error' ) )
        else:
            purge_folder( library.root_folder )
            library.purged = True
            trans.sa_session.add( library )
            trans.sa_session.flush()
            message = "Library '%s' and all of its contents have been purged, datasets will be removed from disk via the cleanup_datasets script" % library.name
            return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                              action='browse_libraries',
                                                              message=galaxy.util.sanitize_text( message ),
                                                              status='done' ) )
