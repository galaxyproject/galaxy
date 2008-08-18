"""
Galaxy Security

"""
import logging
from galaxy.util.bunch import Bunch

log = logging.getLogger(__name__)

# TODO, Nate: Think about whether the following permitted actions are appropriate for the dataset and
# group objects.  What should be the default "public" permitted actions?  Make sure that the public group
# and public datasets are set with the correct permitted actions.  Also make sure that "private" settings
# are correct when an authenticated user creates things inside their "private" environment.
class RBACAgent:
    """Class that handles galaxy security"""
    permitted_actions = Bunch(
        # The ability to edit the metadata of the associated dataset 
        DATASET_EDIT_METADATA = 'dataset_edit_metadata',
        # The ability to change the permissions of a dataset (so specifically, to add and modify 
        # group_dataset_association rows where the dataset is the dataset for which the permission is set). 
        DATASET_MANAGE_PERMISSIONS = 'dataset_manage_permissions',
        # The ability to perform any read only operation on the dataset (view, display at external site,
        # use in a job, etc).
        DATASET_ACCESS = 'dataset_access'
    )
    def allow_action( self, user, action, **kwd ):
        raise 'No valid method of checking action (%s) on %s for user %s.' % ( action, kwd, user )
    def guess_derived_groups_permitted_actions_for_datasets( self, datasets = [] ):
        raise "Unimplemented Method"
    def associate_components( self, **kwd ):
        raise 'No valid method of associating provided components: %s' % kwd
    def get_group( self, id ):
        raise 'No valid method of retrieving group %s' % ( id )
    def create_group( self, **kwd ):
        raise 'No valid method of creating group with %s' % ( kwd )
    def create_private_user_group( self, user ):
        raise "Unimplemented Method"
    def user_set_default_access( self, user, groups = None, history = False, dataset = False ):
        raise "Unimplemented Method"
    def setup_new_user( self, user ):
        self.user_set_default_access( user, history = True, dataset = True )
        self.associate_components( user=user, group=self.get_public_group() )
    def history_set_default_access( self, history, groups=None, dataset=False ):
        raise "Unimplemented Method"
    def set_public_group( self, group ):
        raise "Unimplemented Method"
    def get_public_group( self ):
        raise "Unimplemented Method"
    def guess_public_group( self ):
        raise "Unimplemented Method"
    def set_dataset_groups( self, dataset, groups ):
        raise "Unimplemented Method"
    def set_dataset_permitted_actions( self, dataset ):
        raise "Unimplemented Method"
    def get_component_associations( self, **kwd ):
        raise "Unimplemented Method"
    def components_are_associated( self, **kwd ):
        return bool( self.get_component_associations( **kwd ) )

