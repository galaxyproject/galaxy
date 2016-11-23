from markupsafe import escape
from galaxy import model
from galaxy import util
from galaxy import web
from galaxy.webapps.galaxy.controllers.user import User as BaseUser

class User( BaseUser ):

    @web.expose
    def manage_user_info( self, trans, cntrller, **kwd ):
        '''Manage a user's login, password, public username, type, addresses, etc.'''
        params = util.Params( kwd )
        user_id = params.get( 'id', None )
        if user_id:
            user = trans.sa_session.query( trans.app.model.User ).get( trans.security.decode_id( user_id ) )
        else:
            user = trans.user
        if not user:
            raise AssertionError("The user id (%s) is not valid" % str( user_id ))
        email = util.restore_text( params.get( 'email', user.email ) )
        username = util.restore_text( params.get( 'username', '' ) )
        if not username:
            username = user.username
        message = escape( util.restore_text( params.get( 'message', ''  ) ) )
        status = params.get( 'status', 'done' )
        return trans.fill_template( '/webapps/tool_shed/user/manage_info.mako',
                                    cntrller=cntrller,
                                    user=user,
                                    email=email,
                                    username=username,
                                    message=message,
                                    status=status )
