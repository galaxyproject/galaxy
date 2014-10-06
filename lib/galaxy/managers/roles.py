"""
Manager and Serializer for Roles.
"""

import galaxy.web
from galaxy import exceptions
from galaxy.model import orm
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound

import logging
log = logging.getLogger( __name__ )


# =============================================================================
class RoleManager( object ):
    """
    Interface/service object for interacting with folders.
    """

    def get( self, trans, decoded_role_id):
      """
      Method loads the role from the DB based on the given role id.

      :param  decoded_role_id:      id of the role to load from the DB
      :type   decoded_role_id:      int

      :returns:   the loaded Role object
      :rtype:     Role

      :raises: InconsistentDatabase, RequestParameterInvalidException, InternalServerError
      """
      try:
          role = trans.sa_session.query( trans.app.model.Role ).filter( trans.model.Role.table.c.id == decoded_role_id ).one()
      except MultipleResultsFound:
          raise exceptions.InconsistentDatabase( 'Multiple roles found with the same id.' )
      except NoResultFound:
          raise exceptions.RequestParameterInvalidException( 'No role found with the id provided.' )
      except Exception, e:
          raise exceptions.InternalServerError( 'Error loading from the database.' + str(e) )
      return role
