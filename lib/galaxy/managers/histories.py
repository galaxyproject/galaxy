from galaxy import exceptions
from galaxy.model import orm


class HistoryManager( object ):
    #TODO: all the following would be more useful if passed the user instead of defaulting to trans.user

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
        checks if (a) user owns item or (b) item is accessible to user.
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
        return trans.history == history

    def is_owner( self, trans, history ):
        # anon users are only allowed to view their current history
        if not trans.user:
            return self.is_current( trans, history )
        return trans.user == history.user

    def check_ownership( self, trans, history ):
        if trans.user and trans.user_is_admin():
            return history
        if not trans.user and not self.is_current( trans, history ):
            raise exceptions.AuthenticationRequired( "Must be logged in to manage Galaxy histories", type='error' )
        if self.is_owner( trans, history ):
            return history
        raise exceptions.ItemOwnershipException( "History is not owned by the current user", type='error' )

    def is_accessible( self, trans, history ):
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
        if self.is_accessible( trans, history ):
            return history
        raise exceptions.ItemAccessibilityException( "History is not accessible to the current user", type='error' )
