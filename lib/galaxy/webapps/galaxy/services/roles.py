from typing import Optional

from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.roles import RoleManager
from galaxy.model.db.role import get_private_role_user_emails_dict
from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    Security,
)
from galaxy.schema.schema import (
    RoleDefinitionModel,
    RoleListResponse,
    RoleModelResponse,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.webapps.base.controller import url_for
from galaxy.webapps.galaxy.services.base import ServiceBase


def role_to_model(role, displayed_name: Optional[str] = None):
    item = role.to_dict(view="element")
    role_id = Security.security.encode_id(role.id)
    item["url"] = url_for("role", id=role_id)
    if displayed_name:
        item["displayed_name"] = displayed_name
    return RoleModelResponse(**item)


class RolesService(ServiceBase):

    def __init__(
        self,
        security: IdEncodingHelper,
        role_manager: RoleManager,
    ):
        super().__init__(security)
        self.role_manager = role_manager

    def get_index(self, trans: ProvidesUserContext) -> RoleListResponse:
        roles = self.role_manager.list_displayable_roles(trans)
        private_role_emails = get_private_role_user_emails_dict(trans.sa_session)
        data = []
        for role in roles:
            displayed_name = private_role_emails.get(role.id, role.name)
            data.append(role_to_model(role, displayed_name))
        return RoleListResponse(root=data)

    def show(self, trans: ProvidesUserContext, id: DecodedDatabaseIdField) -> RoleModelResponse:
        role = self.role_manager.get(trans, id)
        return role_to_model(role)

    def create(self, trans: ProvidesUserContext, role_definition_model: RoleDefinitionModel):
        role = self.role_manager.create_role(trans, role_definition_model)
        return role_to_model(role)

    def delete(self, trans: ProvidesUserContext, id: DecodedDatabaseIdField) -> RoleModelResponse:
        role = self.role_manager.get(trans, id)
        role = self.role_manager.delete(trans, role)
        return role_to_model(role)

    def purge(self, trans: ProvidesUserContext, id: DecodedDatabaseIdField) -> RoleModelResponse:
        role = self.role_manager.get(trans, id)
        role = self.role_manager.purge(trans, role)
        return role_to_model(role)

    def undelete(self, trans: ProvidesUserContext, id: DecodedDatabaseIdField) -> RoleModelResponse:
        role = self.role_manager.get(trans, id)
        role = self.role_manager.undelete(trans, role)
        return role_to_model(role)
