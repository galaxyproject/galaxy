from typing import List

from sqlalchemy import false

from galaxy import model
from galaxy.exceptions import (
    Conflict,
    ObjectNotFound,
)
from galaxy.managers.context import ProvidesAppContext
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    GroupDefinitionModel,
    GroupUpdateModel,
)
from galaxy.structured_app import MinimalManagerApp
from galaxy.web import url_for


class GroupsManager:
    """Interface/service object shared by controllers for interacting with groups."""

    def __init__(self, app: MinimalManagerApp) -> None:
        self._app = app

    def index(self, trans: ProvidesAppContext):
        """
        Displays a collection (list) of groups.
        """
        rval = []
        for group in trans.sa_session.query(model.Group).filter(model.Group.deleted == false()):
            item = group.to_dict(value_mapper={"id": trans.security.encode_id})
            encoded_id = trans.security.encode_id(group.id)
            item["url"] = url_for("group", id=encoded_id)
            rval.append(item)
        return rval

    def create(self, trans: ProvidesAppContext, group_model: GroupDefinitionModel):
        """
        Creates a new group.
        """
        name = group_model.name
        self._check_duplicated_group_name(trans, name)

        group = model.Group(name=name)
        trans.sa_session.add(group)
        users = self._get_users_by_ids(trans, group_model.user_ids)
        roles = self._get_roles_by_ids(trans, group_model.role_ids)
        trans.app.security_agent.set_entity_group_associations(groups=[group], roles=roles, users=users)
        trans.sa_session.flush()

        encoded_id = trans.security.encode_id(group.id)
        item = group.to_dict(view="element", value_mapper={"id": trans.security.encode_id})
        item["url"] = url_for("group", id=encoded_id)
        return [item]

    def show(self, trans: ProvidesAppContext, group_id: int):
        """
        Displays information about a group.
        """
        group = self._get_group(trans, group_id)
        item = group.to_dict(view="element", value_mapper={"id": trans.security.encode_id})
        item["url"] = url_for("group", id=item["id"])
        item["users_url"] = url_for("group_users", group_id=item["id"])
        item["roles_url"] = url_for("group_roles", group_id=item["id"])
        return item

    def update(self, trans: ProvidesAppContext, group_id: int, group_model: GroupUpdateModel):
        """
        Modifies a group.
        """
        group = self._get_group(trans, group_id)
        name = group_model.name
        if name:
            self._check_duplicated_group_name(trans, name)
            group.name = name
            trans.sa_session.add(group)
        users = self._get_users_by_ids(trans, group_model.user_ids)
        roles = self._get_roles_by_ids(trans, group_model.role_ids)
        trans.app.security_agent.set_entity_group_associations(
            groups=[group], roles=roles, users=users, delete_existing_assocs=False
        )
        trans.sa_session.flush()

    def _check_duplicated_group_name(self, trans: ProvidesAppContext, group_name: str) -> None:
        if trans.sa_session.query(model.Group).filter(model.Group.name == group_name).first():
            raise Conflict(f"A group with name '{group_name}' already exists")

    def _get_group(self, trans: ProvidesAppContext, group_id: int) -> model.Group:
        group = trans.sa_session.query(model.Group).get(group_id)
        if group is None:
            raise ObjectNotFound("Group not found.")
        return group

    def _get_users_by_ids(self, trans: ProvidesAppContext, user_ids: List[DecodedDatabaseIdField]) -> List[model.User]:
        users = trans.sa_session.query(model.User).filter(model.User.table.c.id.in_(user_ids)).all()
        return users

    def _get_roles_by_ids(self, trans: ProvidesAppContext, role_ids: List[DecodedDatabaseIdField]) -> List[model.Role]:
        roles = trans.sa_session.query(model.Role).filter(model.Role.id.in_(role_ids)).all()
        return roles
