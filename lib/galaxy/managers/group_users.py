import logging
from typing import (
    List,
    Optional,
)

from sqlalchemy import select

from galaxy import model
from galaxy.exceptions import ObjectNotFound
from galaxy.managers.context import ProvidesAppContext
from galaxy.model import (
    User,
    UserGroupAssociation,
)
from galaxy.model.base import transaction
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.structured_app import MinimalManagerApp

log = logging.getLogger(__name__)


class GroupUsersManager:
    """Interface/service object shared by controllers for interacting with group users."""

    def __init__(self, app: MinimalManagerApp) -> None:
        self._app = app

    def index(self, trans: ProvidesAppContext, group_id: int) -> List[model.User]:
        """
        Returns a collection (list) with some information about users associated with the given group.
        """
        group = self._get_group(trans, group_id)
        return [uga.user for uga in group.users]

    def show(self, trans: ProvidesAppContext, user_id: int, group_id: int) -> model.User:
        """
        Returns information about a group user.
        """
        group = self._get_group(trans, group_id)
        user = self._get_user(trans, user_id)
        group_user = self._get_group_user(trans, group, user)
        if group_user is None:
            raise ObjectNotFound(f"User {user.email} not in group {group.name}")
        return user

    def update(self, trans: ProvidesAppContext, user_id: int, group_id: int) -> model.User:
        """
        Adds a user to a group.
        """
        group = self._get_group(trans, group_id)
        user = self._get_user(trans, user_id)
        group_user = self._get_group_user(trans, group, user)
        if group_user is None:
            self._add_user_to_group(trans, group, user)
        return user

    def delete(self, trans: ProvidesAppContext, user_id: int, group_id: int) -> model.User:
        """
        Removes a user from a group.
        """
        group = self._get_group(trans, group_id)
        user = self._get_user(trans, user_id)
        group_user = self._get_group_user(trans, group, user)
        if group_user is None:
            raise ObjectNotFound(f"User {user.email} not in group {group.name}")
        self._remove_user_from_group(trans, group_user)
        return user

    def _get_group(self, trans: ProvidesAppContext, group_id: int) -> model.Group:
        group = trans.sa_session.get(model.Group, group_id)
        if group is None:
            raise ObjectNotFound("Group with the id provided was not found.")
        return group

    def _get_user(self, trans: ProvidesAppContext, user_id: int) -> model.User:
        user = trans.sa_session.get(User, user_id)
        if user is None:
            raise ObjectNotFound("User with the id provided was not found.")
        return user

    def _get_group_user(
        self, trans: ProvidesAppContext, group: model.Group, user: model.User
    ) -> Optional[model.UserGroupAssociation]:
        return get_group_user(trans.sa_session, user, group)

    def _add_user_to_group(self, trans: ProvidesAppContext, group: model.Group, user: model.User):
        gra = model.UserGroupAssociation(user, group)
        trans.sa_session.add(gra)
        with transaction(trans.sa_session):
            trans.sa_session.commit()

    def _remove_user_from_group(self, trans: ProvidesAppContext, group_user: model.UserGroupAssociation):
        trans.sa_session.delete(group_user)
        with transaction(trans.sa_session):
            trans.sa_session.commit()


def get_group_user(session: galaxy_scoped_session, user, group) -> Optional[UserGroupAssociation]:
    stmt = (
        select(UserGroupAssociation).where(UserGroupAssociation.user == user).where(UserGroupAssociation.group == group)
    )
    return session.execute(stmt).scalar_one_or_none()
