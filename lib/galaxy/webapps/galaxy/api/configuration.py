"""
API operations allowing clients to determine Galaxy instance's capabilities
and configuration settings.
"""
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from fastapi import Path

from galaxy.managers.configuration import ConfigurationManager
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.users import UserManager
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import UserModel
from galaxy.web import (
    expose_api,
    expose_api_anonymous_and_sessionless,
    require_admin,
)
from . import (
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    Router,
)
from .common import (
    parse_serialization_params,
    SerializationKeysQueryParam,
    SerializationViewQueryParam,
)

log = logging.getLogger(__name__)

router = Router(tags=["configuration"])


EncodedIdPathParam: EncodedDatabaseIdField = Path(
    ...,
    title="Encoded id",
    description="Encoded id to be decoded",
)


@router.cbv
class FastAPIConfiguration:
    configuration_manager: ConfigurationManager = depends(ConfigurationManager)

    @router.get(
        "/api/whoami",
        summary="Return information about the current authenticated user",
        response_description="Information about the current authenticated user",
    )
    def whoami(self, trans: ProvidesUserContext = DependsOnTrans) -> Optional[UserModel]:
        """Return information about the current authenticated user."""
        return _user_to_model(trans.user, trans.security)

    @router.get(
        "/api/configuration",
        summary="Return an object containing exposable configuration settings",
        response_description="Object containing exposable configuration settings",
    )
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
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

    @router.get(
        "/api/version",
        summary="Return Galaxy version information: major/minor version, optional extra info",
        response_description="Galaxy version information: major/minor version, optional extra info",
    )
    def version(self) -> Dict[str, Any]:
        """Return Galaxy version information: major/minor version, optional extra info."""
        return self.configuration_manager.version()

    @router.get(
        "/api/configuration/dynamic_tool_confs",
        require_admin=True,
        summary="Return dynamic tool configuration files",
        response_description="Dynamic tool configuration files",
    )
    def dynamic_tool_confs(self) -> List[Dict[str, str]]:
        """Return dynamic tool configuration files."""
        return self.configuration_manager.dynamic_tool_confs()

    @router.get(
        "/api/configuration/decode/{encoded_id}",
        require_admin=True,
        summary="Decode a given id",
        response_description="Decoded id",
    )
    def decode_id(self, encoded_id: EncodedDatabaseIdField = EncodedIdPathParam) -> Dict[str, int]:
        """Decode a given id."""
        return self.configuration_manager.decode_id(encoded_id)

    @router.get(
        "/api/configuration/tool_lineages",
        require_admin=True,
        summary="Return tool lineages for tools that have them",
        response_description="Tool lineages for tools that have them",
    )
    def tool_lineages(self) -> List[Dict[str, Dict]]:
        """Return tool lineages for tools that have them."""
        return self.configuration_manager.tool_lineages()

    @router.put(
        "/api/configuration/toolbox", require_admin=True, summary="Reload the Galaxy toolbox (but not individual tools)"
    )
    def reload_toolbox(self):
        """Reload the Galaxy toolbox (but not individual tools)."""
        self.configuration_manager.reload_toolbox()


class ConfigurationController(BaseGalaxyAPIController):
    configuration_manager: ConfigurationManager = depends(ConfigurationManager)
    user_manager: UserManager = depends(UserManager)

    @expose_api
    def whoami(self, trans: ProvidesUserContext, **kwd):
        """
        GET /api/whoami
        Return information about the current authenticated user.

        :returns: dictionary with user information
        :rtype:   dict
        """
        user = self.user_manager.current_user(trans)
        return _user_to_model(user, trans.security)

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
        return self.configuration_manager.decode_id(encoded_id)

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
        view, keys = kwd.get("view"), kwd.get("keys")
        return _index(self.configuration_manager, trans, view, keys)


def _user_to_model(user, security):
    return UserModel(**user.to_dict(view="element", value_mapper={"id": security.encode_id})) if user else None


def _index(manager: ConfigurationManager, trans, view, keys):
    serialization_params = parse_serialization_params(view, keys, "all")
    return manager.get_configuration(trans, serialization_params)
