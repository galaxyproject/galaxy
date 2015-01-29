"""
Manager and Serializer for Datasets.
"""
from galaxy import model
from galaxy import exceptions

from galaxy.managers import base
from galaxy.managers import users

import logging
log = logging.getLogger( __name__ )


class DatasetManager( base.ModelManager, base.AccessibleManagerMixin, base.PurgableManagerMixin ):
    """
    Manipulate datasets: the components contained in DatasetAssociations/DatasetInstances/HDAs/LDDAs
    """
    model_class = model.Dataset
    foreign_key_name = 'dataset'

    #TODO:?? get + error_if_uploading is common pattern, should upload check be worked into access/owed?

    def __init__( self, app ):
        super( DatasetManager, self ).__init__( app )
        # need for admin test
        self.user_manager = users.UserManager( app )

    def create( self, trans, flush=True, **kwargs ):
        """
        Create and return a new Dataset object.
        """
        # default to NEW state on new datasets
        kwargs.update( dict( state=( kwargs.get( 'state', model.Dataset.states.NEW ) ) ) )
        dataset = model.Dataset( **kwargs )

        self.app.model.context.add( dataset )
        if flush:
            self.app.model.context.flush()
        return dataset

    #def copy( self, dataset, **kwargs ):
    #    """
    #    Clone, update, and return the given dataset.
    #    """
    #    pass

    #def to_hda( self, trans, dataset, history, **kwargs ):
    #    """
    #    Create an hda from this dataset.
    #    """
    #    pass

    #def to_ldda( self, trans, dataset, library_folder, **kwargs ):
    #    """
    #    Create an ldda from this dataset.
    #    """
    #    pass

    #TODO: this may be more conv. somewhere else
#TODO: how to allow admin bypass?
    def error_unless_dataset_purge_allowed( self, trans, item, msg=None ):
        if not self.app.config.allow_user_dataset_purge:
            msg = msg or 'This instance does not allow user dataset purging'
            raise exceptions.ConfigDoesNotAllowException( msg )
        return item

    def purge( self, trans, dataset, flush=True ):
        """
        Remove the object_store/file for this dataset from storage and mark
        as purged.

        :raises exceptions.ConfigDoesNotAllowException: if the instance doesn't allow
        """
        self.error_unless_dataset_purge_allowed( trans, dataset )

        # the following also marks dataset as purged and deleted
        dataset.full_delete()
        self.app.model.context.add( dataset )
        if flush:
            self.app.model.context.flush()
        return dataset

    # .... accessibility
    # datasets can implement the accessible interface, but accessibility is checked in an entirely different way
    #   than those resources that have a user attribute (histories, pages, etc.)
    def is_accessible( self, trans, dataset, user ):
        """
        Is this dataset readable/viewable to user?
        """
        if self.user_manager.is_admin( trans, user ):
            return True
        if self.has_access_permission( trans, dataset, user ):
            return True
        return False

    def has_access_permission( self, trans, dataset, user ):
        """
        Return T/F if the user has role-based access to the dataset.
        """
        roles = user.all_roles() if user else []
        return self.app.security_agent.can_access_dataset( roles, dataset )

    #TODO: these need work
    def _access_permission( self, trans, dataset, user=None, role=None ):
        """
        Return most recent DatasetPermissions for the dataset and user.
        """
        security_agent = self.app.security_agent
        access_action = security_agent.permitted_actions.DATASET_ACCESS.action

        # get a list of role ids to check access for (defaulting to all_roles)
        user_roles = [ role ] if role else user.all_roles()
        user_role_ids = [ r.id for r in user_roles ]
        query = ( self.app.model.context.query( model.DatasetPermissions )
                    .filter( model.DatasetPermissions.action == access_action )
                    .filter( model.DatasetPermissions.dataset == dataset )
                    .filter( model.DatasetPermissions.role_id.in_( user_role_ids ) ) )
        #TODO:?? most recent?
        return query.first()

    def _create_access_permission( self, trans, dataset, role, flush=True ):
        """
        Create a new DatasetPermissions for the given dataset and role.
        """
        access_action = self.app.security_agent.permitted_actions.DATASET_ACCESS.action
        permission = model.DatasetPermissions( access_action, dataset, role )
        self.app.model.context.add( permission )
        if flush:
            self.app.model.context.flush()
        return permission

    #def give_access_permission( self, trans, dataset, user, flush=True ):
    #    """
    #    """
    #    # for now, use the user's private role
    #    security_agent = self.app.security_agent
    #    user_role = security_agent.get_private_user_role( user )
    #
    #    existing_permission = self._access_permission( trans, dataset, role=user_role )
    #    print 'existing access_perm:', existing_permission
    #    if existing_permission:
    #        return dataset
    #
    #    permission = self._create_access_permission( trans, dataset, user_role )
    #    print 'access_roles:', [ role.name for role in dataset.get_access_roles( trans ) ]
    #
    #    #access_action = security_agent.permitted_actions.DATASET_ACCESS.action
    #    #access_action = security_agent.get_action( access_action )
    #    #permissions = { access_action : [ user_role ] }
    #    #security_agent.set_dataset_permission( dataset, permissions )
    #
    #    #self.app.model.context.add( dataset )
    #    #if flush:
    #    #    self.app.model.context.flush()
    #
    #    dbl_chk = self._access_permission( trans, dataset, role=user_role )
    #    print 'access_perm:', dbl_chk
    #
    #    return dataset

    #def remove_access_permission( self, trans, dataset, user ):
    #    """
    #    """
    #    pass

    # .... manage/modify
    #def has_manage_permission( self, trans, dataset, user ):
    #    """
    #    """
    #    pass
    #
    #def give_manage_permission( self, trans, dataset, user ):
    #    """
    #    """
    #    pass
    #
    #def remove_manage_permission( self, trans, dataset, user ):
    #    """
    #    """
    #    pass

    #TODO: implement above for groups
    #TODO: datatypes?

    # .... data, object_store


