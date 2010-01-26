"""
Galaxy Security

"""
import logging, socket, operator
from datetime import datetime, timedelta
from galaxy.util.bunch import Bunch
from galaxy.util import listify
from galaxy.model.orm import *

log = logging.getLogger(__name__)

class Action( object ):
    def __init__( self, action, description, model ):
        self.action = action
        self.description = description
        self.model = model

class RBACAgent:
    """Class that handles galaxy security"""
    IN_ACCESSIBLE = 'access_error'
    ILL_LEGITIMATE = 'legitimate_error'
    permitted_actions = Bunch(
        DATASET_MANAGE_PERMISSIONS = Action( "manage permissions", "Role members can manage the roles associated with permissions on this dataset", "grant" ),
        DATASET_ACCESS = Action( "access", "Role members can import this dataset into their history for analysis", "restrict" ),
        LIBRARY_ACCESS = Action( "access library", "Restrict access to this library to only role members", "restrict" ),
        LIBRARY_ADD = Action( "add library item", "Role members can add library items to this library item", "grant" ),
        LIBRARY_MODIFY = Action( "modify library item", "Role members can modify this library item", "grant" ),
        LIBRARY_MANAGE = Action( "manage library permissions", "Role members can manage roles associated with permissions on this library item", "grant" )
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
    def get_item_actions( self, action, item ):
        raise 'No valid method of retrieving action (%s) for item %s.' % ( action, item )
    def guess_derived_permissions_for_datasets( self, datasets = [] ):
        raise "Unimplemented Method"
    def can_access_dataset( self, roles, dataset ):
        raise "Unimplemented Method"
    def can_manage_dataset( self, roles, dataset ):
        raise "Unimplemented Method"
    def can_access_library( self, roles, library ):
        raise "Unimplemented Method"
    def can_add_library_item( self, roles, item ):
        raise "Unimplemented Method"
    def can_modify_library_item( self, roles, item ):
        raise "Unimplemented Method"
    def can_manage_library_item( self, roles, item ):
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
    def dataset_is_public( self, dataset ):
        raise "Unimplemented Method"
    def make_dataset_public( self, dataset ):
        raise "Unimplemented Method"
    def set_all_library_permissions( self, dataset, permissions ):
        raise "Unimplemented Method"
    def library_is_public( self, library ):
        raise "Unimplemented Method"
    def make_library_public( self, library ):
        raise "Unimplemented Method"
    def get_permissions( self, library_dataset ):
        raise "Unimplemented Method"
    def get_legitimate_roles( self, trans, item ):
        raise "Unimplemented Method"
    def check_library_dataset_access( self, trans, library_id, **kwd ):
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
            ( self.model.Library, self.model.LibraryPermissions ),
            ( self.model.LibraryFolder, self.model.LibraryFolderPermissions ),
            ( self.model.LibraryDataset, self.model.LibraryDatasetPermissions ),
            ( self.model.LibraryDatasetDatasetAssociation, self.model.LibraryDatasetDatasetAssociationPermissions ) )
    @property
    def sa_session( self ):
        """Returns a SQLAlchemy session"""
        return self.model.context
    def get_legitimate_roles( self, trans, item ):
        """
        Return a sorted list of legitimate roles that can be associated with a permission on
        item where item is a Library or a Dataset.  If item is public, all roles are legitimate.
        If item is restricted, legitimate roles are derived from the users and groups associated
        with each role that is associated with the access permission ( i.e., DATASET_MANAGE_PERMISSIONS
        or LIBRARY_MANAGE ) on item.
        """
        if ( isinstance( item, self.model.Library ) and self.library_is_public( item ) ) or \
            ( isinstance( item, self.model.Dataset ) and self.dataset_is_public( item ) ):
            return trans.sa_session.query( trans.app.model.Role ) \
                                   .filter( trans.app.model.Role.table.c.deleted==False ) \
                                   .order_by( trans.app.model.Role.table.c.name )
        def sort_by_attr( seq, attr ):
            """
            Sort the sequence of objects by object's attribute
            Arguments:
            seq  - the list or any sequence (including immutable one) of objects to sort.
            attr - the name of attribute to sort by
            """
            # Use the "Schwartzian transform"
            # Create the auxiliary list of tuples where every i-th tuple has form
            # (seq[i].attr, i, seq[i]) and sort it. The second item of tuple is needed not
            # only to provide stable sorting, but mainly to eliminate comparison of objects
            # (which can be expensive or prohibited) in case of equal attribute values.
            intermed = map( None, map( getattr, seq, ( attr, ) * len( seq ) ), xrange( len( seq ) ), seq )
            intermed.sort()
            return map( operator.getitem, intermed, ( -1, ) * len( intermed ) )            
        roles = set()
        # If a library has roles associated with the LIBRARY_ACCESS permission, we need to start with them.
        access_roles = item.get_access_roles( trans )
        for role in access_roles:
            roles.add( role )
            # Each role potentially has users.  We need to find all roles that each of those users have.
            for ura in role.users:
                roles.add( ura.role )
            # Each role also potentially has groups which, in turn, have members ( users ).  We need to 
            # find all roles that each group's members have.
            for gra in role.groups:
                group = gra.group
                for uga in group.users:
                    user = uga.user
                    for ura in user.roles:
                        roles.add( ura.role )
        return sort_by_attr( [ role for role in roles ], 'name' )
    def allow_action( self, roles, action, item ):
        """
        Method for checking a permission for the current user ( based on roles ) to perform a
        specific action on an item, which must be one of:
        Dataset, Library, LibraryFolder, LibraryDataset, LibraryDatasetDatasetAssociation
        """
        item_actions = self.get_item_actions( action, item )
        if not item_actions:
            return action.model == 'restrict'
        ret_val = False
        for item_action in item_actions:
            if item_action.role in roles:
                ret_val = True
                break
        return ret_val
    def can_access_dataset( self, roles, dataset ):
        return self.allow_action( roles, self.permitted_actions.DATASET_ACCESS, dataset )
    def can_manage_dataset( self, roles, dataset ):
        return self.allow_action( roles, self.permitted_actions.DATASET_MANAGE_PERMISSIONS, dataset )
    def can_access_library( self, roles, library ):
        return self.library_is_public( library ) or self.allow_action( roles, self.permitted_actions.LIBRARY_ACCESS, library )
    def can_add_library_item( self, roles, item ):
        return self.allow_action( roles, self.permitted_actions.LIBRARY_ADD, item )
    def can_modify_library_item( self, roles, item ):
        return self.allow_action( roles, self.permitted_actions.LIBRARY_MODIFY, item )
    def can_manage_library_item( self, roles, item ):
        return self.allow_action( roles, self.permitted_actions.LIBRARY_MANAGE, item )
    def get_item_actions( self, action, item ):
        # item must be one of: Dataset, Library, LibraryFolder, LibraryDataset, LibraryDatasetDatasetAssociation
        return [ permission for permission in item.actions if permission.action == action.action ]
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
            these_perms = self.get_permissions( dataset )
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
        self.sa_session.add( assoc )
        self.sa_session.flush()
        return assoc
    def associate_user_role( self, user, role ):
        assoc = self.model.UserRoleAssociation( user, role )
        self.sa_session.add( assoc )
        self.sa_session.flush()
        return assoc
    def associate_group_role( self, group, role ):
        assoc = self.model.GroupRoleAssociation( group, role )
        self.sa_session.add( assoc )
        self.sa_session.flush()
        return assoc
    def associate_action_dataset_role( self, action, dataset, role ):
        assoc = self.model.DatasetPermissions( action, dataset, role )
        self.sa_session.add( assoc )
        self.sa_session.flush()
        return assoc
    def create_private_user_role( self, user ):
        # Create private role
        role = self.model.Role( name=user.email, description='Private Role for ' + user.email, type=self.model.Role.types.PRIVATE )
        self.sa_session.add( role )
        self.sa_session.flush()
        # Add user to role
        self.associate_components( role=role, user=user )
        return role
    def get_private_user_role( self, user, auto_create=False ):
        role = self.sa_session.query( self.model.Role ) \
                              .filter( and_( self.model.Role.table.c.name == user.email, 
                                             self.model.Role.table.c.type == self.model.Role.types.PRIVATE ) ) \
                              .first()
        if not role:
            if auto_create:
                return self.create_private_user_role( user )
            else:
                return None
        return role
    def user_set_default_permissions( self, user, permissions={}, history=False, dataset=False, bypass_manage_permission=False, default_access_private = False ):
        # bypass_manage_permission is used to change permissions of datasets in a userless history when logging in
        if user is None:
            return None
        if not permissions:
            #default permissions
            permissions = { self.permitted_actions.DATASET_MANAGE_PERMISSIONS : [ self.get_private_user_role( user, auto_create=True ) ] }
            #new_user_dataset_access_role_default_private is set as True in config file
            if default_access_private:
                permissions[ self.permitted_actions.DATASET_ACCESS ] = permissions.values()[ 0 ]
        # Delete all of the current default permissions for the user
        for dup in user.default_permissions:
            self.sa_session.delete( dup )
        # Add the new default permissions for the user
        for action, roles in permissions.items():
            if isinstance( action, Action ):
                action = action.action
            for dup in [ self.model.DefaultUserPermissions( user, action, role ) for role in roles ]:
                self.sa_session.add( dup )
        self.sa_session.flush()
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
            self.sa_session.delete( dhp )
        # Add the new default permissions for the history
        for action, roles in permissions.items():
            if isinstance( action, Action ):
                action = action.action
            for dhp in [ self.model.DefaultHistoryPermissions( history, action, role ) for role in roles ]:
                self.sa_session.add( dhp )
        self.sa_session.flush()
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
                if bypass_manage_permission or self.can_manage_dataset( user.all_roles(), dataset ):
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
        """
        Set new permissions on a dataset, eliminating all current permissions
        permissions looks like: { Action : [ Role, Role ] }
        """
        # Delete all of the current permissions on the dataset
        for dp in dataset.actions:
            self.sa_session.delete( dp )
        # Add the new permissions on the dataset
        for action, roles in permissions.items():
            if isinstance( action, Action ):
                action = action.action
            for dp in [ self.model.DatasetPermissions( action, dataset, role ) for role in roles ]:
                self.sa_session.add( dp )
        self.sa_session.flush()
    def set_dataset_permission( self, dataset, permission={} ):
        """
        Set a specific permission on a dataset, leaving all other current permissions on the dataset alone
        permissions looks like: { Action : [ Role, Role ] }
        """
        for action, roles in permission.items():
            if isinstance( action, Action ):
                action = action.action
            # Delete the current specific permission on the dataset if one exists
            for dp in dataset.actions:
                if dp.action == action:
                    self.sa_session.delete( dp )
            # Add the new specific permission on the dataset
            for dp in [ self.model.DatasetPermissions( action, dataset, role ) for role in roles ]:
                self.sa_session.add( dp )
        self.sa_session.flush()
    def dataset_is_public( self, dataset ):
        # A dataset is considered public if there are no "access" actions associated with it.  Any
        # other actions ( 'manage permissions', 'edit metadata' ) are irrelevant.
        return self.permitted_actions.DATASET_ACCESS.action not in [ a.action for a in dataset.actions ]
    def make_dataset_public( self, dataset ):
        # A dataset is considered public if there are no "access" actions associated with it.  Any
        # other actions ( 'manage permissions', 'edit metadata' ) are irrelevant.
        for dp in dataset.actions:
            if dp.action == self.permitted_actions.DATASET_ACCESS.action:
                self.sa_session.delete( dp )
        self.sa_session.flush()
    def get_permissions( self, item ):
        """
        Return a dictionary containing the actions and associated roles on item
        where item is one of Library, LibraryFolder, LibraryDatasetDatasetAssociation,
        LibraryDataset, Dataset.  The dictionary looks like: { Action : [ Role, Role ] }.
        """
        permissions = {}
        for item_permission in item.actions:
            action = self.get_action( item_permission.action )
            if action in permissions:
                permissions[ action ].append( item_permission.role )
            else:
                permissions[ action ] = [ item_permission.role ]
        return permissions
    def copy_dataset_permissions( self, src, dst ):
        if not isinstance( src, self.model.Dataset ):
            src = src.dataset
        if not isinstance( dst, self.model.Dataset ):
            dst = dst.dataset
        self.set_all_dataset_permissions( dst, self.get_permissions( src ) )
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
            self.sa_session.add( sharing_role )
            self.sa_session.flush()
            for user in users:
                self.associate_components( user=user, role=sharing_role )
        self.set_dataset_permission( dataset, { self.permitted_actions.DATASET_ACCESS : [ sharing_role ] } )
    def set_all_library_permissions( self, library_item, permissions={} ):
        # Set new permissions on library_item, eliminating all current permissions
        for role_assoc in library_item.actions:
            self.sa_session.delete( role_assoc )
        # Add the new permissions on library_item
        for item_class, permission_class in self.library_item_assocs:
            if isinstance( library_item, item_class ):
                for action, roles in permissions.items():
                    if isinstance( action, Action ):
                        action = action.action
                    for role_assoc in [ permission_class( action, library_item, role ) for role in roles ]:
                        self.sa_session.add( role_assoc )
                    if isinstance( library_item, self.model.LibraryDatasetDatasetAssociation ) and \
                        action == self.permitted_actions.LIBRARY_MANAGE.action:
                        # Handle the special case when we are setting the LIBRARY_MANAGE_PERMISSION on a
                        # library_dataset_dataset_association since the roles need to be applied to the
                        # DATASET_MANAGE_PERMISSIONS permission on the associated dataset
                        permissions = {}
                        permissions[ self.permitted_actions.DATASET_MANAGE_PERMISSIONS ] = roles
                        self.set_dataset_permission( library_item.dataset, permissions )
        self.sa_session.flush()
    def library_is_public( self, library ):
        # A library is considered public if there are no "access" actions associated with it.
        return self.permitted_actions.LIBRARY_ACCESS.action not in [ a.action for a in library.actions ]
    def make_library_public( self, library ):
        # A library is considered public if there are no "access" actions associated with it.
        for lp in library.actions:
            if lp.action == self.permitted_actions.LIBRARY_ACCESS.action:
                self.sa_session.delete( lp )
        self.sa_session.flush()
    def check_library_dataset_access( self, trans, library_id, **kwd ):
        # library_id must be decoded before being sent
        msg = ''
        permissions = {}
        # accessible will be True only if at least 1 user has every role in DATASET_ACCESS_in
        accessible = False 
        # legitimate will be True only if all roles in DATASET_ACCESS_in are in the set
        # of roles returned from self.get_legitimate_roles()
        legitimate = False
        error = None
        for k, v in get_permitted_actions( filter='DATASET' ).items():
            in_roles = [ self.sa_session.query( self.model.Role ).get( x ) for x in listify( kwd.get( k + '_in', [] ) ) ]
            if v == self.permitted_actions.DATASET_ACCESS and in_roles:
                library = self.model.Library.get( library_id )
                if not self.library_is_public( library ):
                    # Ensure that roles being associated with DATASET_ACCESS are a subset of the legitimate roles
                    # derived from the roles associated with the LIBRARY_ACCESS permission on the library if it's
                    # not public.  This will keep ill-legitimate roles from being associated with the DATASET_ACCESS
                    # permission on the dataset (i.e., if Role1 is associated with LIBRARY_ACCESS, then only those users
                    # that have Role1 should be associated with DATASET_ACCESS.
                    legitimate_roles = self.get_legitimate_roles( trans, library )
                    ill_legitimate_roles = []
                    for role in in_roles:
                        if role not in legitimate_roles:
                            ill_legitimate_roles.append( role )
                    if ill_legitimate_roles:
                        error = self.ILL_LEGITIMATE
                        msg += "The following roles are not associated with users that have the 'access library' permission on this "
                        msg += "library, so they cannot be associated with the 'access' permission on the datasets: "
                        for role in ill_legitimate_roles:
                            msg += "%s, " % role.name
                        msg = msg.rstrip( ", " )
                        new_in_roles = []
                        for role in in_roles:
                            if role in legitimate_roles:
                                new_in_roles.append( role )
                        in_roles = new_in_roles
                    else:
                        legitimate = True
                if len( in_roles ) == 1:
                    accessible = True
                else:
                    # At least 1 user must have every role associated with the access 
                    # permission on this dataset, or the dataset is not accessible.
                    in_roles_set = set()
                    for role in in_roles:
                        in_roles_set.add( role )
                    users_set = set()
                    for role in in_roles:
                        for ura in role.users:
                            users_set.add( ura.user )
                        for gra in role.groups:
                            group = gra.group
                            for uga in group.users:
                                users_set.add( uga.user )
                    # Make sure that at least 1 user has every role being associated with the dataset
                    for user in users_set:
                        user_roles_set = set()
                        for ura in user.roles:
                            user_roles_set.add( ura.role )
                        if in_roles_set.issubset( user_roles_set ):
                            accessible = True
                            break
                if not accessible:
                    error = self.IN_ACCESSIBLE
                    # Don't set the permissions for DATASET_ACCESS if inaccessible, but set all other permissions
                    permissions[ self.get_action( v.action ) ] = []
                    msg += "At least 1 user must have every role associated with accessing datasets.  The roles you "
                    msg += "attempted to associate for access would make the datasets in-accessible by everyone, "
                    msg += "so access permissions were left in their original state (or not set).  All other "
                    msg += "permissions were updated for the datasets."
                else:
                    permissions[ self.get_action( v.action ) ] = in_roles
            else:
                permissions[ self.get_action( v.action ) ] = in_roles
        return permissions, in_roles, error, msg
    def copy_library_permissions( self, source_library_item, target_library_item, user=None ):
        # Copy all relevant permissions from source.
        permissions = {}
        for role_assoc in source_library_item.actions:
            if role_assoc.action != self.permitted_actions.LIBRARY_ACCESS.action:
                # LIBRARY_ACCESS is a special permission that is set only at the library level.
                if role_assoc.action in permissions:
                    permissions[role_assoc.action].append( role_assoc.role )
                else:
                    permissions[role_assoc.action] = [ role_assoc.role ]
        self.set_all_library_permissions( target_library_item, permissions )
        if user:
            item_class = None
            for item_class, permission_class in self.library_item_assocs:
                if isinstance( target_library_item, item_class ):
                    break
            if item_class:
                # Make sure user's private role is included
                private_role = self.model.security_agent.get_private_user_role( user )
                for name, action in self.permitted_actions.items():
                    if not permission_class.filter_by( role_id = private_role.id, action = action.action ).first():
                        lp = permission_class( action.action, target_library_item, private_role )
                        self.sa_session.add( lp )
                        self.sa_session.flush()
            else:
                raise 'Invalid class (%s) specified for target_library_item (%s)' % \
                    ( target_library_item.__class__, target_library_item.__class__.__name__ )
    def show_library_item( self, user, roles, library_item, actions_to_check, hidden_folder_ids='' ):
        """
        This method must be sent an instance of Library() or LibraryFolder().  Recursive execution produces a
        comma-separated string of folder ids whose folders do NOT meet the criteria for showing. Along with
        the string, True is returned if the current user has permission to perform any 1 of actions_to_check
        on library_item. Otherwise, cycle through all sub-folders in library_item until one is found that meets
        this criteria, if it exists.  This method does not necessarily scan the entire library as it returns
        when it finds the first library_item that allows user to perform any one action in actions_to_check.
        """
        for action in actions_to_check:
            if self.allow_action( roles, action, library_item ):
                return True, hidden_folder_ids
        if isinstance( library_item, self.model.Library ):
            return self.show_library_item( user, roles, library_item.root_folder, actions_to_check, hidden_folder_ids='' )
        if isinstance( library_item, self.model.LibraryFolder ):
            for folder in library_item.active_folders:
                can_show, hidden_folder_ids = self.show_library_item( user, roles, folder, actions_to_check, hidden_folder_ids=hidden_folder_ids )
                if can_show:
                    return True, hidden_folder_ids
                if hidden_folder_ids:
                    hidden_folder_ids = '%s,%d' % ( hidden_folder_ids, folder.id )
                else:
                    hidden_folder_ids = '%d' % folder.id
        return False, hidden_folder_ids
    def get_showable_folders( self, user, roles, library_item, actions_to_check, hidden_folder_ids=[], showable_folders=[] ):
        """
        This method must be sent an instance of Library(), all the folders of which are scanned to determine if
        user is allowed to perform any action in actions_to_check. The param hidden_folder_ids, if passed, should 
        contain a list of folder IDs which was generated when the library was previously scanned 
        using the same actions_to_check. A list of showable folders is generated. This method scans the entire library.
        """
        if isinstance( library_item, self.model.Library ):
            return self.get_showable_folders( user, roles, library_item.root_folder, actions_to_check, showable_folders=[] )
        if isinstance( library_item, self.model.LibraryFolder ):
            if library_item.id not in hidden_folder_ids:
                for action in actions_to_check:
                    if self.allow_action( roles, action, library_item ):
                        showable_folders.append( library_item )
                        break
            for folder in library_item.active_folders:
                self.get_showable_folders( user, roles, folder, actions_to_check, showable_folders=showable_folders )
        return showable_folders
    def set_entity_user_associations( self, users=[], roles=[], groups=[], delete_existing_assocs=True ):
        for user in users:
            if delete_existing_assocs:
                for a in user.non_private_roles + user.groups:
                    self.sa_session.delete( a )
                    self.sa_session.flush()
            self.sa_session.refresh( user )
            for role in roles:
                # Make sure we are not creating an additional association with a PRIVATE role
                if role not in user.roles:
                    self.associate_components( user=user, role=role )
            for group in groups:
                self.associate_components( user=user, group=group )
    def set_entity_group_associations( self, groups=[], users=[], roles=[], delete_existing_assocs=True ):
        for group in groups:
            if delete_existing_assocs:
                for a in group.roles + group.users:
                    self.sa_session.delete( a )
                    self.sa_session.flush()
            for role in roles:
                self.associate_components( group=group, role=role )
            for user in users:
                self.associate_components( group=group, user=user )
    def set_entity_role_associations( self, roles=[], users=[], groups=[], delete_existing_assocs=True ):
        for role in roles:
            if delete_existing_assocs:
                for a in role.users + role.groups:
                    self.sa_session.delete( a )
                    self.sa_session.flush()
            for user in users:
                self.associate_components( user=user, role=role )
            for group in groups:
                self.associate_components( group=group, role=role )
    def get_component_associations( self, **kwd ):
        assert len( kwd ) == 2, 'You must specify exactly 2 Galaxy security components to check for associations.'
        if 'dataset' in kwd:
            if 'action' in kwd:
                return self.sa_session.query( self.model.DatasetPermissions ).filter_by( action = kwd['action'].action, dataset_id = kwd['dataset'].id ).first()
        elif 'user' in kwd:
            if 'group' in kwd:
                return self.sa_session.query( self.model.UserGroupAssociation ).filter_by( group_id = kwd['group'].id, user_id = kwd['user'].id ).first()
            elif 'role' in kwd:
                return self.sa_session.query( self.model.UserRoleAssociation ).filter_by( role_id = kwd['role'].id, user_id = kwd['user'].id ).first()
        elif 'group' in kwd:
            if 'role' in kwd:
                return self.sa_session.query( self.model.GroupRoleAssociation ).filter_by( role_id = kwd['role'].id, group_id = kwd['group'].id ).first()
        raise 'No valid method of associating provided components: %s' % kwd
    def check_folder_contents( self, user, roles, folder, hidden_folder_ids='' ):
        """
        This method must always be sent an instance of LibraryFolder().  Recursive execution produces a
        comma-separated string of folder ids whose folders do NOT meet the criteria for showing.  Along
        with the string, True is returned if the current user has permission to access folder. Otherwise,
        cycle through all sub-folders in folder until one is found that meets this criteria, if it exists.
        This method does not necessarily scan the entire library as it returns when it finds the first
        folder that is accessible to user.
        """
        action = self.permitted_actions.DATASET_ACCESS
        lddas = self.sa_session.query( self.model.LibraryDatasetDatasetAssociation ) \
                               .join( "library_dataset" ) \
                               .filter( self.model.LibraryDataset.folder == folder ) \
                               .join( "dataset" ) \
                               .options( eagerload_all( "dataset.actions" ) ) \
                               .all()
        for ldda in lddas:
            ldda_access_permissions = self.get_item_actions( action, ldda.dataset )
            if not ldda_access_permissions:
                # Dataset is public
                return True, hidden_folder_ids
            for ldda_access_permission in ldda_access_permissions:
                if ldda_access_permission.role in roles:
                    # The current user has access permission on the dataset
                    return True, hidden_folder_ids
        for sub_folder in folder.active_folders:
            can_access, hidden_folder_ids = self.check_folder_contents( user, roles, sub_folder, hidden_folder_ids=hidden_folder_ids )
            if can_access:
                return True, hidden_folder_ids
            if hidden_folder_ids:
                hidden_folder_ids = '%s,%d' % ( hidden_folder_ids, sub_folder.id )
            else:
                hidden_folder_ids = '%d' % sub_folder.id
        return False, hidden_folder_ids

