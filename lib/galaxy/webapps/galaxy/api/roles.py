"""
API operations on Role objects.
"""
import json
import logging
from typing import List

from fastapi import (
    Body,
    Depends,
)
from fastapi_utils.cbv import cbv
from fastapi_utils.inferring_router import InferringRouter as APIRouter
from pydantic import (
    BaseModel,
)

from galaxy import web
from galaxy.app import UniverseApplication
from galaxy.managers.base import decode_id
from galaxy.managers.roles import (
    RoleDefinitionModel,
    RoleManager,
    RoleModel,
)
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.webapps.base.controller import BaseAPIController, url_for
from galaxy.work.context import (
    SessionRequestContext,
)
from . import (
    get_admin_user,
    get_app,
    get_trans,
)

log = logging.getLogger(__name__)


# Empty paths (e.g. /api/roles) only work if a prefix is defined right here.
# https://github.com/tiangolo/fastapi/pull/415/files
router = APIRouter(tags=["roles"])


class RoleListModel(BaseModel):
    __root__: List[RoleModel]


def role_to_model(trans, role):
    item = role.to_dict(view='element', value_mapper={'id': trans.security.encode_id})
    role_id = trans.security.encode_id(role.id)
    try:
        item['url'] = url_for('role', id=role_id)
    except AttributeError:
        item['url'] = "*deprecated attribute not filled in by FastAPI server*"
    return RoleModel(**item)


def get_role_manager(app: UniverseApplication = Depends(get_app)) -> RoleManager:
    return app.role_manager


@cbv(router)
class FastAPIRoles:
    role_manager: RoleManager = Depends(get_role_manager)

    @router.get('/api/roles')
    def index(self, trans: SessionRequestContext = Depends(get_trans)) -> RoleListModel:
        roles = self.role_manager.list_displayable_roles(trans)
        return RoleListModel(__root__=[role_to_model(trans, r) for r in roles])

    @router.get('/api/roles/{id}')
    def show(self, id: EncodedDatabaseIdField, trans: SessionRequestContext = Depends(get_trans)) -> RoleModel:
        role_id = trans.app.security.decode_id(id)
        role = self.role_manager.get(trans, role_id)
        return role_to_model(trans, role)

    @router.post("/api/roles")
    def create(self, trans: SessionRequestContext = Depends(get_trans), admin_user=Depends(get_admin_user), role_definition_model: RoleDefinitionModel = Body(...)) -> RoleModel:
        role = self.role_manager.create(trans, role_definition_model)
        return role_to_model(trans, role)


class RoleAPIController(BaseAPIController):

    @web.expose_api
    def index(self, trans, **kwd):
        """
        GET /api/roles
        Displays a collection (list) of roles.
        """
        roles = self._role_manager.list_displayable_roles(trans)
        return RoleListModel(__root__=[role_to_model(trans, r) for r in roles])

    @web.expose_api
    def show(self, trans, id, **kwd):
        """
        GET /api/roles/{encoded_role_id}
        Displays information about a role.
        """
        role_id = decode_id(self.app, id)
        role = self._role_manager.get(trans, role_id)
        return role_to_model(trans, role)

    @web.require_admin
    @web.expose_api
    def create(self, trans, payload, **kwd):
        """
        POST /api/roles
        Creates a new role.
        """
        expand_json_keys(payload, ["user_ids", "group_ids"])
        role_definition_model = RoleDefinitionModel(**payload)
        role = self._role_manager.create(trans, role_definition_model)
        return role_to_model(trans, role)

    @property
    def _role_manager(self):
        return self.app.role_manager


def expand_json_keys(payload, keys):
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            try:
                new_value = json.loads(value)
                payload[key] = new_value
            except Exception:
                pass
