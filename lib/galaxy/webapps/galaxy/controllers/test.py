
from galaxy import web
from galaxy import util
from galaxy.web.base import controller
from galaxy.managers import histories

import logging
log = logging.getLogger( __name__ )


class TestController( controller.JSAppLauncher ):

    def __init__( self, app ):
        super( TestController, self ).__init__( app )
        self.history_serializer = histories.HistorySerializer( app )

    @web.expose
    def history( self, trans ):
        history = trans.history

        bootstrapped = {}
        if history:
            bootstrapped = {
                'history'   : self.history_serializer.serialize_to_view( history,
                    view='detailed', user=trans.user, trans=trans ),
                'contents'  : self.history_serializer.serialize_contents( history, 'contents', trans=trans )
            }
        return self.template( trans, 'history', bootstrapped_data=bootstrapped )

    def _get_extended_config( self, trans ):
        app = trans.app
        configured_for_inactivity_warning = app.config.user_activation_on and app.config.inactivity_box_content is not None
        user_requests = bool( trans.user and ( trans.user.requests or app.security_agent.get_accessible_request_types( trans, trans.user ) ) )
        config = {
            'active_view'                   : 'analysis',
            'params'                        : dict( trans.request.params ),
            'enable_cloud_launch'           : app.config.get_bool( 'enable_cloud_launch', False ),
            'spinner_url'                   : web.url_for( '/static/images/loading_small_white_bg.gif' ),
            'search_url'                    : web.url_for( controller='root', action='tool_search' ),
            # TODO: next two should be redundant - why can't we build one from the other?
            'toolbox'                       : app.toolbox.to_dict( trans, in_panel=False ),
            'toolbox_in_panel'              : app.toolbox.to_dict( trans ),
            'message_box_visible'           : app.config.message_box_visible,
            'show_inactivity_warning'       : configured_for_inactivity_warning and trans.user and not trans.user.active,
            # TODO: move to user
            'user_requests'                 : user_requests
        }

        # TODO: move to user
        stored_workflow_menu_entries = config[ 'stored_workflow_menu_entries' ] = []
        for menu_item in getattr( trans.user, 'stored_workflow_menu_entries', [] ):
            stored_workflow_menu_entries.append({
                'encoded_stored_workflow_id' : trans.security.encode_id( menu_item.stored_workflow_id ),
                'stored_workflow' : {
                    'name' : util.unicodify( menu_item.stored_workflow.name )
                }
            })

        return config

    @web.expose
    def index(self, trans, id=None, tool_id=None, mode=None, workflow_id=None, history_id=None, m_c=None, m_a=None, **kwd):
        history = trans.history
        if history_id:
            unencoded_id = trans.security.decode_id( history_id )
            history = self.history_manager.get_owned( unencoded_id, trans.user )
            trans.set_history( history )

        js_options = self._get_js_options( trans )
        config = js_options[ 'config' ]
        config.update( self._get_extended_config( trans ) )

        return self.template( trans, 'analysis', options=js_options )
