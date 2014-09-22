"""
Manager and Serializer for histories.

Histories are containers for datasets or dataset collections
created (or copied) by users over the course of an analysis.
"""

from galaxy import exceptions
from galaxy.model import orm

from galaxy.managers import base as manager_base
import galaxy.managers.collections_util

import galaxy.web

import logging
log = logging.getLogger( __name__ )


# =============================================================================
class HistoryManager( manager_base.ModelManager ):
    """
    Interface/service object for interacting with HDAs.
    """

    #TODO: all the following would be more useful if passed the user instead of defaulting to trans.user
    def __init__( self, *args, **kwargs ):
        super( HistoryManager, self ).__init__( *args, **kwargs )

    def get( self, trans, unencoded_id, check_ownership=True, check_accessible=True, deleted=None ):
        """
        Get a History from the database by id, verifying ownership.
        """
        # this is a replacement for UsesHistoryMixin because mixins are a bad soln/structure
        history = trans.sa_session.query( trans.app.model.History ).get( unencoded_id )
        if history is None:
            raise exceptions.ObjectNotFound()
        if deleted is True and not history.deleted:
            raise exceptions.ItemDeletionException( 'History "%s" is not deleted' % ( history.name ), type="error" )
        elif deleted is False and history.deleted:
            raise exceptions.ItemDeletionException( 'History "%s" is deleted' % ( history.name ), type="error" )

        history = self.secure( trans, history, check_ownership, check_accessible )
        return history

    def by_user( self, trans, user=None, include_deleted=False, only_deleted=False ):
        """
        Get all the histories for a given user (defaulting to `trans.user`)
        ordered by update time and filtered on whether they've been deleted.
        """
        # handle default and/or anonymous user (which still may not have a history yet)
        user = user or trans.user
        if not user:
            current_history = trans.get_history()
            return [ current_history ] if current_history else []

        history_model = trans.model.History
        query = ( trans.sa_session.query( history_model )
                  .filter( history_model.user == user )
                  .order_by( orm.desc( history_model.table.c.update_time ) ) )
        if only_deleted:
            query = query.filter( history_model.deleted == True )
        elif not include_deleted:
            query = query.filter( history_model.deleted == False )
        return query.all()

    def secure( self, trans, history, check_ownership=True, check_accessible=True ):
        """
        Checks if (a) user owns item or (b) item is accessible to user.
        """
        # all items are accessible to an admin
        if trans.user and trans.user_is_admin():
            return history
        if check_ownership:
            history = self.check_ownership( trans, history )
        if check_accessible:
            history = self.check_accessible( trans, history )
        return history

    def is_current( self, trans, history ):
        """
        True if the given history is the user's current history.

        Returns False if the session has no current history.
        """
        if trans.history is None:
            return False
        return trans.history == history

    def is_owner( self, trans, history ):
        """
        True if the current user is the owner of the given history.
        """
        # anon users are only allowed to view their current history
        if not trans.user:
            return self.is_current( trans, history )
        return trans.user == history.user

    def check_ownership( self, trans, history ):
        """
        Raises error if the current user is not the owner of the history.
        """
        if trans.user and trans.user_is_admin():
            return history
        if not trans.user and not self.is_current( trans, history ):
            raise exceptions.AuthenticationRequired( "Must be logged in to manage Galaxy histories", type='error' )
        if self.is_owner( trans, history ):
            return history
        raise exceptions.ItemOwnershipException( "History is not owned by the current user", type='error' )

    def is_accessible( self, trans, history ):
        """
        True if the user can access (read) the current history.
        """
        # admin always have access
        if trans.user and trans.user_is_admin():
            return True
        # owner has implicit access
        if self.is_owner( trans, history ):
            return True
        # importable and shared histories are always accessible
        if history.importable:
            return True
        if trans.user in history.users_shared_with_dot_users:
            return True
        return False

    def check_accessible( self, trans, history ):
        """
        Raises error if the current user can't access the history.
        """
        if self.is_accessible( trans, history ):
            return history
        raise exceptions.ItemAccessibilityException( "History is not accessible to the current user", type='error' )

    #TODO: bleh...
    def _get_history_data( self, trans, history ):
        """
        Returns a dictionary containing ``history`` and ``contents``, serialized
        history and an array of serialized history contents respectively.
        """
        # import here prevents problems related to circular dependecy between histories and hdas managers.
        import galaxy.managers.hdas
        hda_mgr = galaxy.managers.hdas.HDAManager()
        collection_dictifier = galaxy.managers.collections_util.dictify_dataset_collection_instance

        history_dictionary = {}
        contents_dictionaries = []
        try:
            #for content in history.contents_iter( **contents_kwds ):
            for content in history.contents_iter( types=[ 'dataset', 'dataset_collection' ] ):
                hda_dict = {}

                if isinstance( content, trans.app.model.HistoryDatasetAssociation ):
                    try:
                        hda_dict = hda_mgr.get_hda_dict( trans, content )
                    except Exception, exc:
                        # don't fail entire list if hda err's, record and move on
                        log.exception( 'Error bootstrapping hda: %s', exc )
                        hda_dict = hda_mgr.get_hda_dict_with_error( trans, content, str( exc ) )

                elif isinstance( content, trans.app.model.HistoryDatasetCollectionAssociation ):
                    try:
                        service = trans.app.dataset_collections_service
                        dataset_collection_instance = service.get_dataset_collection_instance(
                            trans=trans,
                            instance_type='history',
                            id=trans.security.encode_id( content.id ),
                        )
                        hda_dict = collection_dictifier( dataset_collection_instance,
                            security=trans.security, parent=dataset_collection_instance.history, view="element" )

                    except Exception, exc:
                        log.exception( "Error in history API at listing dataset collection: %s", exc )
                        #TODO: return some dict with the error

                contents_dictionaries.append( hda_dict )

            # re-use the hdas above to get the history data...
            history_dictionary = self.get_history_dict( trans, history, contents_dictionaries=contents_dictionaries )

        except Exception, exc:
            user_id = str( trans.user.id ) if trans.user else '(anonymous)'
            log.exception( 'Error bootstrapping history for user %s: %s', user_id, str( exc ) )
            message = ( 'An error occurred getting the history data from the server. '
                      + 'Please contact a Galaxy administrator if the problem persists.' )
            history_dictionary[ 'error' ] = message

        return {
            'history'   : history_dictionary,
            'contents'  : contents_dictionaries
        }

    def get_history_dict( self, trans, history, contents_dictionaries=None ):
        """
        Returns history data in the form of a dictionary.
        """
        #TODO: to serializer
        history_dict = history.to_dict( view='element', value_mapper={ 'id':trans.security.encode_id })
        history_dict[ 'user_id' ] = None
        if history.user_id:
            history_dict[ 'user_id' ] = trans.security.encode_id( history.user_id )

        history_dict[ 'nice_size' ] = history.get_disk_size( nice_size=True )
        history_dict[ 'annotation' ] = history.get_item_annotation_str( trans.sa_session, history.user, history )
        if not history_dict[ 'annotation' ]:
            history_dict[ 'annotation' ] = ''

        #TODO: item_slug url
        if history_dict[ 'importable' ] and history_dict[ 'slug' ]:
            username_and_slug = ( '/' ).join(( 'u', history.user.username, 'h', history_dict[ 'slug' ] ))
            history_dict[ 'username_and_slug' ] = username_and_slug

#TODO: re-add
        #hda_summaries = hda_dictionaries if hda_dictionaries else self.get_hda_summary_dicts( trans, history )
        ##TODO remove the following in v2
        #( state_counts, state_ids ) = self._get_hda_state_summaries( trans, hda_summaries )
        #history_dict[ 'state_details' ] = state_counts
        #history_dict[ 'state_ids' ] = state_ids
        #history_dict[ 'state' ] = self._get_history_state_from_hdas( trans, history, state_counts )

        return history_dict

    def most_recent( self, trans, user=None, deleted=False ):
        user = user or trans.user
        if not user:
            return None if trans.history.deleted else trans.history

        #TODO: dup with by_user - should return query from there and call first and not all
        history_model = trans.model.History
        query = ( trans.sa_session.query( history_model )
                  .filter( history_model.user == user )
                  .order_by( orm.desc( history_model.table.c.update_time ) ) )
        if not deleted:
            query = query.filter( history_model.deleted == False )
        return query.first()

# =============================================================================
class HistorySerializer( manager_base.ModelSerializer ):
    """
    Interface/service object for serializing histories into dictionaries.
    """
    pass
