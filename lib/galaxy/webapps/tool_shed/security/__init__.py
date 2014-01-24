"""Tool Shed Security"""
import ConfigParser
import logging
import os
from datetime import datetime
from datetime import timedelta
from galaxy.util.bunch import Bunch
from galaxy.util import listify
from galaxy.model.orm import and_

log = logging.getLogger(__name__)


class Action( object ):

    def __init__( self, action, description, model ):
        self.action = action
        self.description = description
        self.model = model


class RBACAgent:
    """Handle Galaxy Tool Shed security"""
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

    def get_repository_reviewer_role( self ):
        return self.sa_session.query( self.model.Role ) \
                              .filter( and_( self.model.Role.table.c.name == 'Repository Reviewer',
                                             self.model.Role.table.c.type == self.model.Role.types.SYSTEM ) ) \
                              .first()

    def set_entity_group_associations( self, groups=None, users=None, roles=None, delete_existing_assocs=True ):
        if groups is None:
            groups = []
        if users is None:
            users = []
        if roles is None:
            roles = []
        for group in groups:
            if delete_existing_assocs:
                for a in group.roles + group.users:
                    self.sa_session.delete( a )
                    self.sa_session.flush()
            for role in roles:
                self.associate_components( group=group, role=role )
            for user in users:
                self.associate_components( group=group, user=user )

    def set_entity_role_associations( self, roles=None, users=None, groups=None, repositories=None, delete_existing_assocs=True ):
        if roles is None:
            roles = []
        if users is None:
            users = []
        if groups is None:
            groups = []
        if repositories is None:
            repositories = []
        for role in roles:
            if delete_existing_assocs:
                for a in role.users + role.groups:
                    self.sa_session.delete( a )
                    self.sa_session.flush()
            for user in users:
                self.associate_components( user=user, role=role )
            for group in groups:
                self.associate_components( group=group, role=role )

    def set_entity_user_associations( self, users=None, roles=None, groups=None, delete_existing_assocs=True ):
        if users is None:
            users = []
        if roles is None:
            roles = []
        if groups is None:
            groups = []
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

    def can_push( self, app, user, repository ):
        if user:
            return user.username in listify( repository.allow_push( app ) )
        return False

    def user_can_administer_repository( self, user, repository ):
        """Return True if the received user can administer the received repository."""
        if user:
            if repository:
                repository_admin_role = repository.admin_role
                for rra in repository.roles:
                    role = rra.role
                    if role.id == repository_admin_role.id:
                        # We have the repository's admin role, so see if the user is associated with it.
                        for ura in role.users:
                            role_member = ura.user
                            if role_member.id == user.id:
                                return True
                        # The user is not directly associated with the role, so see if they are a member
                        # of a group that is associated with the role.
                        for gra in role.groups:
                            group = gra.group
                            for uga in group.members:
                                member = uga.user
                                if member.id == user.id:
                                    return True
        return False

    def user_can_import_repository_archive( self, user, archive_owner ):
        # This method should be called only if the current user is not an admin.
        if user.username == archive_owner:
            return True
        # A member of the IUC is authorized to create new repositories that are owned by another user.
        iuc_group = self.sa_session.query( self.model.Group ) \
                                   .filter( and_( self.model.Group.table.c.name == 'Intergalactic Utilities Commission',
                                                  self.model.Group.table.c.deleted == False ) ) \
                                   .first()
        if iuc_group is not None:
            for uga in iuc_group.users:
               if uga.user.id == user.id:
                   return True
        return False

    def user_can_review_repositories( self, user ):
        if user:
            roles = user.all_roles()
            if roles:
                repository_reviewer_role = self.get_repository_reviewer_role()
                if repository_reviewer_role:
                    return repository_reviewer_role in roles
        return False

    def user_can_browse_component_review( self, app, repository, component_review, user ):
        if component_review and user:
            if self.can_push( app, user, repository ):
                # A user with write permission on the repository can access private/public component reviews.
                return True
            else:
                if self.user_can_review_repositories( user ):
                    # Reviewers can access private/public component reviews.
                    return True
        return False

def get_permitted_actions( filter=None ):
    '''Utility method to return a subset of RBACAgent's permitted actions'''
    if filter is None:
        return RBACAgent.permitted_actions
    tmp_bunch = Bunch()
    [ tmp_bunch.__dict__.__setitem__(k, v) for k, v in RBACAgent.permitted_actions.items() if k.startswith( filter ) ]
    return tmp_bunch
