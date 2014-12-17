"""
Manager and Serializer for Datasets.
"""
from galaxy import model
from galaxy import exceptions

import base
import users

import logging
log = logging.getLogger( __name__ )


# =============================================================================
class DatasetManager( base.ModelManager, base.AccessibleModelInterface, base.PurgableModelInterface ):
    model_class = model.Dataset
    default_order_by = ( model.Dataset.create_time, )
    foreign_key_name = 'dataset'

    def __init__( self, app ):
        super( DatasetManager, self ).__init__( app )
        self.user_mgr = users.UserManager( app )

    # ------------------------------------------------------------------------- CRUD
    def create( self, trans, flush=True, **kwargs ):
        # default to NEW state on new datasets
        kwargs.update( dict( state=( kwargs.get( 'state', model.Dataset.states.NEW ) ) ) )
        dataset = model.Dataset( **kwargs )
        trans.sa_session.add( dataset )
        if flush:
            trans.sa_session.flush()
        return dataset

    #def to_hda( self, trans, dataset, history, **kwargs ):
    #    pass

    #def to_ldda( self, trans, dataset, library_folder, **kwargs ):
    #    pass

    #def copy( self ):
    #    pass

    def purge( self, trans, dataset, flush=True ):
        self.error_unless_dataset_purge_allowed( trans, dataset )

        # the following also marks dataset as purged and deleted
        dataset.full_delete()
        trans.sa_session.add( dataset )
        if flush:
            trans.sa_session.flush()
        return dataset

    # ------------------------------------------------------------------------- accessibility
    # datasets can implement the accessible interface, but accessibility is checked in an entirely different way
    #   than those resources that have a user attribute (histories, pages, etc.)
    def is_accessible( self, trans, dataset, user ):
        if self.user_mgr.is_admin( trans, user ):
            return True
        if self.has_access_permission( trans, dataset, user ):
            return True
        return False

    def has_access_permission( self, trans, dataset, user ):
        return trans.app.security_agent.can_access_dataset( user.roles, dataset )

    #def give_access_permission( self, trans, dataset, user ):
    #    permission = {}
    #    #TODO:?? is this correct and reliable?
    #    user_private_role = self.user_mgr.private_role( trans, user )
    #    permission[ trans.app.security_agent.permitted_actions.DATASET_ACCESS ] = [ user_private_role ]
    #    trans.app.security_agent.set_dataset_permission( dataset, permission )


    #def remove_access_permission( self, trans, dataset, user ):
    #    pass


    #def has_manage_permission( self, trans, dataset, user ):
    #    pass
    #
    #def give_manage_permission( self, trans, dataset, user ):
    #    pass
    #
    #def remove_manage_permission( self, trans, dataset, user ):
    #    pass


    #TODO: implement above for groups

#TODO: datatypes?


# =============================================================================
class DatasetAssociationManager( base.ModelManager, base.AccessibleModelInterface, base.PurgableModelInterface ):

    def __init__( self, app ):
        super( DatasetAssociationManager, self ).__init__( app )
        self.dataset_mgr = DatasetManager( app )

    def is_accessible( self, trans, dataset_assoc, user ):
        # defer to the dataset
        return self.dataset_mgr.is_accessible( trans, dataset_assoc.dataset, user )
