import sys
from galaxy import util
from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
# Older py compatibility
try:
    set()
except:
    from sets import Set as set

import logging
log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

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
    model_class = model.Library
    template='/admin/library/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Library Name",
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
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        StatusColumn( "Status", attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        DeletedColumn( "Deleted", key="deleted", visible=False, filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
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
    def build_initial_query( self, session ):
        return session.query( self.model_class )

class LibraryAdmin( BaseController ):

    library_list_grid = LibraryListGrid()

    @web.expose
    @web.require_admin
    def browse_libraries( self, trans, **kwargs ):
        if 'operation' in kwargs:
            operation = kwargs['operation'].lower()
            if operation == "browse":
                return trans.response.send_redirect( web.url_for( controller='library_common',
                                                                  action='browse_library',
                                                                  cntrller='library_admin',
                                                                  **kwargs ) )
        # Render the list view
        return self.library_list_grid( trans, **kwargs )
    @web.expose
    @web.require_admin
    def create_library( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'new', False ):
            library = trans.app.model.Library( name = util.restore_text( params.name ), 
                                               description = util.restore_text( params.description ) )
            root_folder = trans.app.model.LibraryFolder( name = util.restore_text( params.name ), description = "" )
            library.root_folder = root_folder
            trans.sa_session.add_all( ( library, root_folder ) )
            trans.sa_session.flush()
            msg = "The new library named '%s' has been created" % library.name
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller='library_admin',
                                                              id=trans.security.encode_id( library.id ),
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='done' ) )
        return trans.fill_template( '/admin/library/new_library.mako', msg=msg, messagetype=messagetype )
    @web.expose
    @web.require_admin
    def purge_library( self, trans, **kwd ):
        # TODO: change this function to purge_library_item, behaving similar to delete_library_item
        # assuming we want the ability to purge libraries.
        # This function is currently only used by the functional tests.
        params = util.Params( kwd )
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
            msg = "Library '%s' has not been marked deleted, so it cannot be purged" % ( library.name )
            return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                              action='browse_libraries',
                                                              message=util.sanitize_text( msg ),
                                                              status='error' ) )
        else:
            purge_folder( library.root_folder )
            library.purged = True
            trans.sa_session.add( library )
            trans.sa_session.flush()
            msg = "Library '%s' and all of its contents have been purged, datasets will be removed from disk via the cleanup_datasets script" % library.name
            return trans.response.send_redirect( web.url_for( controller='library_admin',
                                                              action='browse_libraries',
                                                              message=util.sanitize_text( msg ),
                                                              status='done' ) )   
    @web.expose
    @web.require_admin
    def delete_library_item( self, trans, library_id, library_item_id, library_item_type, **kwd ):
        # This action will handle deleting all types of library items.  State is saved for libraries and
        # folders ( i.e., if undeleted, the state of contents of the library or folder will remain, so previously
        # deleted / purged contents will have the same state ).  When a library or folder has been deleted for
        # the amount of time defined in the cleanup_datasets.py script, the library or folder and all of its
        # contents will be purged.  The association between this method and the cleanup_datasets.py script
        # enables clean maintenance of libraries and library dataset disk files.  This is also why the following
        # 3 objects, and not any of the associations ( the cleanup_datasets.py scipot handles everything else ).
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        library_item_types = { 'library': trans.app.model.Library,
                               'folder': trans.app.model.LibraryFolder,
                               'library_dataset': trans.app.model.LibraryDataset }
        if library_item_type not in library_item_types:
            msg = 'Bad library_item_type specified: %s' % str( library_item_type )
            messagetype = 'error'
        else:
            if library_item_type == 'library_dataset':
                library_item_desc = 'Dataset'
            else:
                library_item_desc = library_item_type.capitalize()
            library_item = trans.sa_session.query( library_item_types[ library_item_type ] ).get( trans.security.decode_id( library_item_id ) )
            library_item.deleted = True
            trans.sa_session.add( library_item )
            trans.sa_session.flush()
            msg = util.sanitize_text( "%s '%s' has been marked deleted" % ( library_item_desc, library_item.name ) )
            messagetype = 'done'
        if library_item_type == 'library':
            return self.browse_libraries( trans, message=msg, status=messagetype )
        else:
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller='library_admin',
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              msg=msg,
                                                              messagetype=messagetype ) )
    @web.expose
    @web.require_admin
    def undelete_library_item( self, trans, library_id, library_item_id, library_item_type, **kwd ):
        # This action will handle undeleting all types of library items
        show_deleted = util.string_as_bool( kwd.get( 'show_deleted', False ) )
        library_item_types = { 'library': trans.app.model.Library,
                               'folder': trans.app.model.LibraryFolder,
                               'library_dataset': trans.app.model.LibraryDataset }
        if library_item_type not in library_item_types:
            msg = 'Bad library_item_type specified: %s' % str( library_item_type )
            status = ERROR
        else:
            if library_item_type == 'library_dataset':
                library_item_desc = 'Dataset'
            else:
                library_item_desc = library_item_type.capitalize()
            library_item = trans.sa_session.query( library_item_types[ library_item_type ] ).get( trans.security.decode_id( library_item_id ) )
            if library_item.purged:
                msg = '%s %s has been purged, so it cannot be undeleted' % ( library_item_desc, library_item.name )
                status = ERROR
            else:
                library_item.deleted = False
                trans.sa_session.add( library_item )
                trans.sa_session.flush()
                msg = util.sanitize_text( "%s '%s' has been marked undeleted" % ( library_item_desc, library_item.name ) )
                status = SUCCESS
        if library_item_type == 'library':
            return self.browse_libraries( trans, message=msg, status=status )
        else:
            return trans.response.send_redirect( web.url_for( controller='library_common',
                                                              action='browse_library',
                                                              cntrller='library_admin',
                                                              id=library_id,
                                                              show_deleted=show_deleted,
                                                              msg=msg,
                                                              messagetype=status ) )
    @web.expose
    @web.require_admin
    def upload_library_dataset( self, trans, library_id, folder_id, **kwd ):
        return trans.webapp.controllers[ 'library_common' ].upload_library_dataset( trans, 'library_admin', library_id, folder_id, **kwd )
