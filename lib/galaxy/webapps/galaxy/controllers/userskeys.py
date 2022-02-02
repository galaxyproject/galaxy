"""
Contains the user interface in the Universe class
"""

from sqlalchemy import false

from galaxy import (
    util,
    web,
)
from galaxy.webapps.base.controller import (
    BaseUIController,
    UsesFormDefinitionsMixin,
)


class User(BaseUIController, UsesFormDefinitionsMixin):
    @web.expose
    @web.require_login()
    @web.require_admin
    def index(self, trans, cntrller, **kwd):
        return self.get_all_users(trans)

    @web.expose
    @web.require_login()
    @web.require_admin
    def admin_api_keys(self, trans, uid, **kwd):
        params = util.Params(kwd)
        uid = params.get("uid", uid)
        new_key = trans.app.model.APIKeys()
        new_key.user_id = trans.security.decode_id(uid)
        new_key.key = trans.app.security.get_new_guid()
        trans.sa_session.add(new_key)
        trans.sa_session.flush()
        return self.get_all_users(trans)

    @web.expose
    @web.require_login()
    @web.require_admin
    def all_users(self, trans, **kwd):
        return self.get_all_users(trans)

    @web.json
    def get_all_users(self, trans):
        users = []
        for user in (
            trans.sa_session.query(trans.app.model.User)
            .filter(trans.app.model.User.table.c.deleted == false())
            .order_by(trans.app.model.User.table.c.email)
        ):
            uid = int(user.id)
            userkey = ""
            for api_user in trans.sa_session.query(trans.app.model.APIKeys).filter(
                trans.app.model.APIKeys.user_id == uid
            ):
                userkey = api_user.key
            users.append({"uid": trans.security.encode_id(uid), "email": user.email, "key": userkey})
        return users
