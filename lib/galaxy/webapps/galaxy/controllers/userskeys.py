"""
Contains the user interface in the Universe class
"""

import logging
import pprint

from galaxy import web
from galaxy import util, model
from galaxy.web.base.controller import BaseUIController, UsesFormDefinitionsMixin
from galaxy.web.framework.helpers import time_ago, grids

from inspect import getmembers

log = logging.getLogger( __name__ )

require_login_template = """
<p>
    This %s has been configured such that only users who are logged in may use it.%s
</p>
<p/>
"""

class UserOpenIDGrid( grids.Grid ):
    use_panels = False
    title = "OpenIDs linked to your account"
    model_class = model.UserOpenID
    template = '/user/openid_manage.mako'
    default_filter = { "openid" : "All" }
    default_sort_key = "-create_time"
    columns = [
        grids.TextColumn( "OpenID URL", key="openid", link=( lambda x: dict( action='openid_auth', login_button="Login", openid_url=x.openid if not x.provider else '', openid_provider=x.provider, auto_associate=True ) ) ),
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
    ]
    operations = [
        grids.GridOperation( "Delete", async_compatible=True ),
    ]
    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( self.model_class ).filter( self.model_class.user_id == trans.user.id )

class User( BaseUIController, UsesFormDefinitionsMixin ):
    user_openid_grid = UserOpenIDGrid()
    installed_len_files = None


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
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        uid = params.get('uid', uid)
        pprint.pprint(uid)
        if params.get( 'new_api_key_button', False ):
            new_key = trans.app.model.APIKeys()
            new_key.user_id = uid
            new_key.key = trans.app.security.get_new_guid()
            trans.sa_session.add( new_key )
            trans.sa_session.flush()
            message = "Generated a new web API key"
            status = "done"
        return trans.fill_template( 'webapps/galaxy/user/ok_admin_api_keys.mako',
                                    cntrller=cntrller,
                                    message=message,
                                    status=status )
    
    
    @web.expose
    @web.require_login()
    @web.require_admin
    def all_users( self, trans, cntrller="userskeys", **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        users = []
        for user in trans.sa_session.query( trans.app.model.User ) \
                                    .filter( trans.app.model.User.table.c.deleted==False ) \
                                    .order_by( trans.app.model.User.table.c.email ):
                uid = int(user.id)
                userkey = ""
                for api_user in trans.sa_session.query(trans.app.model.APIKeys) \
                                      .filter( trans.app.model.APIKeys.user_id == uid):
                    userkey = api_user.key
                users.append({'uid':uid, 'email':user.email, 'key':userkey})
        return trans.fill_template( 'webapps/galaxy/user/list_users.mako',
                                    cntrller=cntrller,
                                    users=users,
                                    message=message,
                                    status=status )
