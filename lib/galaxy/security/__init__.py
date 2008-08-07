"""
Utility functions used systemwide.

"""
import logging
from galaxy.util.bunch import Bunch

log = logging.getLogger(__name__)

class RBACAgent:
    """Class that handles galaxy security"""
    
    actions = Bunch( 
        dataset_actions = Bunch( VIEW = 'dataset_view', #viewing/downloading
                        USE = 'dataset_use', #use in jobs
                        ADD_ROLE = 'dataset_add_role', #dataset can be added to roles
                        REMOVE_ROLE = 'dataset_remove_role', #dataset can be removed from roles
                        ADD_GROUP = 'dataset_add_group', #dataset can be added to groups
                        REMOVE_GROUP = 'dataset_remove_group' ), #dataset can be removed from groups
        role_actions = Bunch( ADD_DATASET = 'role_add_dataset', #add role to dataset
                        REMOVE_DATASET = 'role_remove_dataset', #remove role from dataset
                        DELETE = 'role_delete', #delete a role
                        MODIFY = 'role_modify', #change a role's actions,
                        ADD_GROUP = 'role_add_group', #add role to a group
                        REMOVE_GROUP = 'role_remove_group' ), #remove role from a group
        group_actions = Bunch( ADD_DATASET = 'group_add_dataset', #add group to dataset
                        REMOVE_DATASET = 'group_remove_dataset', #remove dataset from group
                        DELETE = 'group_delete', #delete a group
                        ADD_ROLE = 'group_add_role', #add role to group
                        REMOVE_ROLE = 'group_remove_role', #remove role from group
                        ADD_USER = 'group_add_user' ) #add users to group
    )
    
    def allow_action( self, user, action, **kwd ):
        raise 'No valid method of checking action (%s) on %s for user %s.' % ( action, kwd, user )
    def guess_derived_groups_roles_for_datasets( self, datasets = [] ):
        raise "Unimplemented Method"
    def associate_components( self, **kwd ):
        raise 'No valid method of associating provided components: %s' % kwd
    def get_component( self, component_type, id ):
        raise 'No valid method of retrieving requested component %s with %s' % ( component_type, id )
    def get_component_by( self, component_type, **kwd ):
        raise 'No valid method of retrieving requested component %s with %s' % ( component_type, kwd )
    def create_component( self, component_type, **kwd ):
        raise 'No valid method of creating requested components %s with %s' % ( component_type, kwd )
    def create_private_user_group( self, user ):
        raise "Unimplemented Method"
    def user_set_default_access( self, user, groups = None, roles = None, history = False, dataset = False ):
        raise "Unimplemented Method"
    def setup_new_user( self, user ):
        self.user_set_default_access( user, history = True, dataset = True )
        self.associate_components( user = user, group = self.get_public_group() )
    def history_set_default_access( self, history, groups = None, roles = None, dataset = False ):
        raise "Unimplemented Method"
    def set_public_group( self, group ):
        raise "Unimplemented Method"
    def get_public_group( self ):
        raise "Unimplemented Method"
    def guess_public_group( self ):
        raise "Unimplemented Method"
    def set_dataset_groups( self, dataset, groups ):
        raise "Unimplemented Method"
    def set_dataset_roles( self, dataset, roles ):
        raise "Unimplemented Method"
    def get_component_associations( self, **kwd ):
        raise "Unimplemented Method"
    def components_are_associated( self, **kwd ):
        return bool( self.get_component_associations( **kwd ) )

