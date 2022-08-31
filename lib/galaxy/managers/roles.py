"""
Manager and Serializer for Roles.
"""
import logging
from typing import List

from sqlalchemy import false
from sqlalchemy.orm import exc as sqlalchemy_exceptions

import galaxy.exceptions
from galaxy import model
from galaxy.exceptions import RequestParameterInvalidException
from galaxy.managers import base
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import Role
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
            role = self.session().query(self.model_class).filter(self.model_class.id == role_id).one()
        except sqlalchemy_exceptions.MultipleResultsFound:
            raise galaxy.exceptions.InconsistentDatabase("Multiple roles found with the same id.")
        except sqlalchemy_exceptions.NoResultFound:
            raise galaxy.exceptions.RequestParameterInvalidException("No accessible role found with the id provided.")
        except Exception as e:
            raise galaxy.exceptions.InternalServerError(f"Error loading from the database.{unicodify(e)}")

        if not (trans.user_is_admin or trans.app.security_agent.ok_to_display(trans.user, role)):
            raise galaxy.exceptions.RequestParameterInvalidException("No accessible role found with the id provided.")

        return role

    def list_displayable_roles(self, trans: ProvidesUserContext) -> List[Role]:
        roles = []
        for role in trans.sa_session.query(Role).filter(Role.deleted == false()):
            if trans.user_is_admin or trans.app.security_agent.ok_to_display(trans.user, role):
                roles.append(role)
        return roles

    def create_role(self, trans: ProvidesUserContext, role_definition_model: RoleDefinitionModel) -> model.Role:
        name = role_definition_model.name
        description = role_definition_model.description
        user_ids = role_definition_model.user_ids or []
        group_ids = role_definition_model.group_ids or []

        if trans.sa_session.query(Role).filter(Role.name == name).first():
            raise RequestParameterInvalidException(f"A role with that name already exists [{name}]")

        role_type = Role.types.ADMIN  # TODO: allow non-admins to create roles

        role = Role(name=name, description=description, type=role_type)
        trans.sa_session.add(role)
        users = [trans.sa_session.query(model.User).get(i) for i in user_ids]
        groups = [trans.sa_session.query(model.Group).get(i) for i in group_ids]

        # Create the UserRoleAssociations
        for user in users:
            trans.app.security_agent.associate_user_role(user, role)

        # Create the GroupRoleAssociations
        for group in groups:
            trans.app.security_agent.associate_group_role(group, role)

        trans.sa_session.flush()
        return role
