from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, grids
from galaxy.util.sanitize_html import sanitize_html

import re

VALID_SLUG_RE = re.compile( "^[a-z0-9\-]+$" )

def format_bool( b ):
    if b:
        return "yes"
    else:
        return ""

class PublicURLColumn( grids.GridColumn ):
    def get_value( self, trans, grid, item ):
        username = trans.user.username or "???"
        return username + "/" + item.slug
    def get_link( self, trans, grid, item ):
        if trans.user.username:
            return dict( action='display_by_username_and_slug', username=item.user.username, slug=item.slug )
        else:
            return None
        
class OwnerColumn( grids.GridColumn ):
    def get_value( self, trans, grid, item ):
        return item.user.username

class PageListGrid( grids.Grid ):
    # Grid definition
    use_panels = True
    title = "Your pages"
    model_class = model.Page
    default_sort_key = "-create_time"
    columns = [
        grids.GridColumn( "Title", key="title", attach_popup=True ),
        PublicURLColumn( "Public URL" ),
        grids.GridColumn( "Published", key="published", format=format_bool ),
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
    title = "Published pages from all users"
    model_class = model.Page
    default_sort_key = "-create_time"
    columns = [
        grids.GridColumn( "Title", key="title" ),
        PublicURLColumn( "Public URL" ),
        OwnerColumn( "Published by" ), 
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
    ]
    def apply_default_filter( self, trans, query, **kwargs ):
        return query.filter_by( deleted=False, published=True )
        
# Custom column types
class NameColumn( grids.GridColumn ):
    def __init( self, key, link, attach_popup, filterable ):
        grids.GridColumn.__init__(self, key, link, attach_popup)

    def get_value( self, trans, grid, history ):
        return history.get_display_name()

    def filter( self, db_session, query, column_filter ):
        """ Modify query to filter histories by name. """
        if column_filter == "All":
            pass
        elif column_filter:
            query = query.filter( func.lower( History.name ).like( "%" + column_filter.lower() + "%" ) )
        return query
    def get_accepted_filters( self ):
           """ Returns a list of accepted filters for this column. """
           accepted_filter_labels_and_vals = odict()
           accepted_filter_labels_and_vals["FREETEXT"] = "FREETEXT"
           accepted_filters = []
           for label, val in accepted_filter_labels_and_vals.iteritems():
               args = { self.key: val }
               accepted_filters.append( grids.GridColumnFilter( label, args) )
           return accepted_filters
           
class TagsColumn( grids.GridColumn ):
   def __init__( self, col_name, key, filterable ):
       grids.GridColumn.__init__(self, col_name, key=key, filterable=filterable)
       # Tags cannot be sorted.
       self.sortable = False
       self.tag_elt_id_gen = 0
   def get_value( self, trans, grid, history ):
       self.tag_elt_id_gen += 1
       elt_id="tagging-elt" + str( self.tag_elt_id_gen )
       div_elt = "<div id=%s></div>" % elt_id
       return div_elt + trans.fill_template( "/tagging_common.mako", trans=trans, tagged_item=history, 
                                               elt_id = elt_id, in_form="true", input_size="20", tag_click_fn="add_tag_to_grid_filter" )
   def filter( self, db_session, query, column_filter ):
       """ Modify query to filter histories by tag. """
       if column_filter == "All":
           pass
       elif column_filter:
           # Parse filter to extract multiple tags.
           tag_handler = TagHandler()
           raw_tags = tag_handler.parse_tags( column_filter.encode("utf-8") )
           for name, value in raw_tags.items():
               if name:
                   # Search for tag names.
                   query = query.filter( History.tags.any( func.lower( model.HistoryTagAssociation.user_tname ).like( "%" + name.lower() + "%" ) ) )
                   if value:
                       # Search for tag values.
                       query = query.filter( History.tags.any( func.lower( model.HistoryTagAssociation.user_value ).like( "%" + value.lower() + "%" ) ) )
       return query
   def get_accepted_filters( self ):
       """ Returns a list of accepted filters for this column. """
       accepted_filter_labels_and_vals = odict()
       accepted_filter_labels_and_vals["FREETEXT"] = "FREETEXT"
       accepted_filters = []
       for label, val in accepted_filter_labels_and_vals.iteritems():
           args = { self.key: val }
           accepted_filters.append( grids.GridColumnFilter( label, args) )
       return accepted_filters
       
class FreeTextSearchColumn( grids.GridColumn ):
   def filter( self, db_session, query, column_filter ):
       """ Modify query to search tags and history names. """
       if column_filter == "All":
           pass
       elif column_filter:
           # Build tags filter.
           tag_handler = TagHandler()
           raw_tags = tag_handler.parse_tags( column_filter.encode("utf-8") )
           tags_filter = None
           for name, value in raw_tags.items():
               if name:
                   # Search for tag names.
                   tags_filter = History.tags.any( func.lower( model.HistoryTagAssociation.user_tname ).like( "%" + name.lower() + "%" ) )
                   if value:
                       # Search for tag values.
                       tags_filter = and_( tags_filter, func.lower( History.tags.any( model.HistoryTagAssociation.user_value ).like( "%" + value.lower() + "%" ) ) )

           # Build history name filter.
           history_name_filter = func.lower( History.name ).like( "%" + column_filter.lower() + "%" )

           # Apply filters to query.
           if tags_filter:
               query = query.filter( or_( tags_filter, history_name_filter ) )
           else:
               query = query.filter( history_name_filter )
       return query
   def get_accepted_filters( self ):
       """ Returns a list of accepted filters for this column. """
       accepted_filter_labels_and_vals = odict()
       accepted_filter_labels_and_vals["FREETEXT"] = "FREETEXT"
       accepted_filters = []
       for label, val in accepted_filter_labels_and_vals.iteritems():
           args = { self.key: val }
           accepted_filters.append( grids.GridColumnFilter( label, args) )
       return accepted_filters
        
class HistorySelectionGrid( grids.Grid ):
    # Grid definition.
    template='/page/history_selection_grid.mako'
    title = "Saved Histories"
    model_class = model.History
    default_sort_key = "-update_time"
    columns = [
        NameColumn( "Name", key="name", filterable=True ),
        TagsColumn( "Tags", key="tags", filterable=True),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
        # Columns that are valid for filtering but are not visible.
        FreeTextSearchColumn( "Search", key="free-text-search", visible=False ) # Not filterable because it's the default search.
    ]

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
            operation = kwargs['operation']
            ids = util.listify( kwargs['id'] )
            for id in ids:
                item = session.query( model.Page ).get( trans.security.decode_id( id ) )
                if operation == "Delete":
                    item.deleted = True
                elif operation == "Publish":
                    item.published = True
                elif operation == "Unpublish":
                    item.published = False
            session.flush()
        # Build grid
        grid = self._page_list( trans, *args, **kwargs )
        # Render grid wrapped in panels
        return trans.fill_template( "page/index.mako", grid=grid )
             
    @web.expose
    @web.require_login()  
    def list_published( self, trans, *args, **kwargs ):
        grid = self._all_published_list( trans, *args, **kwargs )
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
        # Render the list view
        return self._history_selection_grid( trans, status=status, message=message, **kwargs )