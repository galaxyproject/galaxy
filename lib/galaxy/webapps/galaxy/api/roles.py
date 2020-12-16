"""
API operations on Role objects.
"""
import json
import logging
from typing import List, Optional

from pydantic import (
    BaseModel,
    Field,

)

from galaxy import web
from galaxy.exceptions import RequestParameterInvalidException
from galaxy.managers.base import decode_id
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.webapps.base.controller import BaseAPIController, url_for

log = logging.getLogger(__name__)

RoleIdField = Field("ID", description="Encoded ID of the role")
RoleNameField = Field(title="Name", description="Name of the role")
RoleDescriptionField = Field(title="Description", description="Description of the role")


class RoleModel(BaseModel):
    id: EncodedDatabaseIdField = RoleIdField
    name: str = RoleNameField
    description: str = RoleDescriptionField
    type: str = Field(title="Type", description="Type or category of the role")
    url: str = Field(title="URL", description="URL for the role")
    model_class: str = Field(title="Model class", description="Database model class (Role)")


class RoleListModel(BaseModel):
    __root__: List[RoleModel]


def role_to_model(trans, role):
    item = role.to_dict(view='element', value_mapper={'id': trans.security.encode_id})
    role_id = trans.security.encode_id(role.id)
    item['url'] = url_for('role', id=role_id)
    return RoleModel(**item)


class RoleDefeinition(BaseModel):
    name: str = RoleNameField
    description: str = RoleDescriptionField
    user_ids: Optional[List[EncodedDatabaseIdField]] = Field(title="User IDs", default=[])
    group_ids: Optional[List[EncodedDatabaseIdField]] = Field(title="Group IDs", default=[])


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
        role_definition_model = RoleDefeinition(**payload)
        name = role_definition_model.name
        description = role_definition_model.description
        user_ids = role_definition_model.user_ids or []
        group_ids = role_definition_model.group_ids or []

        if trans.sa_session.query(trans.app.model.Role).filter(trans.app.model.Role.table.c.name == name).first():
            raise RequestParameterInvalidException(f"A role with that name already exists [{name}]")

        role_type = trans.app.model.Role.types.ADMIN  # TODO: allow non-admins to create roles

        role = trans.app.model.Role(name=name, description=description, type=role_type)
        trans.sa_session.add(role)
        users = [trans.sa_session.query(trans.model.User).get(trans.security.decode_id(i)) for i in user_ids]
        groups = [trans.sa_session.query(trans.model.Group).get(trans.security.decode_id(i)) for i in group_ids]

        # Create the UserRoleAssociations
        for user in users:
            trans.app.security_agent.associate_user_role(user, role)

        # Create the GroupRoleAssociations
        for group in groups:
            trans.app.security_agent.associate_group_role(group, role)

        trans.sa_session.flush()
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
