from typing import (
    Any,
    Dict,
    List,
)

from sqlalchemy import false

from galaxy import model
from galaxy.exceptions import (
    Conflict,
    ObjectAttributeMissingException,
    ObjectNotFound,
)
from galaxy.managers.base import decode_id
from galaxy.managers.context import ProvidesAppContext
from galaxy.schema.fields import EncodedDatabaseIdField
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

    def create(self, trans: ProvidesAppContext, payload: Dict[str, Any]):
        """
        Creates a new group.
        """
        name = payload.get("name", None)
        if name is None:
            raise ObjectAttributeMissingException("Missing required name")
        self._check_duplicated_group_name(trans, name)

        group = model.Group(name=name)
        trans.sa_session.add(group)
        encoded_user_ids = payload.get("user_ids", [])
        users = self._get_users_by_encoded_ids(trans, encoded_user_ids)
        encoded_role_ids = payload.get("role_ids", [])
        roles = self._get_roles_by_encoded_ids(trans, encoded_role_ids)
        trans.app.security_agent.set_entity_group_associations(groups=[group], roles=roles, users=users)
        trans.sa_session.flush()

        encoded_id = trans.security.encode_id(group.id)
        item = group.to_dict(view="element", value_mapper={"id": trans.security.encode_id})
        item["url"] = url_for("group", id=encoded_id)
        return [item]

    def show(self, trans: ProvidesAppContext, encoded_id: EncodedDatabaseIdField):
        """
        Displays information about a group.
        """
        group = self._get_group(trans, encoded_id)
        item = group.to_dict(view="element", value_mapper={"id": trans.security.encode_id})
        item["url"] = url_for("group", id=encoded_id)
        item["users_url"] = url_for("group_users", group_id=encoded_id)
        item["roles_url"] = url_for("group_roles", group_id=encoded_id)
        return item

    def update(self, trans: ProvidesAppContext, encoded_id: EncodedDatabaseIdField, payload: Dict[str, Any]):
        """
        Modifies a group.
        """
        group = self._get_group(trans, encoded_id)
        name = payload.get("name", None)
        if name:
            self._check_duplicated_group_name(trans, name)
            group.name = name
            trans.sa_session.add(group)
        encoded_user_ids = payload.get("user_ids", [])
        users = self._get_users_by_encoded_ids(trans, encoded_user_ids)
        encoded_role_ids = payload.get("role_ids", [])
        roles = self._get_roles_by_encoded_ids(trans, encoded_role_ids)
        trans.app.security_agent.set_entity_group_associations(
            groups=[group], roles=roles, users=users, delete_existing_assocs=False
        )
        trans.sa_session.flush()

    def _decode_id(self, encoded_id: EncodedDatabaseIdField) -> int:
        return decode_id(self._app, encoded_id)

    def _decode_ids(self, encoded_ids: List[EncodedDatabaseIdField]) -> List[int]:
        return [self._decode_id(encoded_id) for encoded_id in encoded_ids]

    def _check_duplicated_group_name(self, trans: ProvidesAppContext, group_name: str) -> None:
        if trans.sa_session.query(model.Group).filter(model.Group.name == group_name).first():
            raise Conflict(f"A group with name '{group_name}' already exists")

    def _get_group(self, trans: ProvidesAppContext, encoded_id: EncodedDatabaseIdField) -> model.Group:
        decoded_group_id = self._decode_id(encoded_id)
        group = trans.sa_session.query(model.Group).get(decoded_group_id)
        if group is None:
            raise ObjectNotFound(f"Group with id {encoded_id} was not found.")
        return group

    def _get_users_by_encoded_ids(
        self, trans: ProvidesAppContext, encoded_user_ids: List[EncodedDatabaseIdField]
    ) -> List[model.User]:
        decoded_user_ids = self._decode_ids(encoded_user_ids)
        users = trans.sa_session.query(model.User).filter(model.User.table.c.id.in_(decoded_user_ids)).all()
        return users

    def _get_roles_by_encoded_ids(
        self, trans: ProvidesAppContext, encoded_role_ids: List[EncodedDatabaseIdField]
    ) -> List[model.Role]:
        decoded_role_ids = self._decode_ids(encoded_role_ids)
        roles = trans.sa_session.query(model.Role).filter(model.Role.id.in_(decoded_role_ids)).all()
        return roles
