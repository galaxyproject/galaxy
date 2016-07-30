"""
API operations on User Preferences objects.
"""

import logging

from sqlalchemy import false, true, or_

from galaxy import exceptions, util, web
from galaxy.managers import users
from galaxy.security.validate_user_input import validate_email
from galaxy.security.validate_user_input import validate_password
from galaxy.security.validate_user_input import validate_publicname
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import CreatesApiKeysMixin
from galaxy.web.base.controller import CreatesUsersMixin
from galaxy.web.base.controller import UsesTagsMixin

log = logging.getLogger( __name__ )


class UserPreferencesAPIController( BaseAPIController, UsesTagsMixin, CreatesUsersMixin, CreatesApiKeysMixin ):

    @expose_api
    def index( self, trans, cntrller='user', **kwd ):
        return {'id': trans.security.encode_id( trans.user.id ),
                'message': "",
                'username': trans.user.username,
                'email': trans.user.email,
                'webapp': trans.webapp.name,
                'remote_user': trans.app.config.use_remote_user,
                'openid': trans.app.config.enable_openid,
                'enable_quotas': trans.app.config.enable_quotas,
                'disk_usage': trans.user.get_disk_usage( nice_size=True ),
                'quota': trans.app.quota_agent.get_quota( trans.user, nice_size=True ),
               }

