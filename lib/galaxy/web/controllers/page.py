from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, grids
from galaxy.util.sanitize_html import sanitize_html
from galaxy.util.odict import odict

import re

VALID_SLUG_RE = re.compile( "^[a-z0-9\-]+$" )

def format_bool( b ):
    if b:
        return "yes"
    else:
        return ""

class PageListGrid( grids.Grid ):
    # Grid definition
    use_panels = True
    title = "Pages"
    model_class = model.Page
    default_filter = { "published" : "All"}
    default_sort_key = "-create_time"
    columns = [
        grids.TextColumn( "Title", key="title", model_class=model.Page, attach_popup=True, filterable="standard" ),
        PublicURLColumn( "Public URL" ),
        grids.GridColumn( "Published", key="published", format=format_bool, filterable="standard" ),
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
    ]
    global_actions = [
        grids.GridAction( "Add new page", dict( action='create' ) )
    ]
    operations = [
        grids.GridOperation( "View", allow_multiple=False, url_args=dict( action='display') ),
        grids.GridOperation( "Edit name/id", allow_multiple=False, url_args=dict( action='edit') ),
        grids.GridOperation( "Edit content", allow_multiple=False, url_args=dict( action='edit_content') ),
        grids.GridOperation( "Delete" ),
        grids.GridOperation( "Publish", condition=( lambda item: not item.published ) ),
        grids.GridOperation( "Unpublish", condition=( lambda item: item.published ) ),
    ]
    def apply_default_filter( self, trans, query, **kwargs ):
        return query.filter_by( user=trans.user, deleted=False )
        
class PageAllPublishedGrid( grids.Grid ):
    # Grid definition
    use_panels = True
    use_async = True
    title = "Published Pages"
    model_class = model.Page
    default_sort_key = "-update_time"
    default_filter = dict( title="All", username="All" )
    columns = [
        PublicURLColumn( "Title", key="title", model_class=model.Page, filterable="advanced"),
        OwnerColumn( "Owner", key="username", model_class=model.User, filterable="advanced", sortable=False ), 
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago )
    ]
    columns.append( 
        grids.MulticolFilterColumn(  
        "Search", 
        cols_to_filter=[ columns[0], columns[1] ], 
        key="free-text-search", visible=False, filterable="standard" )
                )
    def build_initial_query( self, session ):
        # Join so that searching history.user makes sense.
        return session.query( self.model_class ).join( model.User.table )
    def apply_default_filter( self, trans, query, **kwargs ):
        return query.filter( self.model_class.deleted==False ).filter( self.model_class.published==True )
        
class HistorySelectionGrid( grids.Grid ):
    # Custom columns.
    class NameColumn( grids.TextColumn ):
        def get_value(self, trans, grid, history):
            return history.get_display_name()
            
    class DeletedColumn( grids.GridColumn ):
       def get_accepted_filters( self ):
           """ Returns a list of accepted filters for this column. """
           accepted_filter_labels_and_vals = { "active" : "False", "deleted" : "True", "all": "All" }
           accepted_filters = []
           for label, val in accepted_filter_labels_and_vals.items():
               args = { self.key: val }
               accepted_filters.append( grids.GridColumnFilter( label, args) )
           return accepted_filters
           
    class SharingColumn( grids.GridColumn ):
        def filter( self, db_session, user, query, column_filter ):
            """ Modify query to filter histories by sharing status. """
            if column_filter == "All":
                pass
            elif column_filter:
                if column_filter == "private":
                    query = query.filter( model.History.users_shared_with == None )
                    query = query.filter( model.History.importable == False )
                elif column_filter == "shared":
                    query = query.filter( model.History.users_shared_with != None )
                elif column_filter == "importable":
                    query = query.filter( model.History.importable == True )
            return query
        def get_accepted_filters( self ):
            """ Returns a list of accepted filters for this column. """
            accepted_filter_labels_and_vals = odict()
            accepted_filter_labels_and_vals["private"] = "private"
            accepted_filter_labels_and_vals["shared"] = "shared"
            accepted_filter_labels_and_vals["importable"] = "importable"
            accepted_filter_labels_and_vals["all"] = "All"
            accepted_filters = []
            for label, val in accepted_filter_labels_and_vals.items():
                args = { self.key: val }
                accepted_filters.append( grids.GridColumnFilter( label, args) )
            return accepted_filters
    
    # Grid definition.
    title = "Saved Histories"
    template = "/page/select_histories_grid.mako"
    async_template = "/page/select_histories_grid_async.mako" 
    model_class = model.History
    default_filter = { "deleted" : "False" , "shared" : "All" }
    default_sort_key = "-update_time"
    use_async = True
    use_paging = True
    num_rows_per_page = 10
    columns = [
        NameColumn( "Name", key="name", model_class=model.History, filterable="advanced" ),
        grids.IndividualTagsColumn( "Tags", "tags", model.History, model.HistoryTagAssociation, filterable="advanced"),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        # Columns that are valid for filtering but are not visible.
        DeletedColumn( "Deleted", key="deleted", visible=False, filterable="advanced" ),
        SharingColumn( "Shared", key="shared", visible=False, filterable="advanced" ),
    ]
    columns.append( 
        grids.MulticolFilterColumn(  
        "Search", 
        cols_to_filter=[ columns[0], columns[1] ], 
        key="free-text-search", visible=False, filterable="standard" )
                )
    def apply_default_filter( self, trans, query, **kwargs ):
        return query.filter_by( user=trans.user, purged=False )

