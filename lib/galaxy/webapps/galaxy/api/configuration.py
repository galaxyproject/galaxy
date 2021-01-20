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
from galaxy.managers.context import (
    ProvidesAppContext,
    ProvidesUserContext,
)
from galaxy.managers.users import (
    UserManager,
    UserModel
)
from galaxy.model import User
from galaxy.structured_app import StructuredApp
from galaxy.web import (
    expose_api,
    expose_api_anonymous_and_sessionless,
    require_admin
)
from galaxy.webapps.base.controller import BaseAPIController
from . import (
    get_admin_user,
    get_app,
    get_trans,
    get_user,
)

log = logging.getLogger(__name__)


router = APIRouter(tags=['configuration'])

VERSION_JSON_FILE = 'version.json'


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
    if isinstance(keys, str):
        keys = keys.split(',')
    return dict(view=view, keys=keys, default_view=default_view)


def user_to_model(user):
    return UserModel(**user.to_dict()) if user else None


def get_configuration(trans, view, keys, default_view='all'):
    is_admin = trans.user_is_admin
    serialization_params = parse_serialization_params(view, keys, default_view)
    return get_config_dict(trans.app, is_admin, **serialization_params)


def get_config_dict(app, is_admin=False, view=None, keys=None, default_view='all'):
    """
    Return a dictionary with a subset of current Galaxy settings.

    If `is_admin`, include a subset of more sensitive keys.
    Pass in `view` (String) and comma seperated list of keys to control which
    configuration settings are returned.
    """
    serializer = AdminConfigSerializer(app) if is_admin else ConfigSerializer(app)
    return serializer.serialize_to_view(app.config, view=view, keys=keys, default_view=default_view)


def get_version(app):
    version_info = {
        "version_major": app.config.version_major,
        "version_minor": app.config.version_minor,
    }
    # Try loading extra version info
    json_file = os.path.join(app.config.root, VERSION_JSON_FILE)  # TODO: add this to schema
    json_file = os.environ.get("GALAXY_VERSION_JSON_FILE", json_file)
    try:
        with open(json_file) as f:
            extra_info = json.load(f)
    except OSError:
        log.info('Galaxy JSON version file not loaded')
    else:
        version_info['extra'] = extra_info
    return version_info


def decode_id(trans, encoded_id):
    # Handle the special case for library folders
    if ((len(encoded_id) % 16 == 1) and encoded_id.startswith('F')):
        encoded_id = encoded_id[1:]
    decoded_id = trans.security.decode_id(encoded_id)
    return {"decoded_id": decoded_id}


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
        return get_configuration(trans, view, keys)

    @router.get('/api/version')
    def version(self, app: StructuredApp = Depends(get_app)) -> Dict[str, Any]:
        """Return Galaxy version information: major/minor version, optional extra info."""
        return get_version(app)

    @router.get('/api/configuration/decode/{encoded_id}', dependencies=[Depends(get_admin_user)])
    def decode_id(
        self,
        trans: ProvidesAppContext = Depends(get_trans),
        *,
        encoded_id: str
    ) -> Dict[str, int]:
        """Decode a given id."""
        return decode_id(trans, encoded_id)


class ConfigurationController(BaseAPIController):

    @expose_api
    def whoami(self, trans, **kwd):
        """
        GET /api/whoami
        Return information about the current authenticated user.

        :returns: dictionary with user information
        :rtype:   dict
        """
        user = UserManager(self.app).current_user(trans)
        return user_to_model(user)

    @expose_api_anonymous_and_sessionless
    def index(self, trans, **kwd):
        """
        GET /api/configuration
        Return an object containing exposable configuration settings.

        Note: a more complete list is returned if the user is an admin.
        """
        view, keys = kwd.get('view'), kwd.get('keys')
        return get_configuration(trans, view, keys)

    @expose_api_anonymous_and_sessionless
    def version(self, trans, **kwds):
        """
        GET /api/version
        Return Galaxy version information: major/minor version, optional extra info.

        :rtype:     dict
        :returns:   dictionary with major version keyed on 'version_major'
        """
        return get_version(self.app)

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
        return decode_id(trans, encoded_id)

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

    def get_config_dict(self, trans, return_admin=False, view=None, keys=None, default_view='all'):
        # Method left for backward compatibility (templates/galaxy_client_app.mako).
        return get_config_dict(self.app, return_admin, view=view, keys=keys, default_view=default_view)


def _tool_conf_to_dict(conf):
    return dict(
        config_filename=conf['config_filename'],
        tool_path=conf['tool_path'],
    )
