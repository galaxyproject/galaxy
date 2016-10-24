"""
Contains the user interface in the Universe class
"""

import logging

from markupsafe import escape
from sqlalchemy import false

from galaxy import (
    util,
    web
)
from galaxy.web.base.controller import BaseUIController, UsesFormDefinitionsMixin

log = logging.getLogger( __name__ )

require_login_template = """
<p>
    This %s has been configured such that only users who are logged in may use it.%s
</p>
"""

# FIXME: This controller is using unencoded IDs, but I am not going to address
# this now since it is admin-side and should be reimplemented in the API
# anyway.


class User( BaseUIController, UsesFormDefinitionsMixin ):
    @web.expose
    @web.require_login()
    @web.require_admin
    def index( self, trans, cntrller, **kwd ):
        return trans.fill_template( 'webapps/galaxy/user/list_users.mako', action='all_users', cntrller=cntrller )

    @web.expose
    @web.require_login()
    @web.require_admin
    def admin_api_keys( self, trans, cntrller, uid, **kwd ):
        params = util.Params( kwd )
        message = escape( util.restore_text( params.get( 'message', ''  ) ) )
        status = params.get( 'status', 'done' )
        uid = params.get('uid', uid)
        if params.get( 'new_api_key_button', False ):
            new_key = trans.app.model.APIKeys()
            new_key.user_id = uid
            new_key.key = trans.app.security.get_new_guid()
            trans.sa_session.add( new_key )
            trans.sa_session.flush()
            message = "A new web API key has been generated for (%s)" % escape( new_key.user.email )
            status = "done"
        return trans.response.send_redirect( web.url_for( controller='userskeys',
                                                          action='all_users',
                                                          cntrller=cntrller,
                                                          message=message,
                                                          status=status ) )

    @web.expose
    @web.require_login()
    @web.require_admin
    def all_users( self, trans, cntrller="userskeys", **kwd ):
        params = util.Params( kwd )
        message = escape( util.restore_text( params.get( 'message', ''  ) ) )
        status = params.get( 'status', 'done' )
        users = []
        for user in trans.sa_session.query( trans.app.model.User ) \
                                    .filter( trans.app.model.User.table.c.deleted == false() ) \
                                    .order_by( trans.app.model.User.table.c.email ):
                uid = int(user.id)
                userkey = ""
                for api_user in trans.sa_session.query(trans.app.model.APIKeys) \
                        .filter( trans.app.model.APIKeys.user_id == uid):
                    userkey = api_user.key
                users.append({'uid': uid, 'email': user.email, 'key': userkey})
        return trans.fill_template( 'webapps/galaxy/user/list_users.mako',
                                    cntrller=cntrller,
                                    users=users,
                                    message=message,
                                    status=status )
