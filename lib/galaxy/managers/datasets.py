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
    Manipulate datasets: the components contained in DatasetAssociations/DatasetInstances/HDAs/LDDAs
    
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
    def error_unless_dataset_purge_allowed( self, trans, item, msg=None ):
        if not trans.app.config.allow_user_dataset_purge:
            msg = msg or 'This instance does not allow user dataset purging'
            raise exceptions.ConfigDoesNotAllowException( msg )
        return item

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

    def _access_permission( self, trans, dataset, user=None, role=None ):
        """
        """
        security_agent = trans.app.security_agent
        access_action = security_agent.permitted_actions.DATASET_ACCESS.action

        # get a list of role ids to check access for (defaulting to all_roles)
        user_roles = [ role ] if role else user.all_roles()
        user_role_ids = [ role.id for role in user_roles ]
        query = ( trans.sa_session.query( model.DatasetPermissions )
                    .filter( model.DatasetPermissions.action == access_action )
                    .filter( model.DatasetPermissions.dataset == dataset )
                    .filter( model.DatasetPermissions.role_id.in_( user_role_ids ) ) )
        perms = query.all()
        if len( perms ):
            return perms[0]
        return None

    def _create_access_permission( self, trans, dataset, role, flush=True ):
        """
        """
        access_action = trans.app.security_agent.permitted_actions.DATASET_ACCESS.action
        permission = model.DatasetPermissions( access_action, dataset, role )
        trans.sa_session.add( permission )
        if flush:
            trans.sa_session.flush()
        return permission

    def has_access_permission( self, trans, dataset, user ):
        """
        """
        
        roles = user.all_roles() if user else []
        return trans.app.security_agent.can_access_dataset( roles, dataset )

    #TODO: this needs work
    #def give_access_permission( self, trans, dataset, user, flush=True ):
    #    """
    #    """
    #    # for now, use the user's private role
    #    security_agent = trans.app.security_agent
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
    #    #trans.sa_session.add( dataset )
    #    #if flush:
    #    #    trans.sa_session.flush()
    #
    #    dbl_chk = self._access_permission( trans, dataset, role=user_role )
    #    print 'access_perm:', dbl_chk
    #
    #    return dataset

    #def remove_access_permission( self, trans, dataset, user ):
    #    """
    #    """
    #    pass

    # ......................................................................... manage/modify
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
        # get metadata
        pass

    def is_being_used( self, trans, dataset_assoc ):
        """
        """
        #TODO: check history_associations, library_associations
        pass
