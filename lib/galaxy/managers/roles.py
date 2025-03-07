"""
Manager and Serializer for Roles.
"""

import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.exc import (
    MultipleResultsFound,
    NoResultFound,
)

from galaxy import model
from galaxy.exceptions import (
    Conflict,
    InconsistentDatabase,
    InternalServerError,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.managers import base
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import Role
from galaxy.model.base import transaction
from galaxy.model.db.role import get_displayable_roles
from galaxy.schema.schema import RoleDefinitionModel
from galaxy.util import unicodify

log = logging.getLogger(__name__)


class RoleManager(base.ModelManager[model.Role]):
    """
    Business logic for roles.
    """

    model_class = model.Role
    foreign_key_name = "role"

    user_assoc = model.UserRoleAssociation
    group_assoc = model.GroupRoleAssociation

    def get(self, trans: ProvidesUserContext, role_id: int) -> model.Role:
        """
        Method loads the role from the DB based on the given role id.

        :param  role_id:      id of the role to load from the DB
        :type   role_id:      int

        :returns:   the loaded Role object
        :rtype:     galaxy.model.Role

        :raises: InconsistentDatabase, RequestParameterInvalidException, InternalServerError
        """
        try:
            stmt = select(self.model_class).where(self.model_class.id == role_id)
            role = self.session().execute(stmt).scalar_one()
        except MultipleResultsFound:
            raise InconsistentDatabase("Multiple roles found with the same id.")
        except NoResultFound:
            raise ObjectNotFound("No accessible role found with the id provided.")
        except Exception as e:
            raise InternalServerError(f"Error loading from the database.{unicodify(e)}")

        if not (trans.user_is_admin or trans.app.security_agent.ok_to_display(trans.user, role)):
            raise ObjectNotFound("No accessible role found with the id provided.")

        return role

    def list_displayable_roles(self, trans: ProvidesUserContext) -> List[Role]:
        return get_displayable_roles(trans.sa_session, trans.user, trans.user_is_admin, trans.app.security_agent)

    def create_role(self, trans: ProvidesUserContext, role_definition_model: RoleDefinitionModel) -> model.Role:
        name = role_definition_model.name
        description = role_definition_model.description
        user_ids = role_definition_model.user_ids or []
        group_ids = role_definition_model.group_ids or []

        stmt = select(Role).where(Role.name == name).limit(1)
        if trans.sa_session.scalars(stmt).first():
            raise Conflict(f"A role with that name already exists [{name}]")

        role_type = Role.types.ADMIN  # TODO: allow non-admins to create roles

        role = Role(name=name, description=description, type=role_type)
        trans.sa_session.add(role)
        users = [trans.sa_session.get(model.User, i) for i in user_ids]
        groups = [trans.sa_session.get(model.Group, i) for i in group_ids]

        # Create the UserRoleAssociations
        for user in users:
            trans.app.security_agent.associate_user_role(user, role)

        # Create the GroupRoleAssociations
        for group in groups:
            trans.app.security_agent.associate_group_role(group, role)

        with transaction(trans.sa_session):
            trans.sa_session.commit()
        return role

    def delete(self, trans: ProvidesUserContext, role: model.Role) -> model.Role:
        role.deleted = True
        trans.sa_session.add(role)
        with transaction(trans.sa_session):
            trans.sa_session.commit()
        return role

    def purge(self, trans: ProvidesUserContext, role: model.Role) -> model.Role:
        # This method should only be called for a Role that has previously been deleted.
        # Purging a deleted Role deletes all of the following from the database:
        # - UserRoleAssociations where role_id == Role.id
        # - DefaultUserPermissions where role_id == Role.id
        # - DefaultHistoryPermissions where role_id == Role.id
        # - GroupRoleAssociations where role_id == Role.id
        # - DatasetPermissionss where role_id == Role.id
        sa_session = trans.sa_session
        if not role.deleted:
            raise RequestParameterInvalidException(f"Role '{role.name}' has not been deleted, so it cannot be purged.")
        # Delete UserRoleAssociations
        for ura in role.users:
            user = sa_session.get(trans.app.model.User, ura.user_id)
            assert user
            # Delete DefaultUserPermissions for associated users
            for dup in user.default_permissions:
                if role == dup.role:
                    sa_session.delete(dup)
            # Delete DefaultHistoryPermissions for associated users
            for history in user.histories:
                for dhp in history.default_permissions:
                    if role == dhp.role:
                        sa_session.delete(dhp)
            sa_session.delete(ura)
        # Delete GroupRoleAssociations
        for gra in role.groups:
            sa_session.delete(gra)
        # Delete DatasetPermissionss
        for dp in role.dataset_actions:
            sa_session.delete(dp)
        # Delete the role
        sa_session.delete(role)
        with transaction(sa_session):
            sa_session.commit()
        return role

    def undelete(self, trans: ProvidesUserContext, role: model.Role) -> model.Role:
        if not role.deleted:
            raise RequestParameterInvalidException(
                f"Role '{role.name}' has not been deleted, so it cannot be undeleted."
            )
        role.deleted = False
        trans.sa_session.add(role)
        with transaction(trans.sa_session):
            trans.sa_session.commit()
        return role
