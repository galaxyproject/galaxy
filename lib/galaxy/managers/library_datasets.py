"""Manager and Serializer for library datasets."""
import logging

from sqlalchemy import and_, false, not_, or_, true

from galaxy import exceptions

log = logging.getLogger( __name__ )


class LibraryDatasetsManager( object ):
    """Interface/service object for interacting with library datasets."""

    def __init__( self, app ):
        self.app = app

    def get( self, trans, decoded_library_dataset_id, check_accessible=True ):
        """
        Get the library dataset from the DB.

        :param  decoded_library_dataset_id: decoded library dataset id
        :type   decoded_library_dataset_id: int
        :param  check_accessible:           flag whether to check that user can access item
        :type   check_accessible:           bool

        :returns:   the requested library dataset
        :rtype:     galaxy.model.LibraryDataset
        """
        try:
            ld = trans.sa_session.query( trans.app.model.LibraryDataset ).filter( trans.app.model.LibraryDataset.table.c.id == decoded_library_dataset_id ).one()
        except Exception as e:
            raise exceptions.InternalServerError( 'Error loading from the database.' + str( e ) )
        ld = self.secure( trans, ld, check_accessible)
        return ld

    def update( self, trans, ld, check_ownership=True, check_accessible=True ):
        """
        Update the given library dataset.

        :param  ld: library dataset to change
        :type   ld: LibraryDataset
        :param  check_ownership:           flag whether to check that user owns the item
        :type   check_ownership:           bool
        :param  check_accessible:          flag whether to check that user can access item
        :type   check_accessible:          bool

        :returns:   the changed library dataset
        :rtype:     galaxy.model.LibraryDataset

        :raises:
        """

    def secure( self, trans, ld, check_accessible=True, check_ownership=False ):
        """
        Check if library dataset is accessible to user.

        :param  ld:         library dataset
        :type   ld:         galaxy.model.LibraryDataset
        :param  check_accessible:        flag whether to check that user can access library dataset
        :type   check_accessible:        bool

        :returns:   the original library dataset
        :rtype:     galaxy.model.LibraryDataset
        """
        if trans.user_is_admin():
            # all operations are available to an admin
            return ld
        if check_accessible:
            ld = self._check_accessible( trans, ld )
        return ld


    def check_accessible( self, trans, ld ):
        """
        Check whether the library dataset is accessible to current user.

        :param  ld: library dataset
        :type   ld: galaxy.model.LibraryDataset

        :returns:   the original library dataset
        :rtype:     galaxy.model.LibraryDataset

        :raises:    ObjectNotFound
        """
        if not trans.app.security_agent.can_access_library_item( trans.get_current_user_roles(), ld ):
            raise exceptions.ObjectNotFound( 'Library dataset with the id provided was not found.' )
        elif ld.deleted:
            raise exceptions.ObjectNotFound( 'Library dataset with the id provided is deleted.' )
        else:
            return ld
