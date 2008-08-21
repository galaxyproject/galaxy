"""
Galaxy Security

"""
import logging
from galaxy.util.bunch import Bunch

log = logging.getLogger(__name__)

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
    permitted_action_descriptions = Bunch(
        DATASET_EDIT_METADATA = "Edit this dataset's metadata in the library",
        DATASET_MANAGE_PERMISSIONS = "Manage the groups associated with this dataset (and those groups' permissions on the dataset)",
        DATASET_ACCESS = "View, import, and perform analyses on this dataset"
    )
    def allow_action( self, user, action, **kwd ):
        raise 'No valid method of checking action (%s) on %s for user %s.' % ( action, kwd, user )
    def guess_derived_permissions_for_datasets( self, datasets = [] ):
        raise "Unimplemented Method"
    def associate_components( self, **kwd ):
        raise 'No valid method of associating provided components: %s' % kwd
    def get_group( self, id ):
        raise 'No valid method of retrieving group %s' % ( id )
    def create_group( self, **kwd ):
        raise 'No valid method of creating group with %s' % ( kwd )
    def create_private_user_group( self, user ):
        raise "Unimplemented Method"
    def user_set_default_access( self, user, permissions = None, history = False, dataset = False ):
        raise "Unimplemented Method"
    def setup_new_user( self, user ):
        self.user_set_default_access( user, history = True, dataset = True )
        self.associate_components( user=user, group=self.get_public_group() )
    def history_set_default_access( self, history, permissions=None, dataset=False ):
        raise "Unimplemented Method"
    def set_public_group( self, group ):
        raise "Unimplemented Method"
    def get_public_group( self ):
        raise "Unimplemented Method"
    def guess_public_group( self ):
        raise "Unimplemented Method"
    def set_dataset_permissions( self, dataset, permissions ):
        raise "Unimplemented Method"
    def set_dataset_permitted_actions( self, dataset ):
        raise "Unimplemented Method"
    def get_component_associations( self, **kwd ):
        raise "Unimplemented Method"
    def components_are_associated( self, **kwd ):
        return bool( self.get_component_associations( **kwd ) )
    def convert_permitted_action_strings( self, permitted_action_strings ):
        """
        When getting permitted actions from an untrusted source like a
        form, ensure that they match our actual permitted actions.
        """
        return filter( lambda x: x is not None, [ self.permitted_actions.get( action_string ) for action_string in permitted_action_strings ] )
    def get_permitted_action_description( self, permitted_action ):
        """
        Return the description of a permitted_action, regardless of
        whether permitted_action is a key or value.
        """
        if self.permitted_action_descriptions.get( permitted_action ) is not None:
            return self.permitted_action_descriptions.get( permitted_action )
        else:
            for k, v in self.permitted_actions.items():
                if v == permitted_action:
                    return self.permitted_action_descriptions.get( k )
            return permitted_action # so at least something useful is printable

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
    def guess_derived_permissions_for_datasets( self, datasets=[] ):
        """Returns a list of group/action tuples for the output dataset based upon provided datasets"""
        intersect = None
        priority_access_perms = None
        for dataset in datasets:
            # Determine access groups for output datasets - these groups are the 
            # intersection across all inputs.  If we end up with no intersection 
            # between inputs, then we rely on priorities
            if isinstance( dataset, self.model.HistoryDatasetAssociation ):
                dataset = dataset.dataset
            assocs = [ assoc for assoc in dataset.groups ]
            for assoc in assocs:
                if priority_access_perms is None or priority_access_perms[0].priority < assoc.group.priority:
                    priority_access_perms = ( assoc.group, assoc.permitted_actions )
            if intersect is None:
                intersect = [ (a.group, a.permitted_actions) for a in assocs ]
            else:
                # Intersect existing perms with new perms
                #access_assocs = filter( lambda x: x.group in [ a.group for a in access_assocs ], assocs )
                new_intersect = []
                for group, actions in intersect:
                    matches = filter( lambda x: x.group == group, assocs )
                    # Could a dataset ever have more than one GDA with the same group id?
                    if len( matches ) > 1:
                        log.error( "Unable to derive permissions, duplicate group_dataset_association rows exist for group %d, dataset %d" % (group.id, dataset.id) )
                    elif len( matches ) == 1:
                        # compare permitted_actions
                        pa_intersect = filter( lambda x: x in actions, matches[0].permitted_actions )
                        new_intersect.append( ( group, pa_intersect ) )
                intersect = new_intersect
        # If we have no groups left after intersection, take the highest priority group
        if not intersect:
            if priority_access_perms:
                intersect = [ priority_access_perms ]
        return intersect
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
            elif 'permissions' in kwd:
                return self.associate_group_dataset( kwd['permissions'][0], kwd['dataset'], kwd['permissions'][1] )
        elif 'user' in kwd:
            if 'group' in kwd:
                return self.associate_user_group( kwd['user'], kwd['group'] )
        raise 'No valid method of associating provided components: %s' % kwd
    def associate_group_dataset( self, group, dataset, permitted_actions=[ RBACAgent.permitted_actions.DATASET_ACCESS ] ):
        # HACK: The default permitted_actions should really not be used... need to find cases where this is done and correct it
        log.debug("In associate_permissions_dataset, dataset: %d, group: %d, permitted_actions: %s" % ( dataset.id, group.id, permitted_actions ) )
        assoc = self.model.GroupDatasetAssociation( group, dataset, permitted_actions )
        assoc.flush()
        return assoc
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
    def user_set_default_access( self, user, permissions = None, history = False, dataset = False ):
        if permissions is None:
            permissions = [ ( self.create_private_user_group( user ), self.permitted_actions.__dict__.values() ) ]
        if permissions is not None:
            for assoc in user.default_groups: #this is the association not the actual group
                assoc.delete()
                assoc.flush()
            for group, permitted_actions in permissions:
                log.debug("In user_set_default_access, user: %s, group: %s, permitted_actions: %s" % (user.email, group.name, str( permitted_actions)))
                assoc = self.model.DefaultUserGroupAssociation( user, group, permitted_actions )
                assoc.flush()
        if history:
            for history in user.histories:
                self.history_set_default_access( history, permissions=permissions, dataset=dataset )
    def user_get_default_access( self, user ):
        return [ ( duga.group, duga.permitted_actions ) for duga in user.default_groups ]
    def history_set_default_access( self, history, permissions=None, dataset=False ):
        if permissions is None:
            if history.user:
                permissions = self.user_get_default_access( history.user )
            else:
                permissions = [ ( self.get_public_group(), self.permitted_actions.__dict__.values() ) ]
        if permissions is not None:
            for assoc in history.default_groups: #this is the association not the actual group
                assoc.delete()
                assoc.flush()
            for group, permitted_actions in permissions:
                log.debug("In history_set_default_access, history: %s, group: %s, permitted_actions: %s" % (history.id, group.name, str( permitted_actions)))
                assoc = self.model.DefaultHistoryGroupAssociation( history, group, permitted_actions )
                assoc.flush()
        if dataset:
            for data in history.datasets:
                for hda in data.dataset.history_associations:
                    if history.user and hda.history not in history.user.histories:
                        # When would this occur?
                        self.set_dataset_permissions( data.dataset, [ ( self.get_public_group(), [ self.permitted_actions.DATASET_ACCESS ] ) ] )
                        break
                else:
                    if self.allow_action( history.user, self.permitted_actions.DATASET_MANAGE_PERMISSIONS, dataset=data.dataset ):
                        self.set_dataset_permissions( data.dataset, permissions )
    def history_get_default_access( self, history ):
        return [ ( dhga.group, dhga.permitted_actions ) for dhga in history.default_groups ]
    def get_public_group( self ):
        return self.model.Group.get_public_group()
    def set_public_group( self, group ):
        return self.model.Group.set_public_group( group )
    def guess_public_group( self ):
        return self.model.Group.guess_public_group()
    def set_dataset_permissions( self, dataset, permissions ):
        """
        Apply permissions (a list of (group, permitted_action) tuples)
        to a dataset, removing any existing permissions.  permissions can
        also be a list of GroupDatasetAssociations (for simplicity).
        """
        if isinstance( dataset, self.model.HistoryDatasetAssociation ):
            dataset = dataset.dataset
        for group_dataset_assoc in dataset.groups:
            group_dataset_assoc.delete()
            group_dataset_assoc.flush()
        if isinstance( permissions[0], self.model.GroupDatasetAssociation ):
            permissions = [ ( gda.group, gda.permitted_actions ) for gda in permissions ]
        for ptuple in permissions:
            log.debug("In set_dataset_permissions, before elf.associate_components, dataset: %s, group: %s, permitted_actions: %s" % ( str(dataset.id), str(ptuple[0].id), str(ptuple[1])))
            self.associate_components( dataset=dataset, permissions=ptuple )
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
