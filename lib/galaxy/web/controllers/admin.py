import shutil, StringIO, operator, urllib, gzip, tempfile
from galaxy import util, datatypes
from galaxy.web.base.controller import *
from galaxy.datatypes import sniff
from galaxy.security import RBACAgent
import galaxy.model
from galaxy.model.orm import *
from xml.sax.saxutils import escape, unescape
import pkg_resources
pkg_resources.require( "SQLAlchemy >= 0.4" )
import sqlalchemy as sa

import logging
log = logging.getLogger( __name__ )

entities = { '@': 'FuNkYaT' }
unentities = { 'FuNkYaT' : '@' }
no_privilege_msg = "You must have Galaxy administrator privileges to use this feature."

class Admin( BaseController ):
    def user_is_admin( self, trans ):
        admin_users = trans.app.config.get( "admin_users", "" ).split( "," )
        if not admin_users:
            return False
        user = trans.get_user()
        if not user:
            return False
        if not user.email in admin_users:
            return False
        return True
    @web.expose
    def index( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        return trans.fill_template( '/admin/index.mako', msg=msg )
    @web.expose
    def center( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        return trans.fill_template( '/admin/center.mako' )
    @web.expose
    def reload_tool( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        return trans.fill_template( '/admin/reload_tool.mako', toolbox=self.app.toolbox, msg=msg )
    @web.expose
    def tool_reload( self, trans, tool_version=None, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        tool_id = params.tool_id
        self.app.toolbox.reload( tool_id )
        msg = 'Reloaded tool: ' + tool_id
        return trans.fill_template( '/admin/reload_tool.mako', toolbox=self.app.toolbox, msg=msg )
    
    # Galaxy Role Stuff
    @web.expose
    def roles( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        return trans.fill_template( '/admin/dataset_security/roles.mako',
                                    roles=trans.app.model.Role.query().order_by( trans.app.model.Role.table.c.name ).all(),
                                    msg=msg )
    @web.expose
    def create_role( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        users=trans.app.model.User.query().order_by( trans.app.model.User.table.c.email ).all()
        groups = trans.app.model.Group.query() \
                .filter( galaxy.model.Group.table.c.deleted==False ) \
                .order_by( trans.app.model.Group.table.c.name ) \
                .all()
        return trans.fill_template( '/admin/dataset_security/role_create.mako', 
                                    users=users,
                                    groups=groups,
                                    msg=msg )
    @web.expose
    def new_role( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        name = params.name
        description = params.description
        if not name or not description:
            msg = "Please enter a name and a description"
            trans.response.send_redirect( '/admin/create_role?msg=%s' % msg )
        elif trans.app.model.Role.filter_by( name=name ).first():
            msg = "A role with that name already exists"
            trans.response.send_redirect( '/admin/create_role?msg=%s' % msg )
        else:
            # Create the role
            role = galaxy.model.Role( name=name,
                                      description=description,
                                      type=trans.app.model.Role.types.ADMIN )
            role.flush()
            # Add the users
            users = listify( params.users )
            for user_id in users:
                user = galaxy.model.User.get( user_id )
                # Create the UserRoleAssociation
                ura = galaxy.model.UserRoleAssociation( user, role )
                ura.flush()
            # Add the groups
            groups = listify( params.groups )
            for group_id in groups:
                group = galaxy.model.Group.get( group_id )
                # Create the GroupRoleAssociation
                gra = galaxy.model.GroupRoleAssociation( group, role )
                gra.flush()
            msg = "The new role has been created with %s associated users and %s associated groups" % ( str( len( users ) ), str( len( groups ) ) )
            trans.response.send_redirect( '/admin/roles?msg=%s' % msg )
    @web.expose
    def role( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        role = trans.app.model.Role.get( int( params.role_id ) )
        in_users = []
        out_users = []
        in_groups = []
        out_groups = []
        for user in trans.app.model.User.query().order_by( trans.app.model.User.table.c.email ).all():
            if user in [ x.user for x in role.users ]:
                in_users.append( ( user.id, user.email ) )
            else:
                out_users.append( ( user.id, user.email ) )
        for group in trans.app.model.Group.query().order_by( trans.app.model.Group.table.c.name ).all():
            if group in [ x.group for x in role.groups ]:
                in_groups.append( ( group.id, group.name ) )
            else:
                out_groups.append( ( group.id, group.name ) )
        # Build a list of tuples that are LibraryFolderDatasetAssociationss followed by a list of actions
        # whose ActionDatasetRoleAssociation is associated with the Role
        # [ ( LibraryFolderDatasetAssociation [ action, action ] ) ]
        library_dataset_actions = []
        for adra in role.actions:
            for lfda in trans.app.model.LibraryFolderDatasetAssociation.filter( dataset_id==dataset.id ).all():
                if adra.dataset in lfda.folder.active_datasets:
                    library_dataset_actions.append( ( lfda, adra.dataset.actions ) )
        return trans.fill_template( '/admin/dataset_security/role.mako',
                                    role=role,
                                    in_users=in_users,
                                    out_users=out_users,
                                    in_groups=in_groups,
                                    out_groups=out_groups,
                                    library_dataset_actions=library_dataset_actions,
                                    msg=msg )
    @web.expose
    def role_members_edit( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        role = galaxy.model.Role.get( int( params.role_id ) )
        in_users = [ trans.app.model.User.get( x ) for x in listify( params.in_users ) ]
        for ura in role.users:
            user = trans.app.model.User.get( ura.user_id )
            if user not in in_users:
                # Delete DefaultUserPermissions for previously associated users that have been removed from the role
                for dup in user.default_permissions:
                    if role == dup.role:
                        dup.delete()
                        dup.flush()
                # Delete DefaultHistoryPermissions for previously associated users that have been removed from the role
                for history in user.histories:
                    for dhp in history.default_permissions:
                        if role == dhp.role:
                            dhp.delete()
                            dhp.flush()
        in_groups = [ trans.app.model.Group.get( x ) for x in listify( params.in_groups ) ]
        trans.app.security_agent.set_entity_role_associations( roles=[ role ], users=in_users, groups=in_groups )
        role.refresh()
        msg = "The role has been updated with %s associated users and %s associated groups" % ( str( len( in_users ) ), str( len( in_groups ) ) )
        trans.response.send_redirect( '/admin/roles?msg=%s' % msg )

    @web.expose
    def update_group_members( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        group_id = int( params.group_id )
        members = listify( params.members )
        group = galaxy.model.Group.get( group_id )
        # This is tricky since we have default association tables with
        # records referring to members of this group.  Because of this,
        # we'll need to handle changes to the member list rather than the
        # simpler approach of deleting all existing members and creating 
        # new records for user_ids in the received members param.
        # First remove existing members that are not in the received members param
        for uga in group.members:
            if uga.user_id not in members:
                # Delete the UserGroupAssociation
                uga.delete()
                uga.flush()
        # Then add all new members to the group
        for user_id in members:
            user = galaxy.model.User.get( user_id )
            if user not in group.members:
                uga = galaxy.model.UserGroupAssociation( user, group )
                uga.flush()
        msg = "Group membership has been updated with a total of %s members" % len( members )
        trans.response.send_redirect( '/admin/groups?msg=%s' % msg )

    # Galaxy Group Stuff
    @web.expose
    def groups( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        # Build a list of tuples which are groups followed by lists of members and roles
        # [ ( group, [ member, member, member ], [ role, role ] ), ( group, [ member, member ], [ role ] ) ]
        groups_members_roles = []
        groups = galaxy.model.Group.query() \
            .filter( galaxy.model.Group.table.c.deleted==False ) \
            .order_by( galaxy.model.Group.table.c.name ) \
            .all()
        for group in groups:
            members = []
            for uga in group.members:
                members.append( galaxy.model.User.get( uga.user_id ) )
            roles = []
            for gra in group.roles:
                roles.append( galaxy.model.Role.get( gra.role_id ) )
            groups_members_roles.append( ( group, members, roles ) )
        return trans.fill_template( '/admin/dataset_security/groups.mako', 
                                    groups_members_roles=groups_members_roles, 
                                    msg=msg )
    @web.expose
    def create_group( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        users=trans.app.model.User.query().order_by( trans.app.model.User.table.c.email ).all()
        roles = trans.app.model.Role.query() \
                .filter( galaxy.model.Role.table.c.deleted==False ) \
                .order_by( trans.app.model.Role.table.c.name ) \
                .all()
        return trans.fill_template( '/admin/dataset_security/group_create.mako', 
                                    users=users,
                                    roles=roles,
                                    msg=msg )
    @web.expose
    def new_group( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        name = params.name
        if not name:
            msg = "Please enter a name"
            trans.response.send_redirect( '/admin/create_group?msg=%s' % msg )
        elif trans.app.model.Group.filter_by( name=name ).first():
            msg = "A group with that name already exists"
            trans.response.send_redirect( '/admin/create_group?msg=%s' % msg )
        else:
            # Create the group
            group = galaxy.model.Group( name )
            group.flush()
            # Add the members
            members = listify( params.members )
            for user_id in members:
                user = galaxy.model.User.get( user_id )
                # Create the UserGroupAssociation
                uga = galaxy.model.UserGroupAssociation( user, group )
                uga.flush()
            # Add the roles
            roles = params.roles
            if roles and not isinstance( roles, list ):
                roles = [ roles ]
            elif roles is None:
                roles = []
            for role_id in roles:
                role = galaxy.model.Role.get( role_id )
                # Create the GroupRoleAssociation
                gra = galaxy.model.GroupRoleAssociation( group, role )
                gra.flush()
            msg = "The new group has been created with %s members and %s associated roles" % ( str( len( members ) ), str( len( roles ) ) )
            trans.response.send_redirect( '/admin/groups?msg=%s' % msg )
    @web.expose
    def group_members_edit( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        group = galaxy.model.Group.get( int( params.group_id ) )
        members = []
        for uga in group.members:
            members.append ( galaxy.model.User.get( uga.user_id ) )
        return trans.fill_template( '/admin/dataset_security/group_members_edit.mako', 
                                    group=group,
                                    members=members,
                                    users=galaxy.model.User.query().order_by( galaxy.model.User.table.c.email ).all(),
                                    msg=msg )
    @web.expose
    def update_group_members( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        group_id = int( params.group_id )
        members = listify( params.members )
        group = galaxy.model.Group.get( group_id )
        # This is tricky since we have default association tables with
        # records referring to members of this group.  Because of this,
        # we'll need to handle changes to the member list rather than the
        # simpler approach of deleting all existing members and creating 
        # new records for user_ids in the received members param.
        # First remove existing members that are not in the received members param
        for uga in group.members:
            if uga.user_id not in members:
                # Delete the UserGroupAssociation
                uga.delete()
                uga.flush()
        # Then add all new members to the group
        for user_id in members:
            user = galaxy.model.User.get( user_id )
            if user not in group.members:
                uga = galaxy.model.UserGroupAssociation( user, group )
                uga.flush()
        msg = "Group membership has been updated with a total of %s members" % len( members )
        trans.response.send_redirect( '/admin/groups?msg=%s' % msg )
    # TODO: We probably don't want the following 2 methods since managing roles should be
    # restricted to the Role page due to private roles and rules governing them
    @web.expose
    def group_roles_edit( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        group = galaxy.model.Group.get( int( params.group_id ) )
        group_roles = []
        for gra in group.roles:
            group_roles.append ( galaxy.model.Role.get( gra.role_id ) )
        return trans.fill_template( '/admin/dataset_security/group_roles_edit.mako', 
                                    group=group,
                                    group_roles=group_roles,
                                    roles=galaxy.model.Role.query().order_by( galaxy.model.Role.table.c.name ).all(),
                                    msg=msg )
    @web.expose
    def update_group_roles( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        group_id = int( params.group_id )
        roles = listify( params.roles )
        group = galaxy.model.Group.get( group_id )
        # This is tricky since we have default association tables with
        # records referring to members of this group.  Because of this,
        # we'll need to handle changes to the member list rather than the
        # simpler approach of deleting all existing members and creating 
        # new records for user_ids in the received members param.
        # First remove existing members that are not in the received members param
        for gra in group.roles:
            if gra.role_id not in roles:
                # Delete the GroupRoleAssociation
                gra.delete()
                gra.flush()
        # Then add all new roles to the group
        for role_id in roles:
            role = galaxy.model.Role.get( role_id )
            if role not in group.roles:
                gra = galaxy.model.GroupRoleAssociation( group, role )
                gra.flush()
        msg = "Group updated with a total of %s associated roles" % len( roles )
        trans.response.send_redirect( '/admin/groups?msg=%s' % msg )
    @web.expose
    def mark_group_deleted( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        group = galaxy.model.Group.get( int( params.group_id ) )
        group.deleted = True
        group.flush()
        msg = "The group has been marked as deleted."
        trans.response.send_redirect( '/admin/groups?msg=%s' % msg )
    @web.expose
    def deleted_groups( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        # Build a list of tuples which are groups followed by lists of members and roles
        # [ ( group, [ member, member, member ], [ role, role ] ), ( group, [ member, member ], [ role ] ) ]
        groups_members_roles = []
        groups = galaxy.model.Group.query() \
            .filter( galaxy.model.Group.table.c.deleted==True ) \
            .order_by( galaxy.model.Group.table.c.name ) \
            .all()
        for group in groups:
            members = []
            for uga in group.members:
                members.append( galaxy.model.User.get( uga.user_id ) )
            roles = []
            for gra in group.roles:
                roles.append( galaxy.model.Role.get( gra.role_id ) )
            groups_members_roles.append( ( group, members, roles ) )
        return trans.fill_template( '/admin/dataset_security/deleted_groups.mako', 
                                    groups_members_roles=groups_members_roles, 
                                    msg=msg )
    @web.expose
    def undelete_group( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        group = galaxy.model.Group.get( int( params.group_id ) )
        group.deleted = False
        group.flush()
        msg = "The group has been marked as not deleted."
        trans.response.send_redirect( '/admin/groups?msg=%s' % msg )
    @web.expose
    def purge_group( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        group = galaxy.model.Group.get( int( params.group_id ) )
        # Remove UserGroupAssociations
        for uga in group.users:
            uga.delete()
            uga.flush()
        # Remove GroupRoleAssociations
        for gra in group.roles:
            gra.delete()
            gra.flush()
        # Delete the Group
        group.delete()
        group.flush()
        msg = "The group has been purged from the database."
        trans.response.send_redirect( '/admin/deleted_groups?msg=%s' % msg )

    # Galaxy User Stuff
    @web.expose
    def users( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        # Build a list of tuples which are users followed by lists of groups and roles
        # [ ( user, [ group, group, group ], [ role, role ] ), ( user, [ group, group ], [ role ] ) ]
        users_groups_roles = []
        users = trans.app.model.User.query().order_by( trans.app.model.User.table.c.email ).all()
        for user in users:
            groups = []
            for uga in user.groups:
                groups.append( galaxy.model.Group.get( uga.group_id ) )
            roles = []
            for ura in user.roles:
                roles.append( galaxy.model.Role.get( ura.role_id ) )
            users_groups_roles.append( ( user, groups, roles ) )
        return trans.fill_template( '/admin/dataset_security/users.mako',
                                    users_groups_roles=users_groups_roles,
                                    msg=msg )
    @web.expose
    def user( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        user_id = params.user_id
        msg = params.msg
        user = trans.app.model.User.get( user_id )
        # Get the groups and roles to which the user belongs
        groups = trans.app.model.Group.query() \
                    .select_from( ( outerjoin( trans.app.model.Group, trans.app.model.UserGroupAssociation ) ) \
                    .outerjoin( trans.app.model.User ) ) \
                    .filter( and_( trans.app.model.Group.deleted == False, trans.app.model.User.id == user_id ) ) \
                    .order_by( trans.app.model.Group.table.c.name ) \
                    .all()
        roles = user.all_roles()
        return trans.fill_template( '/admin/dataset_security/user.mako', 
                                    user=user, 
                                    groups=groups,
                                    roles=roles,
                                    msg=msg )
    @web.expose
    def user_groups_edit( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        user = galaxy.model.User.get( int( params.user_id ) )
        user_groups = []
        for uga in user.groups:
            user_groups.append ( galaxy.model.Group.get( uga.group_id ) )
        groups = galaxy.model.Group.query() \
            .filter( galaxy.model.Group.table.c.deleted==False ) \
            .order_by( galaxy.model.Group.table.c.name ) \
            .all()
        return trans.fill_template( '/admin/dataset_security/user_groups_edit.mako', 
                                    user=user,
                                    user_groups=user_groups,
                                    groups=groups,
                                    msg=msg )
    @web.expose
    def update_user_groups( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        user_id = int( params.user_id )
        groups = listify( params.groups )
        user = galaxy.model.User.get( user_id )
        # First remove existing UserGroupAssociations that are not in the received groups param
        for uga in user.groups:
            if uga.group_id not in groups:
                # Delete the UserGroupAssociation
                uga.delete()
                uga.flush()
        # Then add all new groups to the user
        for group_id in groups:
            group = galaxy.model.Group.get( group_id )
            if group not in user.groups:
                uga = galaxy.model.UserGroupAssociation( user, group )
                uga.flush()
        msg = "The user now belongs to a total of %s groups" % len( groups )
        trans.response.send_redirect( '/admin/users?msg=%s' % msg )

    # Galaxy Library Stuff
    @web.expose
    def library_browser( self, trans, **kwd ):
        ## TODO: "show deleted libraries" toggle?
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        if 'message' in kwd:
            message = kwd['message']
        else:
            message = None
        return trans.fill_template( '/admin/library/browser.mako', libraries=trans.app.model.Library.filter_by( deleted=False ).all(), message = message )
    libraries = library_browser
    @web.expose
    def library( self, trans, id=None, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        if not id and 'new' not in kwd:
            return trans.show_error_message( "Galaxy can't perform a library action if you don't specify a library" )
        if 'new' not in kwd:
            library = trans.app.model.Library.get( id )
        params = util.Params( kwd )
        if 'new' in kwd:
            if params.new == 'submitted':
                library = trans.app.model.Library( name = util.restore_text( params.name ), description = util.restore_text( params.description ) )
                root_folder = trans.app.model.LibraryFolder( name = util.restore_text( params.name ), description = "" )
                root_folder.flush()
                library.root_folder = root_folder
                library.flush()
                return trans.response.send_redirect( web.url_for( action='library_browser' ) )
            return trans.show_form( 
                web.FormBuilder( action = web.url_for(), title = "Create a new Library", name="library", submit_text = "Create" )
                    .add_text( name = "name", label = "Name", value = "New Library" )
                    .add_text( name = "description", label = "Description", value = "" )
                    .add_input( 'hidden', '', 'new', 'submitted', use_label = False  ) )
        elif 'rename' in kwd:
            if params.rename == 'submitted':
                if 'root_folder' in kwd:
                    root_folder = library.root_folder
                    root_folder.name = util.restore_text( params.name )
                    root_folder.flush()
                library.name = util.restore_text( params.name )
                library.description = util.restore_text( params.description )
                library.flush()
                return trans.response.send_redirect( web.url_for( action='library_browser' ) )
            return trans.show_form( 
                web.FormBuilder( action = web.url_for(), title = "Edit library name and description", name = "library", submit_text = "Save" )
                    .add_text( name = "name", label = "Name", value = library.name )
                    .add_text( name = "description", label = "Description", value = library.description )
                    .add_input( 'checkbox', 'Also change the root folder\'s name', 'root_folder' )
                    .add_input( 'hidden', '', 'rename', 'submitted', use_label = False  )
                    .add_input( 'hidden', '', 'id', id, use_label = False  ) )
        elif 'delete' in kwd:
            def delete_folder( folder ):
                for subfolder in folder.active_folders:
                    delete_folder( subfolder )
                for dataset in folder.active_datasets:
                    dataset.deleted = True
                    dataset.flush()
                folder.deleted = True
                folder.flush()
            delete_folder( library.root_folder )
            library.deleted = True
            library.flush()
            return trans.response.send_redirect( web.url_for( action='library_browser' ) )
        else:
            return trans.show_error_message( "Galaxy can't perform a library action if you don't specify an action" )
    @web.expose
    def folder( self, trans, id=None, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        if not id:
            return trans.show_error_message( "Galaxy can't perform a folder action if you don't specify a folder" )
        params = util.Params( kwd )
        folder = trans.app.model.LibraryFolder.get( id )
        if 'new' in kwd:
            if params.new == 'submitted':
                new_folder = trans.app.model.LibraryFolder( name = util.restore_text( params.name ), description = util.restore_text( params.description ) )
                # We are associating the last used genome_build with folders, so we will always
                # initialize a new folder with the first dbkey in util.dbnames which is currently
                # ?    unspecified (?)
                new_folder.genome_build = util.dbnames.default_value
                folder.add_folder( new_folder )
                new_folder.flush()
                return trans.response.send_redirect( web.url_for( action='library_browser' ) )
            return trans.show_form( 
                web.FormBuilder( action = web.url_for(), title = "Create a new folder", name="folder", submit_text = "Create" )
                    .add_text( name = "name", label = "Name", value = "New Folder" )
                    .add_text( name = "description", label = "Description", value = "" )
                    .add_input( 'hidden', '', 'new', 'submitted', use_label = False  )
                    .add_input( 'hidden', '', 'id', id, use_label = False  ) )
        elif 'rename' in kwd:
            if params.rename == 'submitted':
                folder.name = util.restore_text( params.name )
                folder.description = util.restore_text( params.description )
                folder.flush()
                return trans.response.send_redirect( web.url_for( action='library_browser' ) )
            return trans.show_form( 
                web.FormBuilder( action = web.url_for(), title = "Edit folder name and description", name = "folder", submit_text = "Save" )
                    .add_text( name = "name", label = "Name", value = folder.name )
                    .add_text( name = "description", label = "Description", value = folder.description )
                    .add_input( 'hidden', '', 'rename', 'submitted', use_label = False  )
                    .add_input( 'hidden', '', 'id', id, use_label = False  ) )
        elif 'delete' in kwd:
            def delete_folder( folder ):
                for subfolder in folder.active_folders:
                    delete_folder( subfolder )
                for dataset in folder.active_datasets:
                    dataset.deleted = True
                    dataset.flush()
                folder.deleted = True
                folder.flush()
            delete_folder( folder )
            return trans.response.send_redirect( web.url_for( action='library_browser' ) )
        else:
            return trans.show_error_message( "Galaxy can't perform a folder action if you don't specify an action" )
    @web.expose
    def dataset( self, trans, id=None, name="Unnamed", info='no info', extension=None, folder_id=None, dbkey=None, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        if isinstance( dbkey, list ):
            last_used_build = dbkey[0]
        else:
            last_used_build = dbkey
        if folder_id and not last_used_build:
            folder = trans.app.model.LibraryFolder.get( folder_id )
            last_used_build = folder.genome_build
        data_files = []
        params = util.Params( kwd )
        msg = params.msg

        # add_file method
        def add_file( file_obj, name, extension, dbkey, last_used_build, roles, info='no info', space_to_tab=False ):
            data_type = None
            temp_name = sniff.stream_to_file( file_obj )

            # See if we have a gzipped file, which, if it passes our restrictions, we'll uncompress on the fly.
            is_gzipped, is_valid = self.check_gzip( temp_name )
            if is_gzipped and not is_valid:
                raise BadFileException( "you attempted to upload an inappropriate file." )
            elif is_gzipped and is_valid:
                # We need to uncompress the temp_name file
                CHUNK_SIZE = 2**20 # 1Mb   
                fd, uncompressed = tempfile.mkstemp()   
                gzipped_file = gzip.GzipFile( temp_name )
                while 1:
                    try:
                        chunk = gzipped_file.read( CHUNK_SIZE )
                    except IOError:
                        os.close( fd )
                        os.remove( uncompressed )
                        raise BadFileException( 'problem decompressing gzipped data.' )
                    if not chunk:
                        break
                    os.write( fd, chunk )
                os.close( fd )
                gzipped_file.close()
                # Replace the gzipped file with the decompressed file
                shutil.move( uncompressed, temp_name )
                name = name.rstrip( '.gz' )
                data_type = 'gzip'

            if space_to_tab:
                line_count = sniff.convert_newlines_sep2tabs( temp_name )
            else:
                line_count = sniff.convert_newlines( temp_name )
            if extension == 'auto':
                data_type = sniff.guess_ext( temp_name, sniff_order=trans.app.datatypes_registry.sniff_order )    
            else:
                data_type = extension
            dataset = trans.app.model.LibraryFolderDatasetAssociation( name=name, 
                                                                       info=info, 
                                                                       extension=data_type, 
                                                                       dbkey=dbkey, 
                                                                       create_dataset=True )
            folder = trans.app.model.LibraryFolder.get( folder_id )
            folder.add_dataset( dataset, genome_build=last_used_build )
            dataset.flush()
            if roles:
                for role in roles:
                    adra = galaxy.model.ActionDatasetRoleAssociation( RBACAgent.permitted_actions.DATASET_ACCESS.action, dataset.dataset, role )
                    adra.flush()
            shutil.move( temp_name, dataset.dataset.file_name )
            dataset.dataset.state = dataset.dataset.states.OK
            dataset.init_meta()
            if line_count is not None:
                try:
                    dataset.set_peek( line_count=line_count )
                except:
                    dataset.set_peek()
            else:
                dataset.set_peek()
            dataset.set_size()
            if dataset.missing_meta():
                dataset.datatype.set_meta( dataset )
            trans.app.model.flush()
            return dataset
        # END add_file method

        # Dataset upload
        if 'create_dataset' in kwd:
            # Copied from upload tool action
            last_dataset_created = None
            data_file = kwd['file_data']
            url_paste = kwd['url_paste']
            server_dir = kwd.get( 'server_dir', 'None' )
            if data_file == '' and url_paste == '' and server_dir in [ 'None', '' ]:
                if trans.app.config.library_import_dir is not None:
                    msg = 'Select a file, enter a URL or Text, or select a server directory.'
                else:
                    msg = 'Select a file, enter a URL or enter Text.'
                trans.response.send_redirect( web.url_for( action='dataset', folder_id=folder_id, msg=msg ) )
            space_to_tab = False 
            if 'space_to_tab' in kwd:
                if kwd['space_to_tab'] not in ["None", None]:
                    space_to_tab = True
            roles = []
            if 'roles' in kwd:
                for role_id in listify( kwd['roles'] ):
                    roles.append( galaxy.model.Role.get( role_id ) )
            temp_name = ""
            data_list = []
            created_datasets = []
            if 'filename' in dir( data_file ):
                file_name = data_file.filename
                file_name = file_name.split( '\\' )[-1]
                file_name = file_name.split( '/' )[-1]
                last_dataset_created = add_file( data_file.file,
                                                 file_name,
                                                 extension,
                                                 dbkey,
                                                 last_used_build,
                                                 roles,
                                                 info="uploaded file",
                                                 space_to_tab=space_to_tab )
            elif url_paste not in [ None, "" ]:
                if url_paste.lower().find( 'http://' ) >= 0 or url_paste.lower().find( 'ftp://' ) >= 0:
                    url_paste = url_paste.replace( '\r', '' ).split( '\n' )
                    for line in url_paste:
                        line = line.rstrip( '\r\n' )
                        if line:
                            last_dataset_created = add_file( urllib.urlopen( line ),
                                                             line,
                                                             extension,
                                                             dbkey,
                                                             last_used_build,
                                                             roles,
                                                             info="uploaded url",
                                                             space_to_tab=space_to_tab )
                            created_datasets.append( last_dataset_created )
                else:
                    is_valid = False
                    for line in url_paste:
                        line = line.rstrip( '\r\n' )
                        if line:
                            is_valid = True
                            break
                    if is_valid:
                        last_dataset_created = add_file( StringIO.StringIO( url_paste ),
                                                         'Pasted Entry',
                                                         extension,
                                                         dbkey,
                                                         last_used_build,
                                                         roles,
                                                         info="pasted entry",
                                                         space_to_tab=space_to_tab )
            elif server_dir not in [ None, "", "None" ]:
                full_dir = os.path.join( trans.app.config.library_import_dir, server_dir )
                try:
                    files = os.listdir( full_dir )
                except:
                    log.debug( "Unable to get file list for %s" % full_dir )
                for file in files:
                    full_file = os.path.join( full_dir, file )
                    if not os.path.isfile( full_file ):
                        continue
                    last_dataset_created = add_file( open( full_file, 'rb' ),
                                                     file,
                                                     extension,
                                                     dbkey,
                                                     last_used_build,
                                                     roles,
                                                     info="imported file",
                                                     space_to_tab=space_to_tab )
                    created_datasets.append( last_dataset_created )
            if len( created_datasets ) > 1:
                trans.response.send_redirect( web.url_for(
                    action = 'library_browser',
                    message = "%i new datasets added to the library.  <a href='%s'>Click here</a> if you'd like to edit the permissions on these datasets." % (
                        len( created_datasets ),
                        web.url_for( action='dataset', id=",".join( [ str(d.id) for d in created_datasets ] ) )
                    )
                ) )
            elif last_dataset_created is not None:
                trans.response.send_redirect( web.url_for(
                    action = 'library_browser',
                    message = "New dataset added to the library.  <a href='%s'>Click here</a> if you'd like to edit the permissions or attributes on this dataset." %
                        web.url_for( action='dataset', id=last_dataset_created.id )
                ) )
            else:
                return trans.show_error_message( 'Upload failed' )

        # No dataset(s) specified, display upload form
        elif not id:
            # Send list of data formats to the form so the "extension" select list can be populated dynamically
            file_formats = trans.app.datatypes_registry.upload_file_formats
            # Send list of genome builds to the form so the "dbkey" select list can be populated dynamically
            def get_dbkey_options( last_used_build ):
                for dbkey, build_name in util.dbnames:
                    yield build_name, dbkey, ( dbkey==last_used_build )
            dbkeys = get_dbkey_options( last_used_build )
            # Send list of roles to the form so the dataset can be associated with 1 or more of them.
            roles = trans.app.model.Role.query().order_by( trans.app.model.Role.c.name ).all()
            return trans.fill_template( '/admin/library/new_dataset.mako', 
                                        folder_id=folder_id,
                                        file_formats=file_formats,
                                        dbkeys=dbkeys,
                                        last_used_build=last_used_build,
                                        roles=roles,
                                        msg=msg )
        else:
            if id.count( ',' ):
                ids = id.split(',')
                id = None
            else:
                ids = None
        # id specified, display attributes form
        if id:
            lda = trans.app.model.LibraryFolderDatasetAssociation.get( id )
            if not lda:
                return trans.show_error_message( "Invalid dataset specified" )

            # Copied from edit attributes for 'regular' datasets with some additions
            p = util.Params(kwd, safe=False)
            if p.update_roles:
                # The user clicked the Save button on the 'Associate With Roles' form
                permissions = {}
                for k, v in trans.app.model.Dataset.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( x ) for x in listify( p.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                trans.app.security_agent.set_dataset_permissions( lda.dataset, permissions )
                lda.dataset.refresh()
            elif p.change:
                # The user clicked the Save button on the 'Change data type' form
                trans.app.datatypes_registry.change_datatype( lda, p.datatype )
                trans.app.model.flush()
            elif p.save:
                # The user clicked the Save button on the 'Edit Attributes' form
                lda.name  = name
                lda.info  = info
                # The following for loop will save all metadata_spec items
                for name, spec in lda.datatype.metadata_spec.items():
                    if spec.get("readonly"):
                        continue
                    optional = p.get("is_"+name, None)
                    if optional and optional == 'true':
                        # optional element... == 'true' actually means it is NOT checked (and therefore ommitted)
                        setattr( lda.metadata, name, None )
                    else:
                        setattr( lda.metadata, name, spec.unwrap( p.get ( name, None ) ) )
    
                lda.metadata.dbkey = dbkey
                lda.datatype.after_edit( lda )
                trans.app.model.flush()
                return trans.show_ok_message( "Attributes updated" )
            elif p.detect:
                # The user clicked the Auto-detect button on the 'Edit Attributes' form
                for name, spec in lda.datatype.metadata_spec.items():
                    # We need to be careful about the attributes we are resetting
                    if name not in [ 'name', 'info', 'dbkey' ]:
                        if spec.get( 'default' ):
                            setattr( lda.metadata, name, spec.unwrap( spec.get( 'default' ) ) )
                lda.datatype.set_meta( lda )
                lda.datatype.after_edit( lda )
                trans.app.model.flush()
                return trans.show_ok_message( "Attributes updated" )
            elif p.delete:
                lda.deleted = True
                lda.flush()
                trans.response.send_redirect( web.url_for( action='library_browser' ) )
            lda.datatype.before_edit( lda )
            if "dbkey" in lda.datatype.metadata_spec and not lda.metadata.dbkey:
                # Copy dbkey into metadata, for backwards compatability
                # This looks like it does nothing, but getting the dbkey
                # returns the metadata dbkey unless it is None, in which
                # case it resorts to the old dbkey.  Setting the dbkey
                # sets it properly in the metadata
                lda.metadata.dbkey = lda.dbkey
            # let's not overwrite the imported datatypes module with the variable datatypes?
            ### the built-in 'id' is overwritten in lots of places as well
            ldatatypes = [x for x in trans.app.datatypes_registry.datatypes_by_extension.iterkeys()]
            ldatatypes.sort()
            return trans.fill_template( "/admin/library/dataset.mako", 
                                        dataset=lda, 
                                        datatypes=ldatatypes,
                                        err=None,
                                        msg=msg )
        # multiple ids specfied, display multi permission form
        elif ids:
            ldas = []
            for id in [ int( id ) for id in ids ]:
                lda = trans.app.model.LibraryFolderDatasetAssociation.get( id )
                if lda is None:
                    return trans.show_error_message( 'You specified an invalid dataset' )
                ldas.append( lda )
            if len( ldas ) < 2:
                return trans.show_error_message( 'You must specify at least two datasets to modify permissions on' )
            if 'update_roles' in kwd:
                p = util.Params( kwd )
                permissions = {}
                for k, v in trans.app.model.Dataset.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( x ) for x in listify( p.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                for lda in ldas:
                    trans.app.security_agent.set_dataset_permissions( lda.dataset, permissions )
                    lda.dataset.refresh()
	    # Ensure that the permissions across all datasets are
	    # identical.  Otherwise, we can't update together.
            tmp = []
            for lda in ldas:
                perms = trans.app.security_agent.get_dataset_permissions( lda.dataset )
                if perms not in tmp:
                    tmp.append( perms )
            if len( tmp ) != 1:
                return trans.show_error_message( "The datasets you selected do not have identical permissions, so they can not be updated together" )
            else:
                return trans.fill_template( "/admin/library/dataset.mako",
                                            dataset=ldas )
    @web.expose
    def add_dataset_to_folder_from_history( self, trans, ids="", folder_id=None, **kwd ):
        if not isinstance( ids, list ):
            if ids:
                ids = ids.split( "," )
            else:
                ids = []
        try:
            folder = trans.app.model.LibraryFolder.get( folder_id )
        except:
            folder = None
        if folder is None:
            return trans.show_error_message( "You must provide a valid target folder." )
        error_msg = ok_msg = ""
        dataset_names = []
        if ids:
            for data_id in ids:
                data = trans.app.model.HistoryDatasetAssociation.get( data_id )
                if data:
                    data.to_library_dataset_folder_association( target_folder = folder )
                    dataset_names.append( data.name )
                else:
                    error_msg += "A requested dataset (%s) was invalid.  " % ( data_id )
        if dataset_names:
            ok_msg = "Added datasets (%s) to the library folder." % ( ", ".join( dataset_names ) )
        return trans.fill_template( "/admin/library/add_dataset_from_history.mako", history=trans.get_history(), folder=folder, ok_msg=ok_msg, error_msg=error_msg )
        
    def check_gzip( self, temp_name ):
        """
        Utility method to check gzipped uploads
        """
        temp = open( temp_name, "U" )
        magic_check = temp.read( 2 )
        temp.close()
        if magic_check != datatypes.data.gzip_magic:
            return ( False, False )
        CHUNK_SIZE = 2**15 # 32Kb
        gzipped_file = gzip.GzipFile( temp_name )
        chunk = gzipped_file.read( CHUNK_SIZE )
        gzipped_file.close()
        #if self.check_html( temp_name, chunk=chunk ) or self.check_binary( temp_name, chunk=chunk ):
        #    return( True, False )
        return ( True, True )
    @web.expose
    def datasets( self, trans, **kwd ):
        """
        The datasets method is used by the dropdown box on the admin-side library browser.
        """
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        if 'with-selected' in kwd:
            if not params.dataset_ids:
                return trans.show_error_message( "At least one dataset must be selected." )
            dataset_ids = listify( params.dataset_ids )
            if params.action == 'edit':
                trans.response.send_redirect( web.url_for( action = 'dataset', id = ",".join( dataset_ids ) ) )
            elif params.action == 'delete':
                for id in dataset_ids:
                    d = trans.app.model.LibraryFolderDatasetAssociation.get( id )
                    d.deleted = True
                    d.flush()
                trans.response.send_redirect( web.url_for( action = 'library_browser' ) )
            else:
                return trans.show_error_message( "Not implemented." )
        else:
            return trans.show_error_message( "Galaxy can't operate on datasets without an operation." )
    @web.expose
    def delete_dataset( self, trans, id=None, **kwd):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        if id:
            # id is a LibraryFolderDatasetAssociation.id
            library_folder_dataset_assoc = trans.app.model.LibraryFolderDatasetAssociation.get( id )
            self._delete_dataset( library_folder_dataset_assoc )
            trans.log_event( "Dataset id %s deleted from library folder id %s" % ( str( id ), str( library_folder_dataset_assoc.folder.id ) ) )
            trans.response.send_redirect( web.url_for( action = 'folder', id = library_folder_dataset_assoc.folder.id, msg = 'The dataset was deleted from the folder' ) )
        return trans.show_error_message( "You did not specify a dataset to delete." )
    
    def _delete_dataset( self, library_folder_dataset_assoc ):
        #dataset = library_folder_dataset_assoc.dataset
        # TODO: assuming 1 to 1 mapping between Dataset -> LibraryFolders ( i.e., is can the same
        # dataset record be shared across LibraryFolders?
        # Confirm that things should be deleted as follows
        
        ### Deleting the base dataset will delete datasets that exist in user's histories
        ### ( LDA.dataset == HDA.dataset )
        ### Shouldn't this be a separate option?
        ### For Now, I am commenting out logic that acts on the dataset directly
        ### -- Dan:
        
        
        # Delete the LibraryFolderDatasetAssociation
        library_folder_dataset_assoc.deleted = True
        library_folder_dataset_assoc.flush()
    
    @web.expose
    def delete_folder( self, trans, id=None, **kwd):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        if id:
            if 'confirm' not in kwd:
                return trans.show_warn_message( 'Click <a href="%s">here</a> to confirm folder deletion.' % web.url_for( action = 'delete_folder', id = id, confirm=True ) )
            # id is a LibraryFolder.id
            folder = trans.app.model.LibraryFolder.get( id )
            self._delete_folder( folder )
            
            trans.log_event( "Folder id %s deleted." % id )
            
            if folder.library_root:
                trans.response.send_redirect( web.url_for( action = 'library', id = folder.library_root[0].id, msg = 'You have deleted the root folder.' ) )
            trans.response.send_redirect( web.url_for( action = 'folder', id = folder.parent_id, msg = 'The folder was deleted.' ) )
        return trans.show_error_message( "You did not specify a folder to delete." )
    
    def _delete_folder( self, folder ):
        for library_folder_dataset_association in folder.active_datasets:
            self._delete_dataset( library_folder_dataset_association )
        for folder in folder.active_folders:
            self._delete_folder( folder )
        folder.deleted = True
        folder.flush()
    
    @web.expose
    def delete_library( self, trans, id=None, **kwd):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        if id:
            if 'confirm' not in kwd:
                return trans.show_warn_message( 'Click <a href="%s">here</a> to confirm library deletion.' % web.url_for( action = 'delete_library', id = id, confirm=True ) )
            # id is a LibraryFolder.id
            library = trans.app.model.Library.get( id )
            self._delete_folder( library.root_folder )
            library.deleted = True
            library.flush()
            trans.log_event( "Library id %s deleted." % id )
            trans.response.send_redirect( web.url_for( action = 'libraries', msg = 'You have deleted the library %s.' % library.id ) )
        return trans.show_error_message( "You did not specify a library to delete." )

def listify( item, return_none=False ):
    """
    Since single params are not a single item list
    """
    if item is None:
        return []
    elif isinstance( item, list ):
        return item
    else:
        return [ item ]