class GalaxyRBACAgent( RBACAgent ):
    def __init__( self, model, permitted_actions=None ):
        self.model = model
        if permitted_actions:
            self.permitted_actions = permitted_actions
    def allow_action( self, user, action, **kwd ):
        if 'dataset' in kwd:
            return self.allow_dataset_action( user, action, kwd['dataset'] )
        raise 'No valid method of checking action (%s) on %s for user %s.' % ( action, kwd, user )
    def allow_dataset_action( self, user, action, dataset ):
        """Returns true when user has permission to perform an action"""
        if not isinstance( dataset, self.model.Dataset ):
            dataset = dataset.dataset
        # If dataset is in public group, we always return true for viewing and using
        # This may need to change when the ability to alter groups and permitted_actions is allowed
        if action == self.permitted_actions.DATASET_ACCESS and \
            self.components_are_associated( group = self.get_public_group(), dataset = dataset ):
            return True
        elif user is not None:
            # Loop through permitted_actions and if allowed return true:
            # Check permitted_actions associated with dataset through groups
            for group_dataset_assoc in dataset.groups:
                if self.components_are_associated( user = user, group = group_dataset_assoc.group ):
                    if action in group_dataset_assoc.permitted_actions:
                        return True
        return False # No user and dataset not in public group, or user lacks permission
    def guess_derived_groups_for_datasets( self, datasets=[] ):
         # TODO, Nate: Make sure this method is functionally correct.
        """Returns a list of groups for the output dataset based upon itself and provided datasets"""
        access_groups = None
        priority_access_group = None
        for dataset in datasets:
            # Determine access groups for output datasets - these groups are the 
            # intersection across all inputs.  If we end up with no intersection 
            # between inputs, then we rely on priorities
            if isinstance( dataset, self.model.HistoryDatasetAssociation ):
                dataset = dataset.dataset
            groups = [ data_group_assoc.group for data_group_assoc in dataset.groups ]
            for group in groups:
                if priority_access_group is None or priority_access_group.priority < group.priority:
                    priority_access_group = group
            if access_groups is None:
                access_groups = set( groups )
            else:
                access_groups.intersection_update( set( groups ) )
        # Complete lists for output dataset access
        if access_groups:
            access_groups = list( access_groups)
        else:
            access_groups = []
        # If we have no groups left after intersection, take the highest priority group
        if not access_groups:
            if priority_access_group:
                access_groups = [ priority_access_group ]
        return access_groups
    def get_group( self, id ):
        return self.model.Group.get( id )
        raise 'No valid method of retrieving requested group %s' % ( id )    
    def create_group( self, **kwd ):
        rval = self.model.Group( **kwd )
        rval.flush()
        return rval
        raise 'No valid method of creating group with %s' % ( kwd )
    def associate_components( self, **kwd ):
        assert len( kwd ) == 2, 'You must specify exactly 2 Galaxy security components to associate.'
        if 'dataset' in kwd:
            if 'group' in kwd:
                return self.associate_group_dataset( kwd['group'], kwd['dataset'] )
        elif 'user' in kwd:
            if 'group' in kwd:
                return self.associate_user_group( kwd['user'], kwd['group'] )
        raise 'No valid method of associating provided components: %s' % kwd
    def disassociate_components( self, **kwd ):
        assert len( kwd ) == 2, 'You must specify exactly 2 Galaxy security components to disassociate.'
        if 'dataset' in kwd:
            if 'group' in kwd:
                return self.disassociate_group_dataset( kwd['group'], kwd['dataset'] )
        raise 'No valid method of associating provided components: %s' % kwd
    def associate_group_dataset( self, group, dataset, permitted_actions=[] ):
        if not permitted_actions:
            if isinstance( dataset.permitted_actions, Bunch ):
                permitted_actions = dataset.permitted_actions.__dict__.values()
            else:
                permitted_actions = dataset.permitted_actions
        assoc = self.model.GroupDatasetAssociation( group, dataset, permitted_actions )
        assoc.flush()
        return assoc
    def disassociate_group_dataset( self, group, dataset ):
        assoc = self.model.GroupDatasetAssociation.selectone_by( group_id = group.id, dataset_id = dataset.id )
        assoc.delete()
        assoc.flush()
    def associate_user_group( self, user, group ):
        assoc = self.model.UserGroupAssociation( user, group )
        assoc.flush()
        return assoc
    def create_private_user_group( self, user ):
        # Create private group
        group_name = "%s private group" % user.email
        group = self.model.Group( name=group_name, priority=10 )
        group.flush()        
        # Add user to group
        self.associate_components( group=group, user=user )
        group.flush()
        return group
    def user_set_default_access( self, user, groups = None, history = False, dataset = False ):
        # TODO, Nate: Make sure this method is functionally correct with permitted actions set appropriately.
        if groups is None:
            groups = [ self.create_private_user_group( user ) ]
        if groups is not None:
            for assoc in user.default_groups: #this is the association not the actual group
                assoc.delete()
                assoc.flush()
            for group in groups:
                if isinstance( group, self.model.Group ):
                    permitted_actions = group.permitted_actions.__dict__.values()
                else:
                    permitted_actions = group.permitted_actions
                assoc = self.model.DefaultUserGroupAssociation( user, group, permitted_actions )
                assoc.flush()
        if history:
            for history in user.histories:
                self.history_set_default_access( history, groups=groups, dataset=dataset )
    def history_set_default_access( self, history, groups=None, dataset=False ):
        # TODO, Nate: Make sure this method is functionally correct with permitted actions set appropriately.
        if groups is None:
            if history.user:
                groups = [ assoc.group for assoc in history.user.default_groups ]
            else:
                groups = [ self.get_public_group() ]
        if groups is not None:
            for assoc in history.default_groups: #this is the association not the actual group
                assoc.delete()
                assoc.flush()
            for group in groups:
                if isinstance( group, self.model.Group ):
                    permitted_actions = group.permitted_actions.__dict__.values()
                else:
                    permitted_actions = group.permitted_actions
                assoc = self.model.DefaultHistoryGroupAssociation( history, group, permitted_actions )
                assoc.flush()
        if dataset:
            for data in history.datasets:
                for hda in data.dataset.history_associations:
                    if history.user and hda.history not in history.user.histories:
                        self.set_dataset_groups( data.dataset, [ self.get_public_group() ] )
                        break
                else:
                    self.set_dataset_groups( data.dataset, groups )
    def get_public_group( self ):
        return self.model.Group.get_public_group()
    def set_public_group( self, group ):
        return self.model.Group.set_public_group( group )
    def guess_public_group( self ):
        return self.model.Group.guess_public_group()
    def set_dataset_groups( self, dataset, groups ):
        if isinstance( dataset, self.model.HistoryDatasetAssociation ):
            dataset = dataset.dataset
        for group_dataset_assoc in dataset.groups:
            group_dataset_assoc.delete()
            group_dataset_assoc.flush()
        for group in groups:
            if not isinstance( group, self.model.Group ):
                group = group.group
            self.associate_components( dataset=dataset, group=group )
    def get_component_associations( self, **kwd ):
        # TODO, Nate: Make sure this method is functionally correct.
        assert len( kwd ) == 2, 'You must specify exactly 2 Galaxy security components to check for associations.'
        if 'dataset' in kwd:
            if 'group' in kwd:
                return self.model.GroupDatasetAssociation.get_by( group_id = kwd['group'].id, dataset_id = kwd['dataset'].id )
        elif 'user' in kwd:
            if 'group' in kwd:
                return self.model.UserGroupAssociation.get_by( group_id = kwd['group'].id, user_id = kwd['user'].id )
        raise 'No valid method of associating provided components: %s' % kwd
    def dataset_has_group( self, dataset_id, group_id ):
        return bool( self.model.GroupDatasetAssociation.get_by( group_id = group_id, dataset_id = dataset_id  )  )

def get_permitted_actions( self, filter=None ):
    '''Utility method to return a subset of RBACAgent's permitted actions'''
    if filter is None:
        return RBACAgent.permitted_actions
    if not filter.endswith('_'):
        filter += '_'
    tmp_bunch = Bunch()
    [tmp_bunch.__dict__.__setitem__(k, v) for k, v in RBACAgent.permitted_actions.items() if k.startswith(filter)]
    return tmp_bunch