class HostAgent( RBACAgent ):
    """
    A simple security agent which allows access to datasets based on host.
    This exists so that externals sites such as UCSC can gain access to
    datasets which have permissions which would normally prevent such access.
    """
    # TODO: Make sites user configurable
    sites = Bunch(
        ucsc_main = ( 'hgw1.cse.ucsc.edu', 'hgw2.cse.ucsc.edu', 'hgw3.cse.ucsc.edu', 'hgw4.cse.ucsc.edu',
                      'hgw5.cse.ucsc.edu', 'hgw6.cse.ucsc.edu', 'hgw7.cse.ucsc.edu', 'hgw8.cse.ucsc.edu' ),
        ucsc_test = ( 'hgwdev.cse.ucsc.edu', ),
        ucsc_archaea = ( 'lowepub.cse.ucsc.edu', )
    )
    def __init__( self, model, permitted_actions=None ):
        self.model = model
        if permitted_actions:
            self.permitted_actions = permitted_actions
    @property
    def sa_session( self ):
        """Returns a SQLAlchemy session"""
        return self.model.context
    def allow_action( self, addr, action, **kwd ):
        if 'dataset' in kwd and action == self.permitted_actions.DATASET_ACCESS:
            hda = kwd['dataset']
            if action == self.permitted_actions.DATASET_ACCESS and action.action not in [ dp.action for dp in hda.dataset.actions ]:
                log.debug( 'Allowing access to public dataset with hda: %i.' % hda.id )
                return True # dataset has no roles associated with the access permission, thus is already public
            hdadaa = self.sa_session.query( self.model.HistoryDatasetAssociationDisplayAtAuthorization ) \
                                    .filter_by( history_dataset_association_id = hda.id ).first()
            if not hdadaa:
                log.debug( 'Denying access to private dataset with hda: %i.  No hdadaa record for this dataset.' % hda.id )
                return False # no auth
            # We could just look up the reverse of addr, but then we'd also
            # have to verify it with the forward address and special case any
            # IPs (instead of hosts) in the server list.
            #
            # This would be improved by caching, but that's what the OS's name
            # service cache daemon is for (you ARE running nscd, right?).
            for server in HostAgent.sites.get( hdadaa.site, [] ):
                # We're going to search in order, but if the remote site is load
                # balancing their connections (as UCSC does), this is okay.
                try:
                    if socket.gethostbyname( server ) == addr:
                        break # remote host is in the server list
                except ( socket.error, socket.gaierror ):
                    pass # can't resolve, try next
            else:
                log.debug( 'Denying access to private dataset with hda: %i.  Remote addr is not a valid server for site: %s.' % ( hda.id, hdadaa.site ) )
                return False # remote addr is not in the server list
            if ( datetime.utcnow() - hdadaa.update_time ) > timedelta( seconds=60 ):
                log.debug( 'Denying access to private dataset with hda: %i.  Authorization was granted, but has expired.' % hda.id )
                return False # not authz'd in the last 60 seconds
            log.debug( 'Allowing access to private dataset with hda: %i.  Remote server is: %s.' % ( hda.id, server ) )
            return True
        else:
            raise 'The dataset access permission is the only valid permission in the host security agent.'
    def set_dataset_permissions( self, hda, user, site ):
        hdadaa = self.sa_session.query( self.model.HistoryDatasetAssociationDisplayAtAuthorization ) \
                                .filter_by( history_dataset_association_id = hda.id ).first()
        if hdadaa:
            hdadaa.update_time = datetime.utcnow()
        else:
            hdadaa = self.model.HistoryDatasetAssociationDisplayAtAuthorization( hda=hda, user=user, site=site )
        self.sa_session.add( hdadaa )
        self.sa_session.flush()

def get_permitted_actions( filter=None ):
    '''Utility method to return a subset of RBACAgent's permitted actions'''
    if filter is None:
        return RBACAgent.permitted_actions
    tmp_bunch = Bunch()
    [ tmp_bunch.__dict__.__setitem__(k, v) for k, v in RBACAgent.permitted_actions.items() if k.startswith( filter ) ]
    return tmp_bunch
