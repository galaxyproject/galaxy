import tarfile
from galaxy.web.base.controller import *
from galaxy.webapps.community import model
from galaxy.model.orm import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.web.form_builder import SelectField
from galaxy.model.item_attrs import UsesItemRatings
import logging
log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

class ItemRatings( UsesItemRatings ):
    """Overrides rate_item method since we also allow for comments"""
    def rate_item( self, trans, user, item, rating, comment='' ):
        """ Rate an item. Return type is <item_class>RatingAssociation. """
        item_rating = self.get_user_item_rating( trans.sa_session, user, item, webapp_model=trans.model )
        if not item_rating:
            # User has not yet rated item; create rating.
            item_rating_assoc_class = self._get_item_rating_assoc_class( item, webapp_model=trans.model )
            item_rating = item_rating_assoc_class()
            item_rating.user = trans.user
            item_rating.set_item( item )
            item_rating.rating = rating
            item_rating.comment = comment
            trans.sa_session.add( item_rating )
            trans.sa_session.flush()
        elif item_rating.rating != rating or item_rating.comment != comment:
            # User has previously rated item; update rating.
            item_rating.rating = rating
            item_rating.comment = comment
            trans.sa_session.add( item_rating )
            trans.sa_session.flush()
        return item_rating

class ToolListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            return tool.name
    class TypeColumn( grids.BooleanColumn ):
        def get_value( self, trans, grid, tool ):
            if tool.is_suite:
                return 'Suite'
            return 'Tool'
    class VersionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            return tool.version
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            return tool.description
    class CategoryColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            rval = '<ul>'
            if tool.categories:
                for tca in tool.categories:
                    rval += '<li><a href="browse_tools?operation=tools_by_category&id=%s&webapp=community">%s</a></li>' \
                        % ( trans.security.encode_id( tca.category.id ), tca.category.name )
            else:
                rval += '<li>not set</li>'
            rval += '</ul>'
            return rval
    class ToolCategoryColumn( grids.GridColumn ):
        def filter( self, trans, user, query, column_filter ):
            """Modify query to filter by category."""
            if column_filter == "All":
                pass
            return query.filter( model.Category.name == column_filter )
    class UserColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool ):
            if tool.user:
                return tool.user.username
            return 'no user'
    class EmailColumn( grids.TextColumn ):
        def filter( self, trans, user, query, column_filter ):
            if column_filter == 'All':
                return query
            return query.filter( and_( model.Tool.table.c.user_id == model.User.table.c.id,
                                       model.User.table.c.email == column_filter ) )
    # Grid definition
    title = "Tools"
    model_class = model.Tool
    template='/webapps/community/tool/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="Tool.name",
                    link=( lambda item: dict( operation="view_tool", id=item.id, webapp="community" ) ),
                    attach_popup=False ),
        DescriptionColumn( "Description",
                           key="description",
                           attach_popup=False ),
        VersionColumn( "Version",
                       key="version",
                       attach_popup=False,
                       filterable="advanced" ),
        CategoryColumn( "Category",
                        model_class=model.Category,
                        key="Category.name",
                        attach_popup=False ),
        UserColumn( "Uploaded By",
                     model_class=model.User,
                     link=( lambda item: dict( operation="tools_by_user", id=item.id, webapp="community" ) ),
                     attach_popup=False,
                     key="username" ),
        TypeColumn( "Type",
                     key="suite",
                     attach_popup=False ),
        grids.CommunityRatingColumn( "Average Rating",
                                     key="rating" ),
        # Columns that are valid for filtering but are not visible.
        EmailColumn( "Email",
                     model_class=model.User,
                     key="email",
                     visible=False ),
        ToolCategoryColumn( "Category",
                            model_class=model.Category,
                            key="Category.name",
                            visible=False )
    ]
    columns.append( grids.MulticolFilterColumn( "Search tool name, description, version", 
                                                cols_to_filter=[ columns[0], columns[1], columns[2] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = []
    standard_filters = []
    default_filter = {}
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( self.model_class ) \
                               .join( model.User.table ) \
                               .join( model.ToolEventAssociation.table ) \
                               .join( model.Event.table ) \
                               .outerjoin( model.ToolCategoryAssociation.table ) \
                               .outerjoin( model.Category.table )

class CategoryListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            return category.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            return category.description
    class ToolsColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            if category.tools:
                viewable_tools = 0
                for tca in category.tools:
                    viewable_tools += 1
                return viewable_tools
            return 0

    # Grid definition
    webapp = "community"
    title = "Categories"
    model_class = model.Category
    template='/webapps/community/category/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    link=( lambda item: dict( operation="tools_by_category", id=item.id, webapp="community" ) ),
                    attach_popup=False,
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                    key="description",
                    attach_popup=False,
                    filterable="advanced" ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted",
                             key="deleted",
                             visible=False,
                             filterable="advanced" ),
        ToolsColumn( "Tools",
                     model_class=model.Tool,
                     attach_popup=False )
    ]
    columns.append( grids.MulticolFilterColumn( "Search category name, description",
                                                cols_to_filter=[ columns[0], columns[1] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )

    # Override these
    global_actions = []
    operations = []
    standard_filters = []
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
                
class CommonController( BaseController, ItemRatings ):
    @web.expose
    def edit_tool( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              cntrller=cntrller,
                                                              message='Select a tool to edit',
                                                              status='error' ) )
        tool = get_tool( trans, id )
        can_edit = trans.app.security_agent.can_edit( trans.user, trans.user_is_admin(), cntrller, tool )
        if not can_edit:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              cntrller=cntrller,
                                                              message='You are not allowed to edit this tool',
                                                              status='error' ) )
        if params.get( 'edit_tool_button', False ):
            if params.get( 'in_categories', False ):
                in_categories = [ trans.sa_session.query( trans.app.model.Category ).get( x ) for x in util.listify( params.in_categories ) ]
                trans.app.security_agent.set_entity_category_associations( tools=[ tool ], categories=in_categories )
            else:
                # There must not be any categories associated with the tool
                trans.app.security_agent.set_entity_category_associations( tools=[ tool ], categories=[] )
            user_description = util.restore_text( params.get( 'user_description', '' ) )
            if user_description:
                tool.user_description = user_description
            else:
                tool.user_description = ''
            trans.sa_session.add( tool )
            trans.sa_session.flush()
            message = "Tool '%s' description and category associations have been saved" % tool.name
            return trans.response.send_redirect( web.url_for( controller='common',
                                                              action='edit_tool',
                                                              cntrller=cntrller,
                                                              id=id,
                                                              message=message,
                                                              status='done' ) )
        elif params.get( 'approval_button', False ):
            user_description = util.restore_text( params.get( 'user_description', '' ) )
            if user_description:
                tool.user_description = user_description
                if params.get( 'in_categories', False ):
                    in_categories = [ trans.sa_session.query( trans.app.model.Category ).get( x ) for x in util.listify( params.in_categories ) ]
                    trans.app.security_agent.set_entity_category_associations( tools=[ tool ], categories=in_categories )
                else:
                    # There must not be any categories associated with the tool
                    trans.app.security_agent.set_entity_category_associations( tools=[ tool ], categories=[] )
                trans.sa_session.add( tool )
                trans.sa_session.flush()
                # Move the state from NEW to WAITING
                event = trans.app.model.Event( state=trans.app.model.Tool.states.WAITING )
                tea = trans.app.model.ToolEventAssociation( tool, event )
                trans.sa_session.add_all( ( event, tea ) )
                trans.sa_session.flush()
                message = "Tool '%s' has been submitted for approval and can no longer be modified" % ( tool.name )
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='view_tool',
                                                                  cntrller=cntrller,
                                                                  id=id,
                                                                  message=message,
                                                                  status='done' ) )
            else:
                # The user_description field is required when submitting for approval
                message = 'A user description is required prior to approval.'
                status = 'error'
        in_categories = []
        out_categories = []
        for category in get_categories( trans ):
            if category in [ x.category for x in tool.categories ]:
                in_categories.append( ( category.id, category.name ) )
            else:
                out_categories.append( ( category.id, category.name ) )
        if tool.is_rejected:
            # Include the comments regarding the reason for rejection
            reason_for_rejection = tool.latest_event.comment
        else:
            reason_for_rejection = ''
        can_approve_or_reject = trans.app.security_agent.can_approve_or_reject( trans.user, trans.user_is_admin(), cntrller, tool )
        can_delete = trans.app.security_agent.can_delete( trans.user, trans.user_is_admin(), cntrller, tool )
        can_download = trans.app.security_agent.can_download( trans.user, trans.user_is_admin(), cntrller, tool )
        can_purge = trans.app.security_agent.can_purge( trans.user, trans.user_is_admin(), cntrller )
        can_upload_new_version = trans.app.security_agent.can_upload_new_version( trans.user, tool )
        can_view = trans.app.security_agent.can_view( trans.user, trans.user_is_admin(), cntrller, tool )
        return trans.fill_template( '/webapps/community/tool/edit_tool.mako',
                                    cntrller=cntrller,
                                    tool=tool,
                                    id=id,
                                    in_categories=in_categories,
                                    out_categories=out_categories,
                                    can_approve_or_reject=can_approve_or_reject,
                                    can_delete=can_delete,
                                    can_download=can_download,
                                    can_edit=can_edit,
                                    can_purge=can_purge,
                                    can_upload_new_version=can_upload_new_version,
                                    can_view=can_view,
                                    reason_for_rejection=reason_for_rejection,
                                    message=message,
                                    status=status )
    @web.expose
    def view_tool( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              cntrller=cntrller,
                                                              message='Select a tool to view',
                                                              status='error' ) )
        tool = get_tool( trans, id )
        can_view = trans.app.security_agent.can_view( trans.user, trans.user_is_admin(), cntrller, tool )
        if not can_view:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              cntrller=cntrller,
                                                              message='You are not allowed to view this tool',
                                                              status='error' ) )
        avg_rating, num_ratings = self.get_ave_item_rating_data( trans.sa_session, tool, webapp_model=trans.model )
        can_approve_or_reject = trans.app.security_agent.can_approve_or_reject( trans.user, trans.user_is_admin(), cntrller, tool )
        can_delete = trans.app.security_agent.can_delete( trans.user, trans.user_is_admin(), cntrller, tool )
        can_download = trans.app.security_agent.can_download( trans.user, trans.user_is_admin(), cntrller, tool )
        can_edit = trans.app.security_agent.can_edit( trans.user, trans.user_is_admin(), cntrller, tool )
        can_purge = trans.app.security_agent.can_purge( trans.user, trans.user_is_admin(), cntrller )
        can_rate = trans.app.security_agent.can_rate( trans.user, trans.user_is_admin(), cntrller, tool )
        can_upload_new_version = trans.app.security_agent.can_upload_new_version( trans.user, tool )
        categories = [ tca.category for tca in tool.categories ]
        display_reviews = util.string_as_bool( params.get( 'display_reviews', False ) )
        tool_file_contents = tarfile.open( tool.file_name, 'r' ).getnames()
        tra = self.get_user_item_rating( trans.sa_session, trans.user, tool, webapp_model=trans.model )
        visible_versions = trans.app.security_agent.get_visible_versions( trans.user, trans.user_is_admin(), cntrller, tool )
        if tool.is_rejected:
            # Include the comments regarding the reason for rejection
            reason_for_rejection = tool.latest_event.comment
        else:
            reason_for_rejection = ''
        return trans.fill_template( '/webapps/community/tool/view_tool.mako',
                                    avg_rating=avg_rating,
                                    categories=categories,
                                    can_approve_or_reject=can_approve_or_reject,
                                    can_delete=can_delete,
                                    can_download=can_download,
                                    can_edit=can_edit,
                                    can_purge=can_purge,
                                    can_rate=can_rate,
                                    can_upload_new_version=can_upload_new_version,
                                    can_view=can_view,
                                    cntrller=cntrller,
                                    display_reviews=display_reviews,
                                    num_ratings=num_ratings,
                                    reason_for_rejection=reason_for_rejection,
                                    tool=tool,
                                    tool_file_contents=tool_file_contents,
                                    tra=tra,
                                    visible_versions=visible_versions,
                                    message=message,
                                    status=status )
    @web.expose
    def delete_tool( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            message='Select a tool to delete'
            status='error'
        else:
            tool = get_tool( trans, id )
            if not trans.app.security_agent.can_delete( trans.user, trans.user_is_admin(), cntrller, tool ):
                return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                                  action='browse_tools',
                                                                  cntrller=cntrller,
                                                                  message='You are not allowed to delete this tool',
                                                                  status='error' ) )
            # Create a new event
            event = trans.model.Event( state=trans.model.Tool.states.DELETED )
            # Flush so we can get an event id
            trans.sa_session.add( event )
            trans.sa_session.flush()
            # Associate the tool with the event
            tea = trans.model.ToolEventAssociation( tool=tool, event=event )
            # Delete the tool, keeping state for categories, events and versions
            tool.deleted = True
            trans.sa_session.add_all( ( tool, tea ) )
            trans.sa_session.flush()
            # TODO: What if the tool has versions, should they all be deleted?
            message = "Tool '%s' version %s has been marked deleted" % ( tool.name, tool.version )
            status = 'done'
        return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                          action='browse_tools',
                                                          cntrller=cntrller,
                                                          message=message,
                                                          status=status ) )
    @web.expose
    def download_tool( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        id = params.get( 'id', None )
        if not id:
            return trans.response.send_redirect( web.url_for( controller='tool',
                                                              action='browse_tools',
                                                              cntrller=cntrller,
                                                              message='Select a tool to download',
                                                              status='error' ) )
        tool = get_tool( trans, id )
        if not trans.app.security_agent.can_download( trans.user, trans.user_is_admin(), cntrller, tool ):
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              cntrller=cntrller,
                                                              message='You are not allowed to download this tool',
                                                              status='error' ) )
        trans.response.set_content_type( tool.mimetype )
        trans.response.headers['Content-Length'] = int( os.stat( tool.file_name ).st_size )
        trans.response.headers['Content-Disposition'] = 'attachment; filename=%s' % tool.download_file_name
        return open( tool.file_name )
    @web.expose
    def upload_new_tool_version( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              cntrller=cntrller,
                                                              message='Select a tool to upload a new version',
                                                              status='error' ) )
        tool = get_tool( trans, id )
        if not trans.app.security_agent.can_upload_new_version( trans.user, tool ):
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              cntrller=cntrller,
                                                              message='You are not allowed to upload a new version of this tool',
                                                              status='error' ) )
        return trans.response.send_redirect( web.url_for( controller='tool_upload',
                                                          action='upload',
                                                          message=message,
                                                          status=status,
                                                          replace_id=id ) )
    @web.expose
    @web.require_login( "view tool history" )
    def view_tool_history( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              cntrller=cntrller,
                                                              message='Select a tool to view its history',
                                                              status='error' ) )
        tool = get_tool( trans, id )
        can_view = trans.app.security_agent.can_view( trans.user, trans.user_is_admin(), cntrller, tool )
        if not can_view:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              cntrller=cntrller,
                                                              message="You are not allowed to view this tool's history",
                                                              status='error' ) )
        can_approve_or_reject = trans.app.security_agent.can_approve_or_reject( trans.user, trans.user_is_admin(), cntrller, tool )
        can_edit = trans.app.security_agent.can_edit( trans.user, trans.user_is_admin(), cntrller, tool )
        can_delete = trans.app.security_agent.can_delete( trans.user, trans.user_is_admin(), cntrller, tool )
        can_download = trans.app.security_agent.can_download( trans.user, trans.user_is_admin(), cntrller, tool )
        events = [ tea.event for tea in tool.events ]
        events = [ ( event.state, time_ago( event.update_time ), event.comment ) for event in events ]
        return trans.fill_template( '/webapps/community/common/view_tool_history.mako', 
                                    cntrller=cntrller,
                                    events=events,
                                    tool=tool,
                                    can_approve_or_reject=can_approve_or_reject,
                                    can_edit=can_edit,
                                    can_delete=can_delete,
                                    can_download=can_download,
                                    can_view=can_view,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_login( "rate tools" )
    def rate_tool( self, trans, cntrller, **kwd ):
        """ Rate a tool and return updated rating data. """
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              cntrller=cntrller,
                                                              message='Select a tool to rate',
                                                              status='error' ) )
        tool = get_tool( trans, id )
        can_rate = trans.app.security_agent.can_rate( trans.user, trans.user_is_admin(), cntrller, tool )
        if not can_rate:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              cntrller=cntrller,
                                                              message="You are not allowed to rate this tool",
                                                              status='error' ) )
        if params.get( 'rate_button', False ):
            rating = int( params.get( 'rating', '0' ) )
            comment = util.restore_text( params.get( 'comment', '' ) )
            rating = self.rate_item( trans, trans.user, tool, rating, comment )
        avg_rating, num_ratings = self.get_ave_item_rating_data( trans.sa_session, tool, webapp_model=trans.model )
        can_approve_or_reject = trans.app.security_agent.can_approve_or_reject( trans.user, trans.user_is_admin(), cntrller, tool )
        can_edit = trans.app.security_agent.can_edit( trans.user, trans.user_is_admin(), cntrller, tool )
        can_delete = trans.app.security_agent.can_delete( trans.user, trans.user_is_admin(), cntrller, tool )
        can_download = trans.app.security_agent.can_download( trans.user, trans.user_is_admin(), cntrller, tool )
        display_reviews = util.string_as_bool( params.get( 'display_reviews', False ) )
        tra = self.get_user_item_rating( trans.sa_session, trans.user, tool, webapp_model=trans.model )
        return trans.fill_template( '/webapps/community/common/rate_tool.mako', 
                                    cntrller=cntrller,
                                    tool=tool,
                                    avg_rating=avg_rating,
                                    can_approve_or_reject=can_approve_or_reject,
                                    can_edit=can_edit,
                                    can_delete=can_delete,
                                    can_download=can_download,
                                    can_rate=can_rate,
                                    display_reviews=display_reviews,
                                    num_ratings=num_ratings,
                                    tra=tra,
                                    message=message,
                                    status=status )

