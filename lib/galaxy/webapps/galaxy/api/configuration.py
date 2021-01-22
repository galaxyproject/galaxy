"""
API operations allowing clients to determine Galaxy instance's capabilities
and configuration settings.
"""
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional
)

from fastapi import Depends
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter as APIRouter

from galaxy.managers.configuration import ConfigurationManager
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
from .common import (
    parse_serialization_params,
    SerializationKeysQueryParam,
    SerializationViewQueryParam,
)

log = logging.getLogger(__name__)

router = APIRouter(tags=['configuration'])

AdminUserRequired = Depends(get_admin_user)


def get_configuration_manager(app: StructuredApp = Depends(get_app)) -> ConfigurationManager:
    return ConfigurationManager(app)


@cbv(router)
class FastAPIConfiguration:
    configuration_manager: ConfigurationManager = Depends(get_configuration_manager)

    @router.get('/api/whoami')
    def whoami(self, user: User = Depends(get_user)) -> Optional[UserModel]:
        """Return information about the current authenticated user."""
        return _user_to_model(user)

    @router.get('/api/configuration')
    def index(
        self,
        trans: ProvidesUserContext = Depends(get_trans),
        view: Optional[str] = SerializationViewQueryParam,
        keys: Optional[str] = SerializationKeysQueryParam,
    ) -> Dict[str, Any]:
        """
        Return an object containing exposable configuration settings.

        A more complete list is returned if the user is an admin.
        Pass in `view` and a comma-seperated list of keys to control which
        configuration settings are returned.
        """
        return _index(self.configuration_manager, trans, view, keys)

    @router.get('/api/version')
    def version(self) -> Dict[str, Any]:
        """Return Galaxy version information: major/minor version, optional extra info."""
        return self.configuration_manager.version()

    @router.get('/api/configuration/dynamic_tool_confs', dependencies=[AdminUserRequired])
    def dynamic_tool_confs(self) -> List[Dict[str, str]]:
        return self.configuration_manager.dynamic_tool_confs()

    @router.get('/api/configuration/decode/{encoded_id}', dependencies=[AdminUserRequired])
    def decode_id(
        self,
        trans: ProvidesAppContext = Depends(get_trans),
        *,
        encoded_id: str
    ) -> Dict[str, int]:
        """Decode a given id."""
        return self.configuration_manager.decode_id(trans, encoded_id)

    @router.get('/api/configuration/tool_lineages', dependencies=[AdminUserRequired])
    def tool_lineages(self) -> List[Dict[str, Dict]]:
        """Return tool lineages for tools that have them."""
        return self.configuration_manager.tool_lineages()

    @router.put('/api/configuration/toolbox')
    def reload_toolbox(self):
        """Reload the Galaxy toolbox (but not individual tools)."""
        self.configuration_manager.reload_toolbox()


class ConfigurationController(BaseAPIController):

    def __init__(self, app: StructuredApp):
        super().__init__(app)
        self.configuration_manager = ConfigurationManager(app)

    @expose_api
    def whoami(self, trans, **kwd):
        """
        GET /api/whoami
        Return information about the current authenticated user.

        :returns: dictionary with user information
        :rtype:   dict
        """
        user = UserManager(self.app).current_user(trans)
        return _user_to_model(user)

    @expose_api_anonymous_and_sessionless
    def index(self, trans, **kwd):
        """
        GET /api/configuration
        Return an object containing exposable configuration settings.

        A more complete list is returned if the user is an admin.
        Pass in `view` and a comma-seperated list of keys to control which
        configuration settings are returned.
        """
        return self.get_config_dict(trans, **kwd)

    @expose_api_anonymous_and_sessionless
    def version(self, trans, **kwd):
        """
        GET /api/version
        Return Galaxy version information: major/minor version, optional extra info.

        :rtype:     dict
        :returns:   dictionary with major version keyed on 'version_major'
        """
        return self.configuration_manager.version()

    @require_admin
    @expose_api
    def dynamic_tool_confs(self, trans, **kwds):
        return self.configuration_manager.dynamic_tool_confs()

    @require_admin
    @expose_api
    def decode_id(self, trans, encoded_id, **kwds):
        """Decode a given id."""
        return self.configuration_manager.decode_id(trans, encoded_id)

    @require_admin
    @expose_api
    def tool_lineages(self, trans, **kwds):
        return self.configuration_manager.tool_lineages()

    @require_admin
    @expose_api
    def reload_toolbox(self, trans, **kwds):
        """
        PUT /api/configuration/toolbox
        Reload the Galaxy toolbox (but not individual tools).
        """
        self.configuration_manager.reload_toolbox()

    def get_config_dict(self, trans, **kwd):
        """Return an object containing exposable configuration settings."""
        view, keys = kwd.get('view'), kwd.get('keys')
        return _index(self.configuration_manager, trans, view, keys)


def _user_to_model(user):
    return UserModel(**user.to_dict()) if user else None


def _index(manager, trans, view, keys):
    serialization_params = parse_serialization_params(view, keys, 'all')
    return manager.get_configuration(trans, serialization_params)