class DatasetSerializer( base.ModelSerializer, base.PurgableSerializerMixin ):

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
        super( DatasetSerializer, self ).add_serializers()
        base.PurgableSerializerMixin.add_serializers( self )
        self.serializers.update({
            'id'            : self.serialize_id,
            'create_time'   : self.serialize_date,
            'update_time'   : self.serialize_date,
            'uuid'          : lambda t, i, k: str( i.uuid ) if i.uuid else None,
        })


class DatasetDeserializer( base.ModelDeserializer, base.PurgableDeserializerMixin ):
    model_manager_class = DatasetManager

    def add_deserializers( self ):
        super( DatasetDeserializer, self ).add_deserializers()
        base.PurgableDeserializerMixin.add_deserializers( self )



class DatasetAssociationManager( base.ModelManager, base.AccessibleManagerMixin, base.PurgableManagerMixin ):
    """
    DatasetAssociation/DatasetInstances are intended to be working
    proxies to a Dataset, associated with either a library or a
    user/history (HistoryDatasetAssociation).
    """
    # DA's were meant to be proxies - but were never fully implemented as them
    # Instead, a dataset association HAS a dataset but contains metadata specific to a library (lda) or user (hda)
    model_class = model.DatasetInstance

    def __init__( self, app ):
        super( DatasetAssociationManager, self ).__init__( app )
        self.dataset_manager = DatasetManager( app )

    def is_accessible( self, trans, dataset_assoc, user ):
        """
        Is this DA accessible to `user`?
        """
        # defer to the dataset
        return self.dataset_manager.is_accessible( trans, dataset_assoc.dataset, user )

    #def metadata( self, trans, dataset_assoc ):
    #    """
    #    Return the metadata collection.
    #    """
    #    # get metadata
    #    pass

    #def is_being_used( self, trans, dataset_assoc ):
    #    """
    #    """
    #    #TODO: check history_associations, library_associations
    #    pass


class DatasetAssociationSerializer( base.ModelSerializer, base.PurgableSerializerMixin ):

    def add_serializers( self ):
        super( DatasetAssociationSerializer, self ).add_serializers()
        base.PurgableSerializerMixin.add_serializers( self )


class DatasetAssociationDeserializer( base.ModelDeserializer, base.PurgableDeserializerMixin ):

    def add_deserializers( self ):
        super( DatasetAssociationDeserializer, self ).add_deserializers()
        base.PurgableDeserializerMixin.add_deserializers( self )
