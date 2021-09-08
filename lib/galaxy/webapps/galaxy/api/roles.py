"""
API operations on Role objects.
"""
import json
import logging

from fastapi import (
    Body,
)

from galaxy import web
from galaxy.managers.base import decode_id
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.roles import RoleManager
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import (
    RoleDefinitionModel,
    RoleListModel,
    RoleModel,
)
from galaxy.webapps.base.controller import url_for
from . import (
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)


# Empty paths (e.g. /api/roles) only work if a prefix is defined right here.
# https://github.com/tiangolo/fastapi/pull/415/files
router = Router(tags=["roles"])


def role_to_model(trans, role):
    item = role.to_dict(view='element', value_mapper={'id': trans.security.encode_id})
    role_id = trans.security.encode_id(role.id)
    item['url'] = url_for('role', id=role_id)
    return RoleModel(**item)


@router.cbv
class FastAPIRoles:
    role_manager: RoleManager = depends(RoleManager)

    @router.get('/api/roles')
    def index(self, trans: ProvidesUserContext = DependsOnTrans) -> RoleListModel:
        roles = self.role_manager.list_displayable_roles(trans)
        return RoleListModel(__root__=[role_to_model(trans, r) for r in roles])

    @router.get('/api/roles/{id}')
    def show(self, id: EncodedDatabaseIdField, trans: ProvidesUserContext = DependsOnTrans) -> RoleModel:
        role_id = trans.app.security.decode_id(id)
        role = self.role_manager.get(trans, role_id)
        return role_to_model(trans, role)

    @router.post("/api/roles", require_admin=True)
    def create(self, trans: ProvidesUserContext = DependsOnTrans, role_definition_model: RoleDefinitionModel = Body(...)) -> RoleModel:
        role = self.role_manager.create_role(trans, role_definition_model)
        return role_to_model(trans, role)


class RoleAPIController(BaseGalaxyAPIController):
    role_manager: RoleManager = depends(RoleManager)

    @web.expose_api
    def index(self, trans: ProvidesUserContext, **kwd):
        """
        GET /api/roles
        Displays a collection (list) of roles.
        """
        roles = self.role_manager.list_displayable_roles(trans)
        return RoleListModel(__root__=[role_to_model(trans, r) for r in roles])

    @web.expose_api
    def show(self, trans: ProvidesUserContext, id: str, **kwd):
        """
        GET /api/roles/{encoded_role_id}
        Displays information about a role.
        """
        role_id = decode_id(self.app, id)
        role = self.role_manager.get(trans, role_id)
        return role_to_model(trans, role)

    @web.expose_api
    @web.require_admin
    def create(self, trans: ProvidesUserContext, payload, **kwd):
        """
        POST /api/roles
        Creates a new role.
        """
        expand_json_keys(payload, ["user_ids", "group_ids"])
        role_definition_model = RoleDefinitionModel(**payload)
        role = self.role_manager.create_role(trans, role_definition_model)
        return role_to_model(trans, role)


def expand_json_keys(payload: dict, keys):
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            try:
                new_value = json.loads(value)
                payload[key] = new_value
            except Exception:
                pass
