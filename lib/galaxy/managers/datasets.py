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
    """
    """
    model_class = model.Dataset
    default_order_by = ( model.Dataset.create_time, )
    foreign_key_name = 'dataset'

    def __init__( self, app ):
        """
        """
        super( DatasetManager, self ).__init__( app )
        self.user_mgr = users.UserManager( app )

    # ......................................................................... create
    def create( self, trans, flush=True, **kwargs ):
        """
        """
        # default to NEW state on new datasets
        kwargs.update( dict( state=( kwargs.get( 'state', model.Dataset.states.NEW ) ) ) )
        dataset = model.Dataset( **kwargs )
        trans.sa_session.add( dataset )
        if flush:
            trans.sa_session.flush()
        return dataset

    def copy( self ):
        """
        """
        pass

    # ......................................................................... add to dataset association
    def to_hda( self, trans, dataset, history, **kwargs ):
        """
        """
        pass

    def to_ldda( self, trans, dataset, library_folder, **kwargs ):
        """
        """
        pass

    # ......................................................................... delete
    def purge( self, trans, dataset, flush=True ):
        """
        """
        self.error_unless_dataset_purge_allowed( trans, dataset )

        # the following also marks dataset as purged and deleted
        dataset.full_delete()
        trans.sa_session.add( dataset )
        if flush:
            trans.sa_session.flush()
        return dataset

    # ......................................................................... accessibility
    # datasets can implement the accessible interface, but accessibility is checked in an entirely different way
    #   than those resources that have a user attribute (histories, pages, etc.)
    def is_accessible( self, trans, dataset, user ):
        """
        """
        if self.user_mgr.is_admin( trans, user ):
            return True
        if self.has_access_permission( trans, dataset, user ):
            return True
        return False

    def has_access_permission( self, trans, dataset, user ):
        """
        """
        roles = user.roles if user else []
        return trans.app.security_agent.can_access_dataset( roles, dataset )

    def give_access_permission( self, trans, dataset, user ):
        """
        """
        #permission = {}
        ##TODO:?? is this correct and reliable?
        #user_private_role = self.user_mgr.private_role( trans, user )
        #permission[ trans.app.security_agent.permitted_actions.DATASET_ACCESS ] = [ user_private_role ]
        #trans.app.security_agent.set_dataset_permission( dataset, permission )
        pass

    def remove_access_permission( self, trans, dataset, user ):
        """
        """
        pass

    # ......................................................................... manage/modify
    def has_manage_permission( self, trans, dataset, user ):
        """
        """
        pass

    def give_manage_permission( self, trans, dataset, user ):
        """
        """
        pass

    def remove_manage_permission( self, trans, dataset, user ):
        """
        """
        pass

    #TODO: implement above for groups
    #TODO: datatypes?
    #TODO: data, object_store


# =============================================================================
class DatasetSerializer( base.ModelSerializer ):

    def __init__( self, app ):
        super( DatasetSerializer, self ).__init__( app )

        # most of these views build/add to the previous view
        summary_view = [
            'id',
            'create_time', 'update_time',
            'state',
            'deleted', 'purged', 'purgable',
            #'object_store_id',
            #'external_filename',
            #'extra_files_path',
            'file_size', 'total_size',
            'uuid',
        ]
        # could do visualizations and/or display_apps

        self.serializable_keys = summary_view + [
        ]
        self.views = {
            'summary'   : summary_view,
        }
        self.default_view = 'summary'

    def add_serializers( self ):
        self.serializers.update({
            'id'            : self.serialize_id,
            'create_time'   : self.serialize_date,
            'update_time'   : self.serialize_date,
            'uuid'          : lambda t, i, k: str( i.uuid ) if i.uuid else None,
        })


class DatasetDeserializer( base.ModelDeserializer ):
    pass


# =============================================================================
class DatasetAssociationManager( base.ModelManager, base.AccessibleModelInterface, base.PurgableModelInterface ):
    """
    """
    # A dataset association HAS a dataset but contains metadata specific to a library (lda) or user (hda)
    model_class = model.DatasetInstance
    default_order_by = ( model.Dataset.create_time, )

    def __init__( self, app ):
        """
        """
        super( DatasetAssociationManager, self ).__init__( app )
        self.dataset_mgr = DatasetManager( app )

    def is_accessible( self, trans, dataset_assoc, user ):
        """
        """
        # defer to the dataset
        return self.dataset_mgr.is_accessible( trans, dataset_assoc.dataset, user )

    def metadata( self, trans, dataset_assoc ):
        """
        """
        pass

    def is_being_used( self, trans, dataset_assoc ):
        """
        """
        pass
