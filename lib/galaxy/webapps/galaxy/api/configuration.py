"""
API operations allowing clients to determine Galaxy instance's capabilities
and configuration settings.
"""
import json
import logging
import os
from typing import (
    Any,
    Dict,
    Optional
)

from fastapi import Depends, Query
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter as APIRouter

from galaxy.managers.configuration import (
    AdminConfigSerializer,
    ConfigSerializer
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.users import (
    UserManager,
    UserModel
)
from galaxy.model import User
from galaxy.web import (
    expose_api,
    expose_api_anonymous_and_sessionless,
    require_admin
)
from galaxy.webapps.base.controller import BaseAPIController
from . import (
    get_trans,
    get_user,
)

log = logging.getLogger(__name__)


router = APIRouter(tags=['configuration'])


# TODO move to common.py as soon as used more than once
SerializationViewQueryParam: Optional[str] = Query(
    None,
    title='View',
    description='todo',
)


# TODO move to common.py as soon as used more than once
SerializationKeysQueryParam: Optional[str] = Query(
    None,
    title='Keys',
    description='todo',
)


# TODO move to common.py as soon as used more than once
def parse_serialization_params(view, keys, default_view):
    try:
        keys = keys.split(',')
    except AttributeError:
        pass
    return dict(view=view, keys=keys, default_view=default_view)


def user_to_model(user):
    return UserModel(**user.to_dict()) if user else None


def get_config_dict(app, is_admin=False, view=None, keys=None, default_view='all'):
    serializer = AdminConfigSerializer(app) if is_admin else ConfigSerializer(app)
    return serializer.serialize_to_view(app.config, view=view, keys=keys, default_view=default_view)


@cbv(router)
class FastAPIConfiguration:

    @router.get('/api/whoami')
    def whoami(self, user: User = Depends(get_user)) -> Optional[UserModel]:
        """Return information about the current authenticated user."""
        return user_to_model(user)

    @router.get('/api/configuration')
    def index(
            self,
            trans: ProvidesUserContext = Depends(get_trans),
            view: Optional[str] = SerializationViewQueryParam,
            keys: Optional[str] = SerializationKeysQueryParam,
    ) -> Dict[str, Any]:
        """Return an object containing exposable configuration settings."""
        is_admin = trans.user_is_admin
        serialization_params = parse_serialization_params(view, keys, 'all')   # this gets a dict
        return get_config_dict(trans.app, is_admin, **serialization_params)


class ConfigurationController(BaseAPIController):

    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.user_manager = UserManager(app)

    @expose_api
    def whoami(self, trans, **kwd):
        """
        GET /api/whoami
        Return information about the current authenticated user.

        :returns: dictionary with user information
        :rtype:   dict
        """
        user = self.user_manager.current_user(trans)
        return user_to_model(user)

    @expose_api_anonymous_and_sessionless
    def index(self, trans, **kwd):
        """
        GET /api/configuration
        Return an object containing exposable configuration settings.

        Note: a more complete list is returned if the user is an admin.
        """
        is_admin = trans.user_is_admin
        serialization_params = self._parse_serialization_params(kwd, 'all')
        return get_config_dict(self.app, is_admin, **serialization_params)

    @expose_api_anonymous_and_sessionless
    def version(self, trans, **kwds):
        """
        GET /api/version
        Return a description of the major version of Galaxy (e.g. 15.03).

        :rtype:     dict
        :returns:   dictionary with major version keyed on 'version_major'
        """
        extra = {}
        try:
            version_file = os.environ.get("GALAXY_VERSION_JSON_FILE", self.app.container_finder.app_info.galaxy_root_dir + "/version.json")
            with open(version_file) as f:
                extra = json.load(f)
        except Exception:
            pass
        return {"version_major": self.app.config.version_major, "extra": extra}

    @require_admin
    @expose_api
    def dynamic_tool_confs(self, trans):
        # WARNING: If this method is ever changed so as not to require admin privileges, update the nginx proxy
        # documentation, since this path is used as an authentication-by-proxy method for securing other paths on the
        # server. A dedicated endpoint should probably be added to do that instead.
        confs = self.app.toolbox.dynamic_confs(include_migrated_tool_conf=True)
        return list(map(_tool_conf_to_dict, confs))

    @require_admin
    @expose_api
    def decode_id(self, trans, encoded_id, **kwds):
        """Decode a given id."""
        decoded_id = None
        # Handle the special case for library folders
        if ((len(encoded_id) % 16 == 1) and encoded_id.startswith('F')):
            decoded_id = trans.security.decode_id(encoded_id[1:])
        else:
            decoded_id = trans.security.decode_id(encoded_id)
        return {"decoded_id": decoded_id}

    @require_admin
    @expose_api
    def tool_lineages(self, trans):
        rval = []
        for id, tool in self.app.toolbox.tools():
            if hasattr(tool, 'lineage'):
                lineage_dict = tool.lineage.to_dict()
            else:
                lineage_dict = None

            entry = dict(
                id=id,
                lineage=lineage_dict
            )
            rval.append(entry)
        return rval

    @require_admin
    @expose_api
    def reload_toolbox(self, trans, **kwds):
        """
        PUT /api/configuration/toolbox
        Reload the Galaxy toolbox (but not individual tools).
        """
        self.app.queue_worker.send_control_task('reload_toolbox')


def _tool_conf_to_dict(conf):
    return dict(
        config_filename=conf['config_filename'],
        tool_path=conf['tool_path'],
    )
