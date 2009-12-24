from galaxy.web.base.controller import *
from galaxy.model.orm import *
from galaxy.datatypes import sniff
from galaxy import util
from galaxy.util.odict import odict

log = logging.getLogger( __name__ )

class Library( BaseController ):
    @web.expose
    def index( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        return trans.fill_template( "/library/index.mako",
                                    default_action=params.get( 'default_action', None ),
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    def browse_libraries( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        user, roles = trans.get_user_and_roles()
        all_libraries = trans.sa_session.query( trans.app.model.Library ) \
                                        .filter( trans.app.model.Library.table.c.deleted==False ) \
                                        .order_by( trans.app.model.Library.name )
        library_actions = [ trans.app.security_agent.permitted_actions.LIBRARY_ADD,
                            trans.app.security_agent.permitted_actions.LIBRARY_MODIFY,
                            trans.app.security_agent.permitted_actions.LIBRARY_MANAGE ]
        # The authorized_libraries dictionary looks like: { library : '1,2' }, library : '3' }
        # Its keys are the libraries that should be displayed for the current user and whose values are a
        # string of comma-separated folder ids of the associated folders that should NOT be displayed.
        # The folders that should not be displayed may not be a complete list, but it is ultimately passed
        # to the browse_library() method and the browse_library.mako template to keep from re-checking the
        # same folders when the library is rendered.
        authorized_libraries = odict()
        for library in all_libraries:
            can_access, hidden_folder_ids = trans.app.security_agent.check_folder_contents( user, roles, library.root_folder )
            if can_access:
                authorized_libraries[ library ] = hidden_folder_ids
            else:
                can_show, hidden_folder_ids = trans.app.security_agent.show_library_item( user, roles, library, library_actions )
                if can_show:
                    authorized_libraries[ library ] = hidden_folder_ids
        return trans.fill_template( '/library/browse_libraries.mako', 
                                    libraries=authorized_libraries,
                                    default_action=params.get( 'default_action', None ),
                                    msg=msg,
                                    messagetype=messagetype )