## ---- Utility methods -------------------------------------------------------

def get_versions( item ):
    """Get all versions of item"""
    versions = [ item ]
    this_item = item
    while item.newer_version:
        versions.insert( 0, item.newer_version )
        item = item.newer_version
    item = this_item
    while item.older_version:
        versions.append( item.older_version[ 0 ] )
        item = item.older_version[ 0 ]
    return versions
def get_categories( trans ):
    """Get all categories from the database"""
    return trans.sa_session.query( trans.model.Category ) \
                           .filter( trans.model.Category.table.c.deleted==False ) \
                           .order_by( trans.model.Category.table.c.name ).all()
def get_category( trans, id ):
    """Get a category from the database"""
    return trans.sa_session.query( trans.model.Category ).get( trans.security.decode_id( id ) )
def get_tool( trans, id ):
    """Get a tool from the database"""
    return trans.sa_session.query( trans.model.Tool ).get( trans.security.decode_id( id ) )
def get_latest_versions_of_tools( trans ):
    """Get only the latest version of each tool from the database"""
    return trans.sa_session.query( trans.model.Tool ) \
                           .filter( trans.model.Tool.table.c.newer_version_id == None ) \
                           .order_by( trans.model.Tool.table.c.name )
def get_latest_versions_of_tools_by_state( trans, state ):
    """Get only the latest version of each tool whose state is the received state from the database"""
    tools = []
    for tool in trans.sa_session.query( trans.model.Tool ) \
                                .order_by( trans.model.Tool.table.c.name ):
        if tool.state == state:
            tools.append( tool )
    return tools
def get_event( trans, id ):
    """Get an event from the databse"""
    return trans.sa_session.query( trans.model.Event ).get( trans.security.decode_id( id ) )
def get_user( trans, id ):
    """Get a user from the database"""
    return trans.sa_session.query( trans.model.User ).get( trans.security.decode_id( id ) )
def get_repository( trans, id ):
    """Get a repository from the database via id"""
    return trans.sa_session.query( trans.model.Repository ).get( trans.security.decode_id( id ) )
def get_repository_by_name( trans, name ):
    """Get a repository from the database via name"""
    return trans.sa_session.query( app.model.Repository ).filter_by( name=name ).one()
def get_repository_tip( repository ):
    # The received repository must be a mercurial repository, not a db record.
    tip_changeset = repository.changelog.tip()
    tip_ctx = repository.changectx( tip_changeset )
    return "%s:%s" % ( str( tip_ctx.rev() ), tip_ctx.parents()[0] )
