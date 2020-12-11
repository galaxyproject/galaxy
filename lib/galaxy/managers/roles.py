"""
Manager and Serializer for Roles.
"""
import logging

from sqlalchemy import false
from sqlalchemy.orm import exc as sqlalchemy_exceptions

import galaxy.exceptions
from galaxy import model
from galaxy.managers import base
from galaxy.util import unicodify

log = logging.getLogger(__name__)


class RoleManager(base.ModelManager):
    """
    Business logic for roles.
    """
    model_class = model.Role
    foreign_key_name = 'role'

    user_assoc = model.UserRoleAssociation
    group_assoc = model.GroupRoleAssociation

    def __init__(self, app):
        super().__init__(app)

    def get(self, trans, decoded_role_id):
        """
        Method loads the role from the DB based on the given role id.

        :param  decoded_role_id:      id of the role to load from the DB
        :type   decoded_role_id:      int

        :returns:   the loaded Role object
        :rtype:     galaxy.model.Role

        :raises: InconsistentDatabase, RequestParameterInvalidException, InternalServerError
        """
        try:
            role = (self.session().query(self.model_class)
                    .filter(self.model_class.id == decoded_role_id).one())
        except sqlalchemy_exceptions.MultipleResultsFound:
            raise galaxy.exceptions.InconsistentDatabase('Multiple roles found with the same id.')
        except sqlalchemy_exceptions.NoResultFound:
            raise galaxy.exceptions.RequestParameterInvalidException('No accessible role found with the id provided.')
        except Exception as e:
            raise galaxy.exceptions.InternalServerError('Error loading from the database.' + unicodify(e))

        if not (trans.user_is_admin or trans.app.security_agent.ok_to_display(trans.user, role)):
            raise galaxy.exceptions.RequestParameterInvalidException('No accessible role found with the id provided.')

        return role

    def list_displayable_roles(self, trans):
        roles = []
        for role in trans.sa_session.query(trans.app.model.Role).filter(trans.app.model.Role.table.c.deleted == false()):
            if trans.user_is_admin or trans.app.security_agent.ok_to_display(trans.user, role):
                roles.append(role)
        return roles
