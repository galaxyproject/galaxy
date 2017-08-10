"""
Manager and Serializer for Roles.
"""

from sqlalchemy.orm import exc as sqlalchemy_exceptions

import galaxy.exceptions
from galaxy import model
from galaxy.managers import base

import logging
log = logging.getLogger( __name__ )


class RoleManager( base.ModelManager ):
    """
    Business logic for roles.
    """
    model_class = model.Role
    foreign_key_name = 'role'

    user_assoc = model.UserRoleAssociation
    group_assoc = model.GroupRoleAssociation

    def __init__( self, app ):
        super( RoleManager, self ).__init__( app )

    def get( self, trans, decoded_role_id ):
        """
        Method loads the role from the DB based on the given role id.

        :param  decoded_role_id:      id of the role to load from the DB
        :type   decoded_role_id:      int

        :returns:   the loaded Role object
        :rtype:     galaxy.model.Role

        :raises: InconsistentDatabase, RequestParameterInvalidException, InternalServerError
        """
        try:
            role = ( self.session().query( self.model_class )
                     .filter( self.model_class.id == decoded_role_id ).one() )
        except sqlalchemy_exceptions.MultipleResultsFound:
            raise galaxy.exceptions.InconsistentDatabase( 'Multiple roles found with the same id.' )
        except sqlalchemy_exceptions.NoResultFound:
            raise galaxy.exceptions.RequestParameterInvalidException( 'No role found with the id provided.' )
        except Exception as e:
            raise galaxy.exceptions.InternalServerError( 'Error loading from the database.' + str(e) )
        return role
