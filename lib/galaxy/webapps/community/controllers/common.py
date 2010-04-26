from galaxy.web.base.controller import *
#from galaxy.web.controllers.admin import get_user, get_group, get_role
from galaxy.webapps.community import model
from galaxy.model.orm import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.web.form_builder import SelectField
import logging
log = logging.getLogger( __name__ )

class CommunityCommon( BaseController ):
    @web.expose
    def edit_tool( self, trans, cntrller, id=None, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        # Get the tool
        tool = None
        if id is not None:
            encoded_id = id
            id = trans.app.security.decode_id( id )
            tool = trans.sa_session.query( trans.model.Tool ).get( id )
        if tool is None:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              message='Please select a Tool to edit (the tool ID provided was invalid)',
                                                              status='error' ) )
        if params.save_button and ( params.file_data != '' or params.url != '' ):
            # TODO: call the upload method in the upload controller.
            message = 'Uploading new version not implemented'
            status = 'error'
        elif params.save_button:
            tool.user_description = util.restore_text( params.description )
            categories = []
            set_categories( trans, tool, util.listify( params.category_id ) )
            trans.sa_session.add( tool )
            trans.sa_session.flush()
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              message="Saved categories and description for tool '%s'" % tool.name,
                                                              status='done' ) )
        categories = trans.sa_session.query( trans.model.Category ).order_by( trans.model.Category.table.c.name ).all()
        return trans.fill_template( '/webapps/community/tool/edit_tool.mako',
                                    cntrller=cntrller,
                                    encoded_id = encoded_id,
                                    tool=tool,
                                    categories=categories,
                                    message=message,
                                    status=status )
    @web.expose
    def view_tool( self, trans, cntrller, id=None, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        # Get the tool
        tool = None
        if id is not None:
            id = trans.app.security.decode_id( id )
            tool = trans.sa_session.query( trans.model.Tool ).get( id )
        if tool is None:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              message='Please select a Tool to edit (the tool ID provided was invalid)',
                                                              status='error' ) )
        return trans.fill_template( '/webapps/community/tool/view_tool.mako',
                                    tool=tool,
                                    message=message,
                                    status=status )
    @web.expose
    def add_category( self, trans, cntrller, **kwd ):
        # TODO: we currently assume we are setting a tool category, so this method may need
        # tweaking if / when we decide to set history or workflow categories
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        id = params.get( 'id', None )
        # TODO: redirect if no id
        tool = trans.sa_session.query( trans.model.Tool ).get( trans.security.decode_id( id ) )
        if params.get( 'add_category_button', False ):
            category_ids = util.listify( params.get( 'category_id', '' ) )
            # TODO: redirect if no category_id
            message = "The tool '%s' has been added to the categories: " % ( tool.name )
            for category_id in category_ids:
                category = trans.sa_session.query( trans.model.Category ).get( trans.security.decode_id( category_id ) )
                tca = trans.app.model.ToolCategoryAssociation( tool, category )
                trans.sa_session.add( tca )
                trans.sa_session.flush()
                message += " %s " % category.name
            trans.response.send_redirect( web.url_for( controller=cntrller,
                                                       action='browse_tools',
                                                       use_panels=use_panels,
                                                       cntrller=cntrller,
                                                       message=util.sanitize_text( message ),
                                                       status=status ) )
        category_select_list = SelectField( 'category_id', multiple=True )
        for category in get_unassociated_categories( trans, tool ):
            category_select_list.add_option( category.name, trans.security.encode_id( category.id ) )
        return trans.fill_template( '/webapps/community/category/add_to_category.mako',
                                    cntrller=cntrller,
                                    id=id,
                                    category_select_list=category_select_list,
                                    use_panels=use_panels )
    @web.expose
    def remove_category( self, trans, cntrller, **kwd ):
        # TODO: we currently assume we are setting a tool category, so this method may need
        # tweaking if / when we decide to set history or workflow categories
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        use_panels = util.string_as_bool( params.get( 'use_panels', False ) )
        id = params.get( 'id', None )
        # TODO: redirect if no id
        tool = trans.sa_session.query( trans.model.Tool ).get( trans.security.decode_id( id ) )
        category_id = params.get( 'category_id', None )
        category = trans.sa_session.query( trans.model.Category ).get( trans.security.decode_id( category_id ) )
        # TODO: redirect if no category_id
        for tca in tool.categories:
            if tca.category == category:
                trans.sa_session.delete( tca )
                trans.sa_session.flush()
                break
        message = "The tool '%s' has been removed from the category '%s'" % ( tool.name, category.name )
        trans.response.send_redirect( web.url_for( controller=cntrller,
                                                   action='browse_tools',
                                                   use_panels=use_panels,
                                                   cntrller=cntrller,
                                                   message=util.sanitize_text( message ),
                                                   status=status ) )

## ---- Utility methods -------------------------------------------------------

def get_categories( trans ):
    """Get all categories from the database"""
    return trans.sa_session.query( trans.model.Category ) \
                           .filter( trans.model.Category.table.c.deleted==False ) \
                           .order_by( trans.model.Category.table.c.name )
def get_unassociated_categories( trans, obj ):
    """Get all categories from the database that are not associated with obj"""
    # TODO: we currently assume we are setting a tool category, so this method may need
    # tweaking if / when we decide to set history or workflow categories
    associated_categories = []
    for tca in obj.categories:
        associated_categories.append( tca.category )
    categories = []
    for category in get_categories( trans ):
        if category not in associated_categories:
            categories.append( category )
    return categories
def get_category( trans, id ):
    """Get a Category from the database by id."""
    # Load user from database
    id = trans.security.decode_id( id )
    category = trans.sa_session.query( trans.model.Category ).get( id )
    if not category:
        return trans.show_error_message( "Category not found for id (%s)" % str( id ) )
    return category
def set_categories( trans, obj, category_ids, delete_existing_assocs=True ):
    if delete_existing_assocs:
        for assoc in obj.categories:
            trans.sa_session.delete( assoc )
            trans.sa_session.flush()
    for category_id in category_ids:
        # TODO: we currently assume we are setting a tool category, so this method may need
        # tweaking if / when we decide to set history or workflow categories
        category = trans.sa_session.query( trans.model.Category ).get( category_id )
        obj.categories.append( trans.model.ToolCategoryAssociation( obj, category ) )
