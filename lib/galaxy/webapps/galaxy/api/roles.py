"""
API operations on Role objects.
"""
import json
import logging
from typing import List

from pydantic import (
    BaseModel,
)

from galaxy import web
from galaxy.managers.base import decode_id
from galaxy.managers.roles import (
    RoleDefeinitionModel,
    RoleModel,
)
from galaxy.webapps.base.controller import BaseAPIController, url_for

log = logging.getLogger(__name__)


class RoleListModel(BaseModel):
    __root__: List[RoleModel]


def role_to_model(trans, role):
    item = role.to_dict(view='element', value_mapper={'id': trans.security.encode_id})
    role_id = trans.security.encode_id(role.id)
    item['url'] = url_for('role', id=role_id)
    return RoleModel(**item)


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
        role_definition_model = RoleDefeinitionModel(**payload)
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
