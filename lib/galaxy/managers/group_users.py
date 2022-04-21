import logging
from typing import (
    Any,
    List,
    Optional,
)

from galaxy import model
from galaxy.exceptions import ObjectNotFound
from galaxy.managers.base import decode_id
from galaxy.managers.context import ProvidesAppContext
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.structured_app import MinimalManagerApp

log = logging.getLogger(__name__)


class GroupUsersManager:
    """Interface/service object shared by controllers for interacting with group users."""

    def __init__(self, app: MinimalManagerApp) -> None:
        self._app = app

    def index(self, trans: ProvidesAppContext, group_id: EncodedDatabaseIdField) -> List[model.User]:
        """
        Returns a collection (list) with some information about users associated with the given group.
        """
        group = self._get_group(trans, group_id)
        return [uga.user for uga in group.users]

    def show(
        self, trans: ProvidesAppContext, id: EncodedDatabaseIdField, group_id: EncodedDatabaseIdField
    ) -> model.User:
        """
        Returns information about a group user.
        """
        user_id = id
        group = self._get_group(trans, group_id)
        user = self._get_user(trans, user_id)
        group_user = self._get_group_user(trans, group, user)
        if group_user is None:
            raise ObjectNotFound(f"User {user.email} not in group {group.name}")
        return user

    def update(self, trans: ProvidesAppContext, id: EncodedDatabaseIdField, group_id: EncodedDatabaseIdField):
        """
        Adds a user to a group.
        """
        user_id = id
        group = self._get_group(trans, group_id)
        user = self._get_user(trans, user_id)
        group_user = self._get_group_user(trans, group, user)
        if group_user is None:
            self._add_user_to_group(trans, group, user)
        return user

    def delete(self, trans: ProvidesAppContext, id: EncodedDatabaseIdField, group_id: EncodedDatabaseIdField):
        """
        Removes a user from a group.
        """
        user_id = id
        group = self._get_group(trans, group_id)
        user = self._get_user(trans, user_id)
        group_user = self._get_group_user(trans, group, user)
        if group_user is None:
            raise ObjectNotFound(f"User {user.email} not in group {group.name}")
        self._remove_user_from_group(trans, group_user)
        return user

    def _get_group(self, trans: ProvidesAppContext, encoded_group_id: EncodedDatabaseIdField) -> Any:
        decoded_group_id = decode_id(self._app, encoded_group_id)
        group = trans.sa_session.query(model.Group).get(decoded_group_id)
        if group is None:
            raise ObjectNotFound(f"Group with id {encoded_group_id} was not found.")
        return group

    def _get_user(self, trans: ProvidesAppContext, encoded_user_id: EncodedDatabaseIdField) -> model.User:
        decoded_user_id = decode_id(self._app, encoded_user_id)
        user = trans.sa_session.query(model.User).get(decoded_user_id)
        if user is None:
            raise ObjectNotFound(f"User with id {encoded_user_id} was not found.")
        return user

    def _get_group_user(
        self, trans: ProvidesAppContext, group: model.Group, user: model.User
    ) -> Optional[model.UserGroupAssociation]:
        return (
            trans.sa_session.query(model.UserGroupAssociation)
            .filter(model.UserGroupAssociation.user == user, model.UserGroupAssociation.group == group)
            .one_or_none()
        )

    def _add_user_to_group(self, trans: ProvidesAppContext, group: model.Group, user: model.User):
        gra = model.UserGroupAssociation(user, group)
        trans.sa_session.add(gra)
        trans.sa_session.flush()

    def _remove_user_from_group(self, trans: ProvidesAppContext, group_user: model.UserGroupAssociation):
        trans.sa_session.delete(group_user)
        trans.sa_session.flush()
