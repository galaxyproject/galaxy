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
        roles = trans.get_current_user_roles()
        all_libraries = trans.sa_session.query( trans.app.model.Library ) \
                                        .filter( trans.app.model.Library.table.c.deleted==False ) \
                                        .order_by( trans.app.model.Library.name )
        authorized_libraries = []
        for library in all_libraries:
            if trans.app.security_agent.library_is_public( library ) or trans.app.security_agent.can_access_library( roles, library ):
                authorized_libraries.append( library )
        return trans.fill_template( '/library/browse_libraries.mako', 
                                    libraries=authorized_libraries,
                                    default_action=params.get( 'default_action', None ),
                                    msg=msg,
                                    messagetype=messagetype )
