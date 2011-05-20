"""
Galaxy Tool Shed Security
"""
import os, logging, ConfigParser
from datetime import datetime, timedelta
from galaxy.util.bunch import Bunch
from galaxy.util import listify
from galaxy.model.orm import *
from galaxy.webapps.community.controllers.common import get_versions

log = logging.getLogger(__name__)

class Action( object ):
    def __init__( self, action, description, model ):
        self.action = action
        self.description = description
        self.model = model

class RBACAgent:
    """Class that handles galaxy community space security"""
    permitted_actions = Bunch()
    def associate_components( self, **kwd ):
        raise 'No valid method of associating provided components: %s' % kwd
    def associate_user_role( self, user, role ):
        raise 'No valid method of associating a user with a role'
    def convert_permitted_action_strings( self, permitted_action_strings ):
        """
        When getting permitted actions from an untrusted source like a
        form, ensure that they match our actual permitted actions.
        """
        return filter( lambda x: x is not None, [ self.permitted_actions.get( action_string ) for action_string in permitted_action_strings ] )
    def create_private_user_role( self, user ):
        raise "Unimplemented Method"
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
    def get_private_user_role( self, user ):
        raise "Unimplemented Method"

class CommunityRBACAgent( RBACAgent ):
    def __init__( self, model, permitted_actions=None ):
        self.model = model
        if permitted_actions:
            self.permitted_actions = permitted_actions
    @property
    def sa_session( self ):
        """Returns a SQLAlchemy session"""
        return self.model.context
    def allow_action( self, roles, action, item ):
        """
        Method for checking a permission for the current user ( based on roles ) to perform a
        specific action on an item
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
    def associate_components( self, **kwd ):
        if 'user' in kwd:
            if 'group' in kwd:
                return self.associate_user_group( kwd['user'], kwd['group'] )
            elif 'role' in kwd:
                return self.associate_user_role( kwd['user'], kwd['role'] )
        elif 'role' in kwd:
            if 'group' in kwd:
                return self.associate_group_role( kwd['group'], kwd['role'] )
        elif 'tool' in kwd:
            return self.associate_tool_category( kwd['tool'], kwd['category'] )
        elif 'repository' in kwd:
            return self.associate_repository_category( kwd[ 'repository' ], kwd[ 'category' ] )
        raise 'No valid method of associating provided components: %s' % kwd
    def associate_group_role( self, group, role ):
        assoc = self.model.GroupRoleAssociation( group, role )
        self.sa_session.add( assoc )
        self.sa_session.flush()
        return assoc
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
    def associate_tool_category( self, tool, category ):
        assoc = self.model.ToolCategoryAssociation( tool, category )
        self.sa_session.add( assoc )
        self.sa_session.flush()
        return assoc
    def associate_repository_category( self, repository, category ):
        assoc = self.model.RepositoryCategoryAssociation( repository, category )
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
    def get_item_actions( self, action, item ):
        # item must be one of: Dataset, Library, LibraryFolder, LibraryDataset, LibraryDatasetDatasetAssociation
        return [ permission for permission in item.actions if permission.action == action.action ]
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
    def set_entity_category_associations( self, tools=[], categories=[], delete_existing_assocs=True ):
        for tool in tools:
            if delete_existing_assocs:
                for a in tool.categories:
                    self.sa_session.delete( a )
                    self.sa_session.flush()
            self.sa_session.refresh( tool )
            for category in categories:
                self.associate_components( tool=tool, category=category )
    def can_rate( self, user, user_is_admin, cntrller, item ):
        # The current user can rate and review the item if they are an admin or if
        # they did not upload the item and the item is approved or archived.
        if user and user_is_admin and cntrller == 'admin':
            return True
        if cntrller in [ 'tool' ] and ( item.is_approved or item.is_archived ) and user != item.user:
            return True
        return False
    def can_approve_or_reject( self, user, user_is_admin, cntrller, item ):
        # The current user can approve or reject the item if the user
        # is an admin, and the item's state is WAITING.
        return user and user_is_admin and cntrller=='admin' and item.is_waiting
    def can_delete( self, user, user_is_admin, cntrller, item ):
        # The current user can delete the item if they are an admin or if they uploaded the
        # item and in either case the item's state is not DELETED.
        if user and user_is_admin and cntrller == 'admin':
            can_delete = not item.is_deleted
        elif cntrller in [ 'tool' ]:
            can_delete = user==item.user and not item.is_deleted
        else:
            can_delete = False
        return can_delete
    def can_download( self, user, user_is_admin, cntrller, item ):
        # The current user can download the item if they are an admin or if the
        # item's state is not one of: NEW, WAITING.
        if user and user_is_admin and cntrller == 'admin':
            return True
        elif cntrller in [ 'tool' ]:
            can_download = not( item.is_new or item.is_waiting )
        else:
            can_download = False
        return can_download
    def can_edit( self, user, user_is_admin, cntrller, item ):
        # The current user can edit the item if they are an admin or if they uploaded the item
        # and the item's state is one of: NEW, REJECTED.
        if user and user_is_admin and cntrller == 'admin':
            return True
        if cntrller in [ 'tool' ]:
            return user and user==item.user and ( item.is_new or item.is_rejected )
        return False
    def can_purge( self, user, user_is_admin, cntrller ):
        # The current user can purge the item if they are an admin.
        return user and user_is_admin and cntrller == 'admin'
    def can_upload_new_version( self, user, item ):
        # The current user can upload a new version as long as the item's state is not NEW or WAITING.
        if not user:
            return False
        versions = get_versions( item )
        state_ok = True
        for version in versions:
            if version.is_new or version.is_waiting:
                state_ok = False
                break
        return state_ok
    def can_view( self, user, user_is_admin, cntrller, item ):
        # The current user can view the item if they are an admin or if they uploaded the item
        # or if the item's state is APPROVED.
        if user and user_is_admin and cntrller == 'admin':
            return True
        if cntrller in [ 'tool' ] and item.is_approved or item.is_archived or item.is_deleted:
            return True
        return user and user==item.user
    def can_push( self, user, repository ):
        # TODO: handle this via the mercurial api.
        if not user:
            return False
        # Read the repository's hgrc file
        hgrc_file = os.path.abspath( os.path.join( repository.repo_path, ".hg", "hgrc" ) )
        config = ConfigParser.ConfigParser()
        config.read( hgrc_file )
        for option in config.options( "web" ):
            if option == 'allow_push':
                allowed = config.get( "web", option )
                return user.username in allowed
        return False
    def get_all_action_permissions( self, user, user_is_admin, cntrller, item ):
        """Get all permitted actions on item for the current user"""
        can_edit = self.can_edit( cntrller, user, user_is_admin, item )
        can_view = self.can_view( cntrller, user, user_is_admin, item )
        can_upload_new_version = self.can_upload_new_version( user, item )
        visible_versions = self.get_visible_versions( user, user_is_admin, cntrller, item )
        can_approve_or_reject = self.can_approve_or_reject( user, user_is_admin, cntrller, item )
        can_delete = self.can_delete( user, user_is_admin, cntrller, item )
        return can_edit, can_view, can_upload_new_version, can_delete, visible_versions, can_approve_or_reject
    def get_visible_versions( self, user, user_is_admin, cntrller, item ):
        # All previous versions of item can be displayed if the current user is an admin
        # or they uploaded item.  Otherwise, only versions whose state is APPROVED or 
        # ARCHIVED will be displayed.
        if user and user_is_admin and cntrller == 'admin':
            visible_versions = get_versions( item )
        elif cntrller in [ 'tool' ]:
            visible_versions = []
            for version in get_versions( item ):
                if version.is_approved or version.is_archived or version.user == user:
                    visible_versions.append( version )
        else:
           visible_versions = []
        return visible_versions 

def get_permitted_actions( filter=None ):
    '''Utility method to return a subset of RBACAgent's permitted actions'''
    if filter is None:
        return RBACAgent.permitted_actions
    tmp_bunch = Bunch()
    [ tmp_bunch.__dict__.__setitem__(k, v) for k, v in RBACAgent.permitted_actions.items() if k.startswith( filter ) ]
    return tmp_bunch
