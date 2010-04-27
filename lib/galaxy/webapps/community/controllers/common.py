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
    def edit_tool( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              message='Select a tool to edit',
                                                              status='error' ) )
        tool = get_tool( trans, id )
        if params.get( 'edit_tool_button', False ):
            tool.user_description = util.restore_text( params.description )
            trans.sa_session.add( tool )
            trans.sa_session.flush()
            return trans.response.send_redirect( web.url_for( controller='common',
                                                              action='edit_tool',
                                                              cntrller=cntrller,
                                                              id=id,
                                                              message="The information was updated",
                                                              status='done' ) )
        return trans.fill_template( '/webapps/community/tool/edit_tool.mako',
                                    cntrller=cntrller,
                                    id=id,
                                    tool=tool,
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
                                                              message='Select a tool to view',
                                                              status='error' ) )
        tool = get_tool( trans, id )
        categories = [ tca.category for tca in tool.categories ]
        return trans.fill_template( '/webapps/community/tool/view_tool.mako',
                                    tool=tool,
                                    categories=categories,
                                    cntrller=cntrller,
                                    message=message,
                                    status=status )
    @web.expose
    def manage_categories( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              message='Select a tool to manage categories',
                                                              status='error' ) )
        tool = get_tool( trans, id )
        if params.get( 'manage_categories_button', False ):
            in_categories = [ trans.sa_session.query( trans.app.model.Category ).get( x ) for x in util.listify( params.in_categories ) ]
            trans.app.security_agent.set_entity_category_associations( tools=[ tool ], categories=in_categories )
            trans.sa_session.refresh( tool )
            message = "Tool '%s' has been updated with %d associated categories" % ( tool.name, len( in_categories ) )
            trans.response.send_redirect( web.url_for( controller='common',
                                                       action='manage_categories',
                                                       cntrller=cntrller,
                                                       id=id,
                                                       message=util.sanitize_text( message ),
                                                       status=status ) )            
        in_categories = []
        out_categories = []
        for category in get_categories( trans ):
            if category in [ x.category for x in tool.categories ]:
                in_categories.append( ( category.id, category.name ) )
            else:
                out_categories.append( ( category.id, category.name ) )
        return trans.fill_template( '/webapps/community/tool/manage_categories.mako',
                                    tool=tool,
                                    in_categories=in_categories,
                                    out_categories=out_categories,
                                    cntrller=cntrller,
                                    message=message,
                                    status=status )
    @web.expose
    def upload_new_tool_version( self, trans, cntrller, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                              action='browse_tools',
                                                              message='Select a tool to to upload a new version',
                                                              status='error' ) )
        tool = get_tool( trans, id )
        if params.save_button and ( params.file_data != '' or params.url != '' ):
            # TODO: call the upload method in the upload controller.
            message = 'Uploading new version not implemented'
            status = 'error'
        return trans.response.send_redirect( web.url_for( controller=cntrller,
                                                          action='browse_tools',
                                                          message='Not yet implemented, sorry...',
                                                          status='error' ) )

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
    return trans.sa_session.query( trans.model.Category ).get( trans.security.decode_id( id ) )
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
def get_tool( trans, id ):
    return trans.sa_session.query( trans.model.Tool ).get( trans.app.security.decode_id( id ) )

