"""
Galaxy Security

"""
import logging
from galaxy.util.bunch import Bunch
from galaxy.model.orm import *

log = logging.getLogger(__name__)

class Action( object ):
    def __init__( self, action, description, model ):
        self.action = action
        self.description = description
        self.model = model

class RBACAgent:
    """Class that handles galaxy security"""
    permitted_actions = Bunch(
        DATASET_MANAGE_PERMISSIONS = Action( "manage permissions", "Role members can manage the roles associated with this dataset", "grant" ),
        DATASET_ACCESS = Action( "access", "Role members can import this dataset into their history for analysis", "restrict" ),
        LIBRARY_ADD = Action( "add library item", "Role members can add library items to this folder", "grant" ),
        LIBRARY_MODIFY = Action( "modify library item", "Role members can modify this library item", "grant" ),
        LIBRARY_MANAGE = Action( "manage library permissions", "Role members can manage roles associated with this library item", "grant" )
    )
    def get_action( self, name, default=None ):
        """Get a permitted action by its dict key or action name"""
        for k, v in self.permitted_actions.items():
            if k == name or v.action == name:
                return v
        return default
    def get_actions( self ):
        """Get all permitted actions as a list of Action objects"""
        return self.permitted_actions.__dict__.values()
    def allow_action( self, user, action, **kwd ):
        raise 'No valid method of checking action (%s) on %s for user %s.' % ( action, kwd, user )
    def guess_derived_permissions_for_datasets( self, datasets = [] ):
        raise "Unimplemented Method"
    def associate_components( self, **kwd ):
        raise 'No valid method of associating provided components: %s' % kwd
    def create_private_user_role( self, user ):
        raise "Unimplemented Method"
    def get_private_user_role( self, user ):
        raise "Unimplemented Method"
    def user_set_default_permissions( self, user, permissions={}, history=False, dataset=False ):
        raise "Unimplemented Method"
    def history_set_default_permissions( self, history, permissions=None, dataset=False, bypass_manage_permission=False ):
        raise "Unimplemented Method"
    def set_all_dataset_permissions( self, dataset, permissions ):
        raise "Unimplemented Method"
    def set_dataset_permission( self, dataset, permission ):
        raise "Unimplemented Method"
    def make_dataset_public( self, dataset ):
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