class GalaxyRBACAgent( RBACAgent ):

    def __init__( self, model, actions = None ):
        self.model = model
        if actions:
            actions = actions

    def allow_action( self, user, action, **kwd ):
        if 'dataset' in kwd:
            return self.allow_dataset_action( user, action, kwd['dataset'] )
        raise 'No valid method of checking action (%s) on %s for user %s.' % ( action, kwd, user )
    def allow_dataset_action( self, user, action, dataset ):
        """Returns true when user has permission to perform an action"""
        
        while not isinstance( dataset, self.model.Dataset ):
            dataset = dataset.dataset
        #if dataset is in public group, we always return true for viewing and using
        #this may need to change when the ability to alter groups and roles is allowed
        if action in [ self.actions.dataset_actions.USE, self.actions.dataset_actions.VIEW ] and self.components_are_associated( group = self.get_public_group(), dataset = dataset ):
            return True
        elif user is not None:
            #loop through permissions and if allowed return true:
            #check roles associated directly with dataset first
            for role_dataset_assoc in dataset.roles:
                if self.components_are_associated( user = user, role = role_dataset_assoc.role ):
                    for permission in role_dataset_assoc.role.permissions:
                        if action in permission.permission.actions:
                            return True
            #check roles associated with dataset through groups
            for group_dataset_assoc in dataset.groups:
                if self.components_are_associated( user = user, group = group_dataset_assoc.group ):
                    for group_role_assoc in group_dataset_assoc.group.roles:
                        for permission in group_role_assoc.role.permissions:
                            if action in permission.permission.actions:
                                return True
        return False #no user and dataset not in public group, or user lacks permission
    def guess_derived_groups_roles_for_datasets( self, datasets = [] ):
        """Returns a list of output roles and groups based upon itself and provided datasets"""
        access_roles = None
        priority_access_role = None
        access_groups = None
        priority_access_group = None
        for dataset in datasets:
            #determine access roles and groups for output datasets
            #roles and groups for output dataset is the intersection across all inputs
            #if we end up with no intersection between inputs, then we rely on priorities
            if isinstance( dataset, self.model.HistoryDatasetAssociation ):
                dataset = dataset.dataset
            roles = [ data_role_assoc.role for data_role_assoc in dataset.roles ]
            for role in roles:
                if priority_access_role is None or priority_access_role.priority < role.priority:
                    priority_access_role = role
            groups = [ data_group_assoc.group for data_group_assoc in dataset.groups ]
            for group in groups:
                if priority_access_group is None or priority_access_group.priority < group.priority:
                    priority_access_group = group
            if access_roles is None:
                access_roles = set( roles )
                access_groups = set( groups )
            else:
                access_roles.intersection_update( set( roles ) )
                access_groups.intersection_update( set( groups ) )
        
        #complete lists for output dataset access
        if access_roles:
            access_roles = list( access_roles )
        else:
            access_roles = []
        if access_groups:
            access_groups = list( access_groups)
        else:
            access_groups = []
        #if we have no roles or groups left after intersection,
        #take the highest priority group or role
        if not access_roles and not access_groups:
            if priority_access_role and priority_access_group:
                if priority_access_group.priority == priority_access_role.priority:
                    access_groups = [ priority_access_group ]
                    access_roles = [ priority_access_role ]
                elif priority_access_group.priority > priority_access_role.priority:
                    access_groups = [ priority_access_group ]
                else:
                   access_roles = [ priority_access_role ]
            elif priority_access_role:
                 access_roles = [ priority_access_role ]
            elif priority_access_group:
                access_groups = [ priority_access_group ]
        
        return access_groups, access_roles
    
    def get_component( self, component_type, id ):
        if component_type.lower() == 'group':
            return self.model.Group.get( id )
        elif component_type.lower() == 'role':
            return self.model.Role.get( id )
        elif component_type.lower() == 'permission':
            return self.model.Permission.get( id )
        raise 'No valid method of retrieving requested component %s with %s' % ( component_type, id )
    def get_component_by( self, component_type, **kwd ):
        if component_type.lower() == 'group':
            return self.model.Group.get_by( **kwd )
        elif component_type.lower() == 'role':
            return self.model.Role.get_by( **kwd )
        elif component_type.lower() == 'permission':
            return self.model.Permission.get_by( **kwd )
        raise 'No valid method of retrieving requested component %s with %s' % ( component_type, kwd )
    
    def create_component( self, component_type, **kwd ):
        if component_type.lower() == 'group':
            rval = self.model.Group( **kwd )
            rval.flush()
            return rval
        elif component_type.lower() == 'role':
            rval = self.model.Role( **kwd )
            rval.flush()
            return rval
        elif component_type.lower() == 'permission':
            rval = self.model.Permission( **kwd )
            rval.flush()
            return rval
        raise 'No valid method of creating requested components %s with %s' % ( component_type, kwd )

    
    def associate_components( self, **kwd ):
        assert len( kwd ) == 2, 'You must specify exactly 2 Galaxy security components to associate.'
        if 'dataset' in kwd:
            if 'group' in kwd:
                return self.associate_group_dataset( kwd['group'], kwd['dataset'] )
            elif 'role' in kwd:
                return self.associate_role_dataset( kwd['role'], kwd['dataset'] )
        elif 'user' in kwd:
            if 'group' in kwd:
                return self.associate_user_group( kwd['user'], kwd['group'] )
            elif 'role' in kwd:
                return self.associate_user_role( kwd['user'], kwd['role']  )
        elif 'role' in kwd:
            if 'group' in kwd:
                return self.associate_group_role( kwd['group'], kwd['role'] )
            elif 'control_role' in kwd:
                return self.associate_role_control_role( kwd['control_role'], kwd['role'] )
            elif 'target_role' in kwd:
                return self.associate_role_control_role( kwd['role'], kwd['target_role'] )
            elif 'permission' in kwd:
                return self.associate_role_permission( kwd['role'], kwd['permission'] )
        elif 'group' in kwd:
            if 'control_role' in kwd:
                return self.associate_group_control_role( kwd['group'], kwd['control_role']  )
        raise 'No valid method of associating provided components: %s' % kwd
    def associate_group_dataset( self, group, dataset ):
        assoc = self.model.GroupDatasetAssociation( group, dataset )
        assoc.flush()
        return assoc
    def associate_role_dataset( self, role, dataset ):
        assoc = self.model.RoleDatasetAssociation( role, dataset )
        assoc.flush()
        return assoc
    def associate_user_group( self, user, group ):
        assoc = self.model.UserGroupAssociation( user, group )
        assoc.flush()
        return assoc
    def associate_user_role( self, user, role ):
        assoc = self.model.UserRoleAssociation( user, role )
        assoc.flush()
        return assoc
    def associate_group_role( self, group, role ):
        assoc = self.model.GroupRoleAssociation( group, role )
        assoc.flush()
        return assoc
    def associate_role_control_role( self, control_role, role ):
        assoc = self.model.RoleControlRoleAssociation( control_role, role )
        assoc.flush()
        return assoc
    def associate_group_control_role( self, group, role ):
        assoc = self.model.GroupControlRoleAssociation( group, role )
        assoc.flush()
        return assoc
    def associate_role_permission( self, role, permission ):
        assoc = self.model.RolePermissionAssociation( role, permission )
        assoc.flush()
        return assoc
        
    def create_private_user_group( self, user ):
        #create roles for user modification of role
        user_permission = self.model.Permission( "%s role modification" % user.email, list( self.model.Role.access_actions.__dict__.values() ) )
        user_permission.flush()
        user_role = self.model.Role( "%s role modification" % user.email )
        user_role.flush()
        self.associate_components( role = user_role, permission = user_permission )
        self.associate_components( user = user, role = user_role )
        self.associate_components( control_role = user_role, role = user_role )
        
        
        #create private group
        group = self.model.Group( user.email, priority = 10 )
        group.flush()
        #create dataset permissions
        dataset_permission = self.model.Permission( "%s dataset access" % user.email, list( self.model.Dataset.access_actions.__dict__.values() ) )
        dataset_permission.flush()
        #create private dataset access role
        role = self.model.Role( "%s dataset access" % user.email, priority = 10 )
        self.associate_components( role = role, permission = dataset_permission )
        role.flush()
        #add control role to role
        self.associate_components( control_role = user_role, role = role )
        #add role to group
        self.associate_components( group = group, role = user_role )
        
        #create roles for user modification of group
        group_permission = self.model.Permission( "%s group modification" % user.email, list( self.model.Group.access_actions.__dict__.values() ) )
        group_permission.flush()
        group_role = self.model.Role( "%s group modification" % user.email )
        group_role.flush()
        #add control role to role
        self.associate_components( control_role = user_role, role = group_role )
        self.associate_components( permission = group_permission, role = group_role )
        #add role to group
        self.associate_components( control_role = group_role, group = group )
        #associate role and user
        self.associate_components( role = group_role, user = user )
        
        #add user to group
        self.associate_components( group = group, user = user )
        group.flush()
        return group
    
    
    
    def user_set_default_access( self, user, groups = None, roles = None, history = False, dataset = False ):
        if groups is None and roles is None:
            groups = [ self.get_public_group(), self.create_private_user_group( user ) ]
            roles = []
        if groups is not None:
            for assoc in user.default_groups: #this is the association not the actual group
                assoc.delete()
                assoc.flush()
            for group in groups:
                assoc = self.model.DefaultUserGroupAssociation( user, group )
                assoc.flush()
        if roles is not None:
            for assoc in user.default_roles: #this is the association not the actual group
                assoc.delete()
                assoc.flush()
            for role in roles:
                assoc = self.model.DefaultUserRoleAssociation( user, role )
                assoc.flush()
        if history:
            for history in user.histories:
                self.history_set_default_access( history, groups = groups, roles = roles, dataset = dataset )

    def history_set_default_access( self, history, groups = None, roles = None, dataset = False ):
        if groups is None and roles is None:
            if history.user:
                groups = history.user.default_groups
                roles = history.user.default_roles
            else:
                groups = [ self.get_public_group() ]
                roles = []
        if groups is not None:
            for assoc in history.default_groups: #this is the association not the actual group
                assoc.delete()
                assoc.flush()
            for group in groups:
                assoc = self.model.DefaultHistoryGroupAssociation( history, group )
                assoc.flush()
        if roles is not None:
            for assoc in history.default_roles: #this is the association not the actual group
                assoc.delete()
                assoc.flush()
            for role in roles:
                assoc = self.model.DefaultHistoryRoleAssociation( history, role )
                assoc.flush()
        if dataset:
            for data in history.datasets:
                for hda in data.dataset.history_associations:
                    if history.user and hda.history not in history.user.histories:
                        self.set_dataset_groups( data.dataset, [ self.get_public_group() ] )
                        self.set_dataset_roles( data.dataset, [] )
                        break
                else:
                    self.set_dataset_groups( data.dataset, groups )
                    self.set_dataset_roles( data.dataset, roles )
    
    def get_public_group( self ):
        return self.model.Group.get_public_group()
    def set_public_group( self, group ):
        return self.model.Group.set_public_group( group )
    def guess_public_group( self ):
        return self.model.Group.guess_public_group()
    
    def set_dataset_groups( self, dataset, groups ):
        if isinstance( dataset, self.model.HistoryDatasetAssociation):
            dataset = dataset.dataset
        for assoc in dataset.groups:
            assoc.delete()
            assoc.flush()
        for group in groups:
            if not isinstance( group, self.model.Group ):
                group = group.group
            self.associate_components( dataset = dataset, group = group )
    def set_dataset_roles( self, dataset, roles ):
        if isinstance( dataset, self.model.HistoryDatasetAssociation):
            dataset = dataset.dataset
        for assoc in dataset.roles:
            assoc.delete()
            assoc.flush()
        for role in roles:
            if not isinstance( role, self.model.Role ):
                role = role.role
            self.associate_components( dataset = dataset, role = role )
    
    
    def get_component_associations( self, **kwd ):
        assert len( kwd ) == 2, 'You must specify exactly 2 Galaxy security components to check for associations.'
        if 'dataset' in kwd:
            if 'group' in kwd:
                return self.model.GroupDatasetAssociation.get_by( group_id = kwd['group'].id, dataset_id = kwd['dataset'].id )
            elif 'role' in kwd:
                return self.model.RoleDatasetAssociation.get_by( role_id = kwd['role'].id, dataset_id = kwd['dataset'].id )
        elif 'user' in kwd:
            if 'group' in kwd:
                return self.model.UserGroupAssociation.get_by( group_id = kwd['group'].id, user_id = kwd['user'].id )
            elif 'role' in kwd:
                return self.model.UserRoleAssociation.get_by( user_id = kwd['user'].id, role_id = kwd['role'].id )
        elif 'role' in kwd:
            if 'group' in kwd:
                return self.model.GroupRoleAssociation.get_by( group_id = kwd['group'].id, role_id = kwd['role'].id )
            elif 'control_role' in kwd:
                return self.model.RoleControlRoleAssociation.get_by( target_role_id = kwd['role'].id, role_id = kwd['control_role'].id )
            elif 'target_role' in kwd:
                return self.model.RoleControlRoleAssociation.get_by( role_id = kwd['role'].id, target_role_id = kwd['target_role'].id )
        elif 'group' in kwd:
            if 'control_role' in kwd:
                return self.model.GroupControlRoleAssociation.get_by( group_id = kwd['group'].id, role_id = kwd['control_role'].id )
        raise 'No valid method of associating provided components: %s' % kwd






