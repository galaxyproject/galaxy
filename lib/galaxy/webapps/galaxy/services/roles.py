from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.roles import RoleManager
from galaxy.model.db.role import get_private_role_user_emails_dict
from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    Security,
)
from galaxy.schema.schema import (
    GroupModel,
    GroupModelListResponse,
    RoleDefinitionModel,
    RoleListResponse,
    RoleModelResponse,
    RoleUpdatePayload,
    RoleUserListResponse,
    RoleUserResponse,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.webapps.base.controller import url_for
from galaxy.webapps.galaxy.services.base import ServiceBase


def role_to_model(role, displayed_name: str | None = None):
    item = role.to_dict(view="element")
    role_id = Security.security.encode_id(role.id)
    item["url"] = url_for("role", id=role_id)
    # If displayed_name provided, use that value in place of Role.name. It is
    # used to disambiguate generic role names like "private role".
    if displayed_name:
        item["name"] = displayed_name
    return RoleModelResponse(**item)


class RolesService(ServiceBase):
    def __init__(
        self,
        security: IdEncodingHelper,
        role_manager: RoleManager,
    ):
        super().__init__(security)
        self.role_manager = role_manager

    def get_index(
        self,
        trans: ProvidesUserContext,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = 0,
        exclude_private: bool = False,
    ) -> RoleListResponse:
        roles = self.role_manager.list_displayable_roles(
            trans, search=search, limit=limit, offset=offset or 0, exclude_private=exclude_private
        )
        role_ids = {r.id for r in roles}
        private_role_emails = get_private_role_user_emails_dict(trans.sa_session, role_ids=role_ids)
        data = [role_to_model(role, private_role_emails.get(role.id, role.name)) for role in roles]
        return RoleListResponse(root=data)

    def show(self, trans: ProvidesUserContext, id: DecodedDatabaseIdField) -> RoleModelResponse:
        role = self.role_manager.get(trans, id)
        return role_to_model(role)

    def create(self, trans: ProvidesUserContext, role_definition_model: RoleDefinitionModel):
        role = self.role_manager.create_role(trans, role_definition_model)
        return role_to_model(role)

    def update(
        self, trans: ProvidesUserContext, id: DecodedDatabaseIdField, payload: RoleUpdatePayload
    ) -> RoleModelResponse:
        role = self.role_manager.get(trans, id)
        role = self.role_manager.update_role(trans, role, payload)
        return role_to_model(role)

    def get_users(self, trans: ProvidesUserContext, id: DecodedDatabaseIdField) -> RoleUserListResponse:
        role = self.role_manager.get(trans, id)
        users = self.role_manager.get_users(trans, role)
        return RoleUserListResponse(root=[RoleUserResponse(id=user_id, email=email) for user_id, email in users])

    def get_groups(self, trans: ProvidesUserContext, id: DecodedDatabaseIdField) -> GroupModelListResponse:
        role = self.role_manager.get(trans, id)
        groups = self.role_manager.get_groups(trans, role)
        return GroupModelListResponse(root=[GroupModel(id=group_id, name=name) for group_id, name in groups])

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
