"""
Manager and Serializer for Roles.
"""

import logging

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
from galaxy.model.db.role import (
    get_displayable_roles,
    get_role_groups,
    get_role_users,
)
from galaxy.schema.schema import (
    RoleDefinitionModel,
    RoleUpdatePayload,
)
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

    def list_displayable_roles(
        self,
        trans: ProvidesUserContext,
        search: str | None = None,
        limit: int | None = None,
        offset: int = 0,
        exclude_private: bool = False,
    ) -> list[Role]:
        return get_displayable_roles(
            trans.sa_session,
            trans.user,
            trans.user_is_admin,
            search=search,
            limit=limit,
            offset=offset,
            exclude_private=exclude_private,
        )

    def create_role(self, trans: ProvidesUserContext, role_definition_model: RoleDefinitionModel) -> model.Role:
        name = role_definition_model.name
        description = role_definition_model.description
        user_ids = role_definition_model.user_ids or []
        group_ids = role_definition_model.group_ids or []

        self._check_duplicated_role_name(trans, name)

        role_type = role_definition_model.role_type  # TODO: allow non-admins to create roles

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

        trans.sa_session.commit()
        return role

    def update_role(self, trans: ProvidesUserContext, role: model.Role, payload: RoleUpdatePayload) -> model.Role:
        if payload.name is not None:
            if not payload.name:
                raise RequestParameterInvalidException("Enter a valid role name.")
            self._check_duplicated_role_name(trans, payload.name, exclude_role_id=role.id)
            role.name = payload.name
        if payload.description is not None:
            role.description = payload.description
        trans.sa_session.add(role)
        # Commits the name and description together with the associations.
        trans.app.security_agent.set_role_user_and_group_associations(
            role, user_ids=payload.user_ids, group_ids=payload.group_ids
        )
        return role

    def get_users(self, trans: ProvidesUserContext, role: model.Role) -> list[tuple[int, str]]:
        """Return (id, email) of the role's non-deleted users."""
        return get_role_users(trans.sa_session, role.id)

    def get_groups(self, trans: ProvidesUserContext, role: model.Role) -> list[tuple[int, str]]:
        """Return (id, name) of the role's non-deleted groups."""
        return get_role_groups(trans.sa_session, role.id)

    def _check_duplicated_role_name(
        self, trans: ProvidesUserContext, name: str, exclude_role_id: int | None = None
    ) -> None:
        stmt = select(Role).where(Role.name == name)
        if exclude_role_id is not None:
            stmt = stmt.where(Role.id != exclude_role_id)
        if trans.sa_session.scalars(stmt.limit(1)).first():
            raise Conflict(f"A role with that name already exists [{name}]")

    def delete(self, trans: ProvidesUserContext, role: model.Role) -> model.Role:
        role.deleted = True
        trans.sa_session.add(role)
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
            user = sa_session.get(model.User, ura.user_id)
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
        sa_session.commit()
        return role

    def undelete(self, trans: ProvidesUserContext, role: model.Role) -> model.Role:
        if not role.deleted:
            raise RequestParameterInvalidException(
                f"Role '{role.name}' has not been deleted, so it cannot be undeleted."
            )
        role.deleted = False
        trans.sa_session.add(role)
        trans.sa_session.commit()
        return role