class PageController( BaseController ):
    
    _page_list = PageListGrid()
    _all_published_list = PageAllPublishedGrid()
    _history_selection_grid = HistorySelectionGrid()
    
    @web.expose
    @web.require_login()  
    def index( self, trans, *args, **kwargs ):
        # Handle operation
        if 'operation' in kwargs and 'id' in kwargs:
            session = trans.sa_session
            operation = kwargs['operation'].lower()
            ids = util.listify( kwargs['id'] )
            for id in ids:
                item = session.query( model.Page ).get( trans.security.decode_id( id ) )
                if operation == "delete":
                    item.deleted = True
                elif operation == "publish":
                    item.published = True
                elif operation == "unpublish":
                    item.published = False
            session.flush()
        # Build grid
        grid = self._page_list( trans, *args, **kwargs )
        # Render grid wrapped in panels
        return trans.fill_template( "page/index.mako", grid=grid )
             
    @web.expose
    def list_published( self, trans, *args, **kwargs ):
        grid = self._all_published_list( trans, *args, **kwargs )
        if 'async' in kwargs:
            return grid
        else:
            # Render grid wrapped in panels
            return trans.fill_template( "page/index.mako", grid=grid )

             
    @web.expose
    @web.require_login( "create pages" )
    def create( self, trans, page_title="", page_slug="" ):
        """
        Create a new page
        """
        user = trans.get_user()
        page_title_err = page_slug_err = ""
        if trans.request.method == "POST":
            if not page_title:
                page_title_err = "Page name is required"
            elif not page_slug:
                page_slug_err = "Page id is required"
            elif not VALID_SLUG_RE.match( page_slug ):
                page_slug_err = "Page identifier must consist of only lowercase letters, numbers, and the '-' character"
            elif trans.sa_session.query( model.Page ).filter_by( user=user, slug=page_slug, deleted=False ).first():
                page_slug_err = "Page id must be unique"
            else:
                # Create the new stored workflow
                page = model.Page()
                page.title = page_title
                page.slug = page_slug
                page.user = user
                # And the first (empty) workflow revision
                page_revision = model.PageRevision()
                page_revision.title = page_title
                page_revision.page = page
                page.latest_revision = page_revision
                page_revision.content = ""
                # Persist
                session = trans.sa_session
                session.add( page )
                session.flush()
                # Display the management page
                ## trans.set_message( "Page '%s' created" % page.title )
                return trans.response.send_redirect( web.url_for( action='index' ) )
        return trans.show_form( 
            web.FormBuilder( web.url_for(), "Create new page", submit_text="Submit" )
                .add_text( "page_title", "Page title", value=page_title, error=page_title_err )
                .add_text( "page_slug", "Page identifier", value=page_slug, error=page_slug_err,
                           help="""A unique identifier that will be used for
                                public links to this page. A default is generated
                                from the page title, but can be edited. This field
                                must contain only lowercase letters, numbers, and
                                the '-' character.""" ),
            template="page/create.mako" )
        
    @web.expose
    @web.require_login( "create pages" )
    def edit( self, trans, id, page_title="", page_slug="" ):
        """
        Create a new page
        """
        encoded_id = id
        id = trans.security.decode_id( id )
        session = trans.sa_session
        page = session.query( model.Page ).get( id )
        user = trans.user
        assert page.user == user
        page_title_err = page_slug_err = ""
        if trans.request.method == "POST":
            if not page_title:
                page_title_err = "Page name is required"
            elif not page_slug:
                page_slug_err = "Page id is required"
            elif not VALID_SLUG_RE.match( page_slug ):
                page_slug_err = "Page identifier must consist of only lowercase letters, numbers, and the '-' character"
            elif page_slug == page.slug or trans.sa_session.query( model.Page ).filter_by( user=user, slug=page_slug, deleted=False ).first():
                page_slug_err = "Page id must be unique"
            else:
                page.title = page_title
                page.slug = page_slug
                session.flush()
                # Display the management page
                return trans.response.send_redirect( web.url_for( action='index' ) )
        else:
            page_title = page.title
            page_slug = page.slug
        return trans.show_form( 
            web.FormBuilder( web.url_for( id=encoded_id ), "Edit page attributes", submit_text="Submit" )
                .add_text( "page_title", "Page title", value=page_title, error=page_title_err )
                .add_text( "page_slug", "Page identifier", value=page_slug, error=page_slug_err,
                           help="""A unique identifier that will be used for
                                public links to this page. A default is generated
                                from the page title, but can be edited. This field
                                must contain only lowercase letters, numbers, and
                                the '-' character.""" ),
            template="page/create.mako" )
        
    @web.expose
    @web.require_login( "edit pages" )
    def edit_content( self, trans, id ):
        """
        Render the main page editor interface. 
        """
        id = trans.security.decode_id( id )
        page = trans.sa_session.query( model.Page ).get( id )
        assert page.user == trans.user
        return trans.fill_template( "page/editor.mako", page=page )
        
    @web.expose
    @web.require_login() 
    def save( self, trans, id, content ):
        id = trans.security.decode_id( id )
        page = trans.sa_session.query( model.Page ).get( id )
        assert page.user == trans.user
        # Sanitize content
        content = sanitize_html( content, 'utf-8', 'text/html' )
        # Add a new revision to the page with the provided content
        page_revision = model.PageRevision()
        page_revision.title = page.title
        page_revision.page = page
        page.latest_revision = page_revision
        page_revision.content = content
        trans.sa_session.flush()
        
    @web.expose
    @web.require_login()  
    def display( self, trans, id ):
        id = trans.security.decode_id( id )
        page = trans.sa_session.query( model.Page ).get( id )
        if page.user is not trans.user:
            error( "Page is not owned by current user" )
        return trans.fill_template( "page/display.mako", page=page )
        
    @web.expose
    def display_by_username_and_slug( self, trans, username, slug ):
        session = trans.sa_session
        user = session.query( model.User ).filter_by( username=username ).first()
        if user is None:
            raise web.httpexceptions.HTTPNotFound()
        page = trans.sa_session.query( model.Page ).filter_by( user=user, slug=slug, deleted=False, published=True ).first()
        if page is None:
            raise web.httpexceptions.HTTPNotFound()
        return trans.fill_template( "page/display.mako", page=page )
        
    @web.expose
    @web.require_login("select a history from saved histories")
    def list_histories_for_selection( self, trans, **kwargs ):
        """ Returns HTML that enables a user to select one or more histories. """
        # Render the list view
        return self._history_selection_grid( trans, **kwargs )
        
    @web.expose
    @web.require_login("get annotation table for history")
    def get_history_annotation_table( self, trans, id ):
        """ Returns HTML for an annotation table for a history. """
        
        # TODO: users should be able to annotate a history if they own it, it is importable, or it is shared with them. This only
        # returns a history if a user owns it.
        history = self.get_history( trans, id, True )
        
        if history:
            # TODO: Query taken from root/history; it should be moved either into history or trans object
            # so that it can reused.
            query = trans.sa_session.query( model.HistoryDatasetAssociation ) \
                .filter( model.HistoryDatasetAssociation.history == history ) \
                .options( eagerload( "children" ) ) \
                .join( "dataset" ).filter( model.Dataset.purged == False ) \
                .options( eagerload_all( "dataset.actions" ) ) \
                .order_by( model.HistoryDatasetAssociation.hid )
            # For now, do not show deleted datasets.
            show_deleted = False
            if not show_deleted:
                query = query.filter( model.HistoryDatasetAssociation.deleted == False )
            return trans.fill_template( "page/history_annotation_table.mako", history=history, datasets=query.all(), show_deleted=False )
            
    @web.expose
    def get_editor_iframe( self, trans ):
        """ Returns the document for the page editor's iframe. """
        return trans.fill_template( "page/wymiframe.mako" )
        