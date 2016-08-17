"""
Manager and Serializer for TS repositories.
"""
import logging

from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from galaxy.exceptions import (InconsistentDatabase, InternalServerError,
    RequestParameterInvalidException)

log = logging.getLogger( __name__ )


# =============================================================================
class RepoManager( object ):
    """
    Interface/service object for interacting with TS repositories.
    """

    def __init__( self, *args, **kwargs ):
        super( RepoManager, self ).__init__( *args, **kwargs )

    def get( self, trans, decoded_repo_id ):
        """
        Get the repo from the DB.

        :param  decoded_repo_id:       decoded repo id
        :type   decoded_repo_id:       int

        :returns:   the requested repo
        :rtype:     Repository
        """
        try:
            repo = trans.sa_session.query( trans.app.model.Repository ).filter( trans.app.model.Repository.table.c.id == decoded_repo_id ).one()
        except MultipleResultsFound:
            raise InconsistentDatabase( 'Multiple repositories found with the same id.' )
        except NoResultFound:
            raise RequestParameterInvalidException( 'No repository found with the id provided.' )
        except Exception:
            raise InternalServerError( 'Error loading from the database.' )
        return repo

    def list_by_owner( self, trans, user_id ):
        """
        Return a list of of repositories owned by a given TS user from the DB.

        :returns: query that will emit repositories owned by given user
        :rtype:   sqlalchemy query
        """
        query = trans.sa_session.query( trans.app.model.Repository ).filter( trans.app.model.Repository.table.c.user_id == user_id )
        return query

    def create( self, trans, name, description=''):
        """
        Create a new group.
        """

    def update( self, trans, group, name=None, description=None ):
        """
        Update the given group
        """

    def delete( self, trans, group, undelete=False ):
        """
        Mark given group deleted/undeleted based on the flag.
        """
