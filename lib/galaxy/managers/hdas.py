from galaxy import exceptions
from ..managers import histories


class HDAManager( object ):

    def __init__( self ):
        self.histories_mgr = histories.HistoryManager()

    def get( self, trans, unencoded_id, check_ownership=True, check_accessible=True ):
        """
        """
        # this is a replacement for UsesHistoryDatasetAssociationMixin because mixins are a bad soln/structure
        hda = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( unencoded_id )
        if hda is None:
            raise exceptions.ObjectNotFound()
        hda = self.secure( trans, hda, check_ownership, check_accessible )
        return hda

    def secure( self, trans, hda, check_ownership=True, check_accessible=True ):
        """
        checks if (a) user owns item or (b) item is accessible to user.
        """
        # all items are accessible to an admin
        if trans.user and trans.user_is_admin():
            return hda
        if check_ownership:
            hda = self.check_ownership( trans, hda )
        if check_accessible:
            hda = self.check_accessible( trans, hda )
        return hda

    def can_access_dataset( self, trans, hda ):
        current_user_roles = trans.get_current_user_roles()
        return trans.app.security_agent.can_access_dataset( current_user_roles, hda.dataset )

    #TODO: is_owner, is_accessible

    def check_ownership( self, trans, hda ):
        if not trans.user:
            #if hda.history == trans.history:
            #    return hda
            raise exceptions.AuthenticationRequired( "Must be logged in to manage Galaxy datasets", type='error' )
        if trans.user_is_admin():
            return hda
        # check for ownership of the containing history and accessibility of the underlying dataset
        if( self.histories_mgr.is_owner( trans, hda.history )
                and self.can_access_dataset( trans, hda ) ):
            return hda
        raise exceptions.ItemOwnershipException(
            "HistoryDatasetAssociation is not owned by the current user", type='error' )

    def check_accessible( self, trans, hda ):
        if trans.user and trans.user_is_admin():
            return hda
        # check for access of the containing history...
        self.histories_mgr.check_accessible( trans, hda.history )
        # ...then the underlying dataset
        if self.can_access_dataset( trans, hda ):
            return hda
        raise exceptions.ItemAccessibilityException(
            "HistoryDatasetAssociation is not accessible to the current user", type='error' )

    def err_if_uploading( self, trans, hda ):
        if hda.state == trans.model.Dataset.states.UPLOAD:
            raise exceptions.Conflict( "Please wait until this dataset finishes uploading" )
        return hda
