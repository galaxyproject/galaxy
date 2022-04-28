import logging
from typing import (
    Any,
    Optional,
)

from galaxy import model
from galaxy.exceptions import ObjectNotFound
from galaxy.managers.base import decode_id
from galaxy.managers.context import ProvidesAppContext
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.structured_app import MinimalManagerApp

log = logging.getLogger(__name__)


class GroupRolesManager:
    """Interface/service object shared by controllers for interacting with group roles."""

    def __init__(self, app: MinimalManagerApp) -> None:
        self._app = app

    def index(self, trans: ProvidesAppContext, group_id: EncodedDatabaseIdField):
        """
        Returns a collection roles associated with the given group.
        """
        group = self._get_group(trans, group_id)
        return group.roles

    def show(self, trans: ProvidesAppContext, id: EncodedDatabaseIdField, group_id: EncodedDatabaseIdField):
        """
        Returns information about a group role.
        """
        role_id = id
        group = self._get_group(trans, group_id)
        role = self._get_role(trans, role_id)
        group_role = self._get_group_role(trans, group, role)
        if not group_role:
            raise ObjectNotFound(f"Role {role.name} not in group {group.name}")
        return role

    def update(self, trans: ProvidesAppContext, id: EncodedDatabaseIdField, group_id: EncodedDatabaseIdField):
        """
        Adds a role to a group if it is not already associated.
        """
        role_id = id
        group = self._get_group(trans, group_id)
        role = self._get_role(trans, role_id)
        group_role = self._get_group_role(trans, group, role)
        if not group_role:
            self._add_role_to_group(trans, group, role)
        return role

    def delete(self, trans: ProvidesAppContext, id: EncodedDatabaseIdField, group_id: EncodedDatabaseIdField):
        """
        Removes a role from a group.
        """
        role_id = id
        group = self._get_group(trans, group_id)
        role = self._get_role(trans, role_id)
        group_role = self._get_group_role(trans, group, role)
        if not group_role:
            raise ObjectNotFound(f"Role {role.name} not in group {group.name}")
        self._remove_role_from_group(trans, group_role)
        return role

    def _get_group(self, trans: ProvidesAppContext, encoded_group_id: EncodedDatabaseIdField) -> Any:
        decoded_group_id = decode_id(self._app, encoded_group_id)
        group = trans.sa_session.query(model.Group).get(decoded_group_id)
        if not group:
            raise ObjectNotFound(f"Group with id {encoded_group_id} was not found.")
        return group

    def _get_role(self, trans: ProvidesAppContext, encoded_role_id: EncodedDatabaseIdField) -> model.Role:
        decoded_role_id = decode_id(self._app, encoded_role_id)
        role = trans.sa_session.query(model.Role).get(decoded_role_id)
        if not role:
            raise ObjectNotFound(f"Role with id {encoded_role_id} was not found.")
        return role

    def _get_group_role(
        self, trans: ProvidesAppContext, group: model.Group, role: model.Role
    ) -> Optional[model.GroupRoleAssociation]:
        return (
            trans.sa_session.query(model.GroupRoleAssociation)
            .filter(model.GroupRoleAssociation.group == group, model.GroupRoleAssociation.role == role)
            .one_or_none()
        )

    def _add_role_to_group(self, trans: ProvidesAppContext, group: model.Group, role: model.Role):
        gra = model.GroupRoleAssociation(group, role)
        trans.sa_session.add(gra)
        trans.sa_session.flush()

    def _remove_role_from_group(self, trans: ProvidesAppContext, group_role: model.GroupRoleAssociation):
        trans.sa_session.delete(group_role)
        trans.sa_session.flush()
