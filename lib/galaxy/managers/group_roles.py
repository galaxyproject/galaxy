import logging
from typing import (
    List,
    Optional,
)

from galaxy import model
from galaxy.exceptions import ObjectNotFound
from galaxy.managers.context import ProvidesAppContext
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.structured_app import MinimalManagerApp

log = logging.getLogger(__name__)


class GroupRolesManager:
    """Interface/service object shared by controllers for interacting with group roles."""

    def __init__(self, app: MinimalManagerApp) -> None:
        self._app = app

    def index(self, trans: ProvidesAppContext, group_id: int) -> List[model.GroupRoleAssociation]:
        """
        Returns a collection roles associated with the given group.
        """
        group = self._get_group(trans, group_id)
        return group.roles

    def show(self, trans: ProvidesAppContext, role_id: int, group_id: int) -> model.Role:
        """
        Returns information about a group role.
        """
        group = self._get_group(trans, group_id)
        role = self._get_role(trans, role_id)
        group_role = self._get_group_role(trans, group, role)
        if not group_role:
            raise ObjectNotFound(f"Role {role.name} not in group {group.name}")
        return role

    def update(self, trans: ProvidesAppContext, role_id: int, group_id: int) -> model.Role:
        """
        Adds a role to a group if it is not already associated.
        """
        group = self._get_group(trans, group_id)
        role = self._get_role(trans, role_id)
        group_role = self._get_group_role(trans, group, role)
        if not group_role:
            self._add_role_to_group(trans, group, role)
        return role

    def delete(self, trans: ProvidesAppContext, role_id: int, group_id: int) -> model.Role:
        """
        Removes a role from a group.
        """
        group = self._get_group(trans, group_id)
        role = self._get_role(trans, role_id)
        group_role = self._get_group_role(trans, group, role)
        if not group_role:
            raise ObjectNotFound(f"Role {role.name} not in group {group.name}")
        self._remove_role_from_group(trans, group_role)
        return role

    def _get_group(self, trans: ProvidesAppContext, group_id: int) -> model.Group:
        group = trans.sa_session.query(model.Group).get(group_id)
        if not group:
            raise ObjectNotFound(f"Group with id {DecodedDatabaseIdField.encode(group_id)} was not found.")
        return group

    def _get_role(self, trans: ProvidesAppContext, role_id: int) -> model.Role:
        role = trans.sa_session.query(model.Role).get(role_id)
        if not role:
            raise ObjectNotFound(f"Role with id {DecodedDatabaseIdField.encode(role_id)} was not found.")
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