class GalaxyRBACAgent( RBACAgent ):
    def __init__( self, model, permitted_actions=None ):
        self.model = model
        if permitted_actions:
            self.permitted_actions = permitted_actions
        # List of "library_item" objects and their associated permissions and info template objects
        self.library_item_assocs = ( 
            ( self.model.Library, self.model.LibraryPermissions, self.model.LibraryInfoAssociation ),
            ( self.model.LibraryFolder, self.model.LibraryFolderPermissions, self.model.LibraryFolderInfoAssociation ),
            ( self.model.LibraryDataset, self.model.LibraryDatasetPermissions, self.model.LibraryDatasetInfoAssociation ),
            ( self.model.LibraryDatasetDatasetAssociation, self.model.LibraryDatasetDatasetAssociationPermissions, self.model.LibraryDatasetDatasetInfoAssociation ),
            ( self.model.LibraryItemInfo, self.model.LibraryItemInfoPermissions, None ),
            ( self.model.LibraryItemInfoTemplate, self.model.LibraryItemInfoTemplatePermissions, None ) )
    def allow_action( self, user, action, **kwd ):
        if 'dataset' in kwd:
            return self.allow_dataset_action( user, action, kwd[ 'dataset' ] )
        elif 'library_item' in kwd:
            return self.allow_library_item_action( user, action, kwd[ 'library_item' ] )
        raise 'No valid method of checking action (%s) for user %s using kwd %s' % ( action, str( user ), str( kwd ) )
    def allow_dataset_action( self, user, action, dataset ):
        """Returns true when user has permission to perform an action"""
        if not isinstance( dataset, self.model.Dataset ):
            dataset = dataset.dataset
        if not user:
            if action == self.permitted_actions.DATASET_ACCESS and action.action not in [ dp.action for dp in dataset.actions ]:
                return True # anons only get access, and only if there are no roles required for the access action
            # other actions (or if the dataset has roles defined for the access action) fall through to the false below
        elif action.action not in [ dp.action for dp in dataset.actions ]:
            if action.model == 'restrict':
                return True # implicit access to restrict-style actions if the dataset does not have the action
            # grant-style actions fall through to the false below
        else:
            user_role_ids = sorted( [ r.id for r in user.all_roles() ] )
            perms = self.get_dataset_permissions( dataset )
            if action in perms.keys():
                # The filter() returns a list of the dataset's role ids of which the user is not a member,
                # so an empty list means the user has all of the required roles.
                if not filter( lambda x: x not in user_role_ids, [ r.id for r in perms[ action ] ] ):
                    return True # user has all of the roles required to perform the action
                # Fall through to the false because the user is missing at least one required role
        return False # default is to reject
    def allow_library_item_action( self, user, action, library_item ):
        if user is None:
            # All permissions are granted, so non-users cannot have permissions
            return False
        if action.model == 'grant':
            user_role_ids = [ r.id for r in user.all_roles() ]
            # Check to see if user has access to any of the roles
            allowed_role_assocs = []
            for item_class, permission_class, info_association_class in self.library_item_assocs:
                if isinstance( library_item, item_class ):
                    if permission_class == self.model.LibraryPermissions:
                        allowed_role_assocs = permission_class.filter_by( action=action.action, library_id=library_item.id ).all()
                    elif permission_class == self.model.LibraryFolderPermissions:
                        allowed_role_assocs = permission_class.filter_by( action=action.action, library_folder_id=library_item.id ).all()
                    elif permission_class == self.model.LibraryDatasetPermissions:
                        allowed_role_assocs = permission_class.filter_by( action=action.action, library_dataset_id=library_item.id ).all()
                    elif permission_class == self.model.LibraryDatasetDatasetAssociationPermissions:
                        allowed_role_assocs = permission_class.filter_by( action=action.action, library_dataset_dataset_association_id=library_item.id ).all()
                    elif permission_class == self.model.LibraryItemInfoPermissions:
                        allowed_role_assocs = permission_class.filter_by( action=action.action, library_item_info_id=library_item.id ).all()
                    elif permission_class == self.model.LibraryItemInfoTemplatePermissions:
                        allowed_role_assocs = permission_class.filter_by( action=action.action, library_item_info_template_id=library_item.id ).all()
            for allowed_role_assoc in allowed_role_assocs:
                if allowed_role_assoc.role_id in user_role_ids:
                    return True
            return False
        else:
            raise 'Unimplemented model (%s) specified for action (%s)' % ( action.model, action.action )
    def guess_derived_permissions_for_datasets( self, datasets=[] ):
        """Returns a dict of { action : [ role, role, ... ] } for the output dataset based upon provided datasets"""
        perms = {}
        for dataset in datasets:
            if not isinstance( dataset, self.model.Dataset ):
                dataset = dataset.dataset
            these_perms = {}
            # initialize blank perms
            for action in self.get_actions():
                these_perms[ action ] = []
            # collect this dataset's perms
            these_perms = self.get_dataset_permissions( dataset )
            # join or intersect this dataset's permissions with others
            for action, roles in these_perms.items():
                if action not in perms.keys():
                    perms[ action ] = roles
                else:
                    if action.model == 'grant':
                        # intersect existing roles with new roles
                        perms[ action ] = filter( lambda x: x in perms[ action ], roles )
                    elif action.model == 'restrict':
                        # join existing roles with new roles
                        perms[ action ].extend( filter( lambda x: x not in perms[ action ], roles ) )
        return perms
    def associate_components( self, **kwd ):
        if 'user' in kwd:
            if 'group' in kwd:
                return self.associate_user_group( kwd['user'], kwd['group'] )
            elif 'role' in kwd:
                return self.associate_user_role( kwd['user'], kwd['role'] )
        elif 'role' in kwd:
            if 'group' in kwd:
                return self.associate_group_role( kwd['group'], kwd['role'] )
        if 'action' in kwd:
            if 'dataset' in kwd and 'role' in kwd:
                return self.associate_action_dataset_role( kwd['action'], kwd['dataset'], kwd['role'] )
        raise 'No valid method of associating provided components: %s' % kwd
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
    def associate_action_dataset_role( self, action, dataset, role ):
        assoc = self.model.DatasetPermissions( action, dataset, role )
        assoc.flush()
        return assoc
    def create_private_user_role( self, user ):
        # Create private role
        role = self.model.Role( name=user.email, description='Private Role for ' + user.email, type=self.model.Role.types.PRIVATE )
        role.flush()
        # Add user to role
        self.associate_components( role=role, user=user )
        return role
    def get_private_user_role( self, user, auto_create=False ):
        role = self.model.Role.filter( and_( self.model.Role.table.c.name == user.email, 
                                             self.model.Role.table.c.type == self.model.Role.types.PRIVATE ) ).first()
        if not role:
            if auto_create:
                return self.create_private_user_role( user )
            else:
                return None
        return role
    def user_set_default_permissions( self, user, permissions={}, history=False, dataset=False, bypass_manage_permission=False ):
        # bypass_manage_permission is used to change permissions of datasets in a userless history when logging in
        if user is None:
            return None
        if not permissions:
            permissions = { self.permitted_actions.DATASET_MANAGE_PERMISSIONS : [ self.get_private_user_role( user, auto_create=True ) ] }
        # Delete all of the current default permissions for the user
        for dup in user.default_permissions:
            dup.delete()
            dup.flush()
        # Add the new default permissions for the user
        for action, roles in permissions.items():
            if isinstance( action, Action ):
                action = action.action
            for dup in [ self.model.DefaultUserPermissions( user, action, role ) for role in roles ]:
                dup.flush()
        if history:
            for history in user.active_histories:
                self.history_set_default_permissions( history, permissions=permissions, dataset=dataset, bypass_manage_permission=bypass_manage_permission )
    def user_get_default_permissions( self, user ):
        permissions = {}
        for dup in user.default_permissions:
            action = self.get_action( dup.action )
            if action in permissions:
                permissions[ action ].append( dup.role )
            else:
                permissions[ action ] = [ dup.role ]
        return permissions
    def history_set_default_permissions( self, history, permissions={}, dataset=False, bypass_manage_permission=False ):
        # bypass_manage_permission is used to change permissions of datasets in a user-less history when logging in
        user = history.user
        if not user:
            # default permissions on a user-less history are None
            return None
        if not permissions:
            permissions = self.user_get_default_permissions( user )
        # Delete all of the current default permission for the history
        for dhp in history.default_permissions:
            dhp.delete()
            dhp.flush()
        # Add the new default permissions for the history
        for action, roles in permissions.items():
            if isinstance( action, Action ):
                action = action.action
            for dhp in [ self.model.DefaultHistoryPermissions( history, action, role ) for role in roles ]:
                dhp.flush()
        if dataset:
            # Only deal with datasets that are not purged
            for hda in history.activatable_datasets:
                dataset = hda.dataset
                if dataset.library_associations:
                    # Don't change permissions on a dataset associated with a library
                    continue
                if [ assoc for assoc in dataset.history_associations if assoc.history not in user.histories ]:
                    # Don't change permissions on a dataset associated with a history not owned by the user
                    continue
                if bypass_manage_permission or self.allow_action( user, self.permitted_actions.DATASET_MANAGE_PERMISSIONS, dataset=dataset ):
                    self.set_all_dataset_permissions( dataset, permissions )
    def history_get_default_permissions( self, history ):
        permissions = {}
        for dhp in history.default_permissions:
            action = self.get_action( dhp.action )
            if action in permissions:
                permissions[ action ].append( dhp.role )
            else:
                permissions[ action ] = [ dhp.role ]
        return permissions
    def set_all_dataset_permissions( self, dataset, permissions={} ):
        # Set new permissions on a dataset, eliminating all current permissions        
        # Delete all of the current permissions on the dataset
        for dp in dataset.actions:
            dp.delete()
            dp.flush()
        # Add the new permissions on the dataset
        for action, roles in permissions.items():
            if isinstance( action, Action ):
                action = action.action
            for dp in [ self.model.DatasetPermissions( action, dataset, role ) for role in roles ]:
                dp.flush()
    def set_dataset_permission( self, dataset, permission={} ):
        # Set a specific permission on a dataset, leaving all other current permissions on the dataset alone
        for action, roles in permission.items():
            if isinstance( action, Action ):
                action = action.action
            # Delete the current specific permission on the dataset if one exists
            for dp in dataset.actions:
                if dp.action == action:
                    dp.delete()
                    dp.flush()
            # Add the new specific permission on the dataset
            for dp in [ self.model.DatasetPermissions( action, dataset, role ) for role in roles ]:
                dp.flush()
    def make_dataset_public( self, dataset ):
        # A dataset is considered public if there are no "access" actions associated with it.  Any
        # other actions ( 'manage permissions', 'edit metadata' ) are irrelevant.
        for dp in dataset.actions:
            if dp.action == self.permitted_actions.DATASET_ACCESS.action:
                dp.delete()
                dp.flush()
    def get_dataset_permissions( self, dataset ):
        if not isinstance( dataset, self.model.Dataset ):
            dataset = dataset.dataset
        permissions = {}
        for dp in dataset.actions:
            action = self.get_action( dp.action )
            if action in permissions:
                permissions[ action ].append( dp.role )
            else:
                permissions[ action ] = [ dp.role ]
        return permissions
    def copy_dataset_permissions( self, src, dst ):
        if not isinstance( src, self.model.Dataset ):
            src = src.dataset
        if not isinstance( dst, self.model.Dataset ):
            dst = dst.dataset
        self.set_all_dataset_permissions( dst, self.get_dataset_permissions( src ) )
    def privately_share_dataset( self, dataset, users = [] ):
        intersect = None
        for user in users:
            roles = [ ura.role for ura in user.roles if ura.role.type == self.model.Role.types.SHARING ]
            if intersect is None:
                intersect = roles
            else:
                new_intersect = []
                for role in roles:
                    if role in intersect:
                        new_intersect.append( role )
                intersect = new_intersect
        sharing_role = None
        if intersect:
            for role in intersect:
                if not filter( lambda x: x not in users, [ ura.user for ura in role.users ] ):
                    # only use a role if it contains ONLY the users we're sharing with
                    sharing_role = role
                    break
        if sharing_role is None:
            sharing_role = self.model.Role( name = "Sharing role for: " + ", ".join( [ u.email for u in users ] ),
                                            type = self.model.Role.types.SHARING )
            sharing_role.flush()
            for user in users:
                self.associate_components( user=user, role=sharing_role )
        self.set_dataset_permission( dataset, { self.permitted_actions.DATASET_ACCESS : [ sharing_role ] } )
    def set_all_library_permissions( self, library_item, permissions={} ):
        # Set new permissions on library_item, eliminating all current permissions
        for role_assoc in library_item.actions:
            role_assoc.delete()
            role_assoc.flush()
        # Add the new permissions on library_item
        for item_class, permission_class, info_association_class in self.library_item_assocs:
            if isinstance( library_item, item_class ):
                for action, roles in permissions.items():
                    if isinstance( action, Action ):
                        action = action.action
                    for role_assoc in [ permission_class( action, library_item, role ) for role in roles ]:
                        role_assoc.flush()
    def get_library_dataset_permissions( self, library_dataset ):
        # Permissions will always be the same for LibraryDatasets and associated
        # LibraryDatasetDatasetAssociations
        if isinstance( library_dataset, self.model.LibraryDatasetDatasetAssociation ):
            library_dataset = library_dataset.library_dataset
        permissions = {}
        for library_dataset_permission in library_dataset.actions:
            action = self.get_action( library_dataset_permission.action )
            if action in permissions:
                permissions[ action ].append( library_dataset_permission.role )
            else:
                permissions[ action ] = [ library_dataset_permission.role ]
        return permissions
    def copy_library_permissions( self, source_library_item, target_library_item, user=None ):
        # Copy all permissions from source
        permissions = {}
        for role_assoc in source_library_item.actions:
            if role_assoc.action in permissions:
                permissions[role_assoc.action].append( role_assoc.role )
            else:
                permissions[role_assoc.action] = [ role_assoc.role ]
        self.set_all_library_permissions( target_library_item, permissions )
        if user:
            # Make sure user's private role is included
            item_class = None
            for item_class, permission_class, info_association_class in self.library_item_assocs:
                if isinstance( target_library_item, item_class ):
                    break
            if item_class:
                private_role = self.model.security_agent.get_private_user_role( user )
                for name, action in self.permitted_actions.items():
                    if not permission_class.filter_by( role_id = private_role.id, action = action.action ).first():
                        lp = permission_class( action.action, target_library_item, private_role )
                        lp.flush()
            else:
                raise 'Invalid class (%s) specified for target_library_item (%s)' % ( target_library_item.__class__, target_library_item.__class__.__name__ )
    def show_library_item( self, user, library_item ):
        # TODO: possibly needs to support other library item types
        if self.allow_action( user, self.permitted_actions.LIBRARY_MODIFY, library_item=library_item ) or \
            self.allow_action( user, self.permitted_actions.LIBRARY_MANAGE, library_item=library_item ) or \
            self.allow_action( user, self.permitted_actions.LIBRARY_ADD, library_item=library_item ):
            return True
        if isinstance( library_item, self.model.Library ):
            return self.show_library_item( user, library_item.root_folder )
        elif isinstance( library_item, self.model.LibraryFolder ):
            for folder in library_item.folders:
                if self.show_library_item( user, folder ):
                    return True
        return False
    def set_entity_user_associations( self, users=[], roles=[], groups=[], delete_existing_assocs=True ):
        for user in users:
            if delete_existing_assocs:
                for a in user.non_private_roles + user.groups:
                    a.delete()
                    a.flush()
            for role in roles:
                self.associate_components( user=user, role=role )
            for group in groups:
                self.associate_components( user=user, group=group )
    def set_entity_group_associations( self, groups=[], users=[], roles=[], delete_existing_assocs=True ):
        for group in groups:
            if delete_existing_assocs:
                for a in group.roles + group.users:
                    a.delete()
                    a.flush()
            for role in roles:
                self.associate_components( group=group, role=role )
            for user in users:
                self.associate_components( group=group, user=user )
    def set_entity_role_associations( self, roles=[], users=[], groups=[], delete_existing_assocs=True ):
        for role in roles:
            if delete_existing_assocs:
                for a in role.users + role.groups:
                    a.delete()
                    a.flush()
            for user in users:
                self.associate_components( user=user, role=role )
            for group in groups:
                self.associate_components( group=group, role=role )
    def get_component_associations( self, **kwd ):
        assert len( kwd ) == 2, 'You must specify exactly 2 Galaxy security components to check for associations.'
        if 'dataset' in kwd:
            if 'action' in kwd:
                return self.model.DatasetPermissions.filter_by( action = kwd['action'].action, dataset_id = kwd['dataset'].id ).first()
        elif 'user' in kwd:
            if 'group' in kwd:
                return self.model.UserGroupAssociation.filter_by( group_id = kwd['group'].id, user_id = kwd['user'].id ).first()
            elif 'role' in kwd:
                return self.model.UserRoleAssociation.filter_by( role_id = kwd['role'].id, user_id = kwd['user'].id ).first()
        elif 'group' in kwd:
            if 'role' in kwd:
                return self.model.GroupRoleAssociation.filter_by( role_id = kwd['role'].id, group_id = kwd['group'].id ).first()
        raise 'No valid method of associating provided components: %s' % kwd
    def check_folder_contents( self, user, entry ):
        """
        Return true if there are any datasets under 'folder' that the
        user has access permission on.  We do this a lot and it's a
        pretty inefficient method, optimizations are welcomed.
        """
        if isinstance( entry, self.model.Library ):
            return self.check_folder_contents( user, entry.root_folder )
        elif isinstance( entry, self.model.LibraryFolder ):
            for library_dataset in entry.active_datasets:
                if self.allow_action( user, self.permitted_actions.DATASET_ACCESS, dataset=library_dataset.library_dataset_dataset_association.dataset ):
                    return True
            for folder in entry.active_folders:
                if self.check_folder_contents( user, folder ):
                    return True
            return False
        elif isinstance( entry, self.model.LibraryDatasetDatasetAssociation ):
            return self.allow_action( user, self.permitted_actions.DATASET_ACCESS, dataset=entry.dataset )
        else:
            raise 'Passed an illegal object to check_folder_contents: %s' % type( entry )

def get_permitted_actions( filter=None ):
    '''Utility method to return a subset of RBACAgent's permitted actions'''
    if filter is None:
        return RBACAgent.permitted_actions
    tmp_bunch = Bunch()
    [ tmp_bunch.__dict__.__setitem__(k, v) for k, v in RBACAgent.permitted_actions.items() if k.startswith( filter ) ]
    return tmp_bunch
