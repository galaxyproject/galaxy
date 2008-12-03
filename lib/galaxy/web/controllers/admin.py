import shutil, StringIO, operator, urllib, gzip, tempfile
from galaxy import util, datatypes
from galaxy.web.base.controller import *
from galaxy.datatypes import sniff
from galaxy.security import RBACAgent
from galaxy.model.orm import *

import logging
log = logging.getLogger( __name__ )

class Admin( BaseController ):
    @web.expose
    @web.require_admin
    def index( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        messagetype = params.get( 'messagetype', 'done' )
        return trans.fill_template( '/admin/index.mako', msg=msg, messagetype=messagetype )
    @web.expose
    @web.require_admin
    def center( self, trans, **kwd ):
        return trans.fill_template( '/admin/center.mako' )
    @web.expose
    @web.require_admin
    def reload_tool( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        messagetype = params.get( 'messagetype', 'done' )
        return trans.fill_template( '/admin/reload_tool.mako', toolbox=self.app.toolbox, msg=msg, messagetype=messagetype )
    @web.expose
    @web.require_admin
    def tool_reload( self, trans, tool_version=None, **kwd ):
        params = util.Params( kwd )
        tool_id = params.tool_id
        self.app.toolbox.reload( tool_id )
        msg = 'Reloaded tool: ' + tool_id
        return trans.fill_template( '/admin/reload_tool.mako', toolbox=self.app.toolbox, msg=msg, messagetype='done' )
    
    # Galaxy Role Stuff
    @web.expose
    @web.require_admin
    def roles( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        messagetype = params.get( 'messagetype', 'done' )
        return trans.fill_template( '/admin/dataset_security/roles.mako',
                                    roles=trans.app.model.Role.filter( trans.app.model.Role.table.c.type != trans.app.model.Role.types.PRIVATE ) \
                                                              .order_by( trans.app.model.Role.table.c.name ).all(),
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def create_role( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        messagetype = params.get( 'messagetype', 'done' )
        users = trans.app.model.User.filter( trans.app.model.User.table.c.deleted==False ).order_by( trans.app.model.User.table.c.email ).all()
        groups = trans.app.model.Group.query() \
                .filter( trans.app.model.Group.table.c.deleted==False ) \
                .order_by( trans.app.model.Group.table.c.name ) \
                .all()
        return trans.fill_template( '/admin/dataset_security/role_create.mako', 
                                    users=users,
                                    groups=groups,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def new_role( self, trans, **kwd ):
        params = util.Params( kwd )
        name = params.get( 'name', '' )
        description = params.get( 'description', '' )
        if not name or not description:
            msg = "Enter a valid name and a description"
        elif trans.app.model.Role.filter( trans.app.model.Role.table.c.name==name ).first():
            msg = "A role with that name already exists"
        else:
            # Create the role
            role = trans.app.model.Role( name=name, description=description, type=trans.app.model.Role.types.ADMIN )
            role.flush()
            # Add the users
            users = util.listify( params.users )
            for user_id in users:
                user = trans.app.model.User.get( user_id )
                # Create the UserRoleAssociation
                ura = trans.app.model.UserRoleAssociation( user, role )
                ura.flush()
            # Add the groups
            groups = util.listify( params.groups )
            for group_id in groups:
                group = trans.app.model.Group.get( group_id )
                # Create the GroupRoleAssociation
                gra = trans.app.model.GroupRoleAssociation( group, role )
                gra.flush()
            msg = "The new role has been created with %s associated users and %s associated groups" % ( str( len( users ) ), str( len( groups ) ) )
            trans.response.send_redirect( web.url_for( controller='admin', action='roles', msg=msg, messagetype='done' ) )
        trans.response.send_redirect( web.url_for( controller='admin', action='create_role', msg=msg, messagetype='error' ) )
    @web.expose
    @web.require_admin
    def role( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        messagetype = params.get( 'messagetype', 'done' )
        role = trans.app.model.Role.get( int( params.role_id ) )
        if 'role_members_edit_button' in kwd:
            self.role_members_edit( trans, **kwd )
        in_users = []
        out_users = []
        in_groups = []
        out_groups = []
        for user in trans.app.model.User.filter( trans.app.model.User.table.c.deleted==False ).order_by( trans.app.model.User.table.c.email ).all():
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
        library_dataset_actions = {}
        for adra in role.actions:
            for lfda in trans.app.model.LibraryFolderDatasetAssociation \
                            .filter( trans.app.model.LibraryFolderDatasetAssociation.dataset_id==adra.dataset_id ) \
                            .all():
                root_found = False
                folder_path = ''
                folder = lfda.folder
                while not root_found:
                    folder_path = '%s / %s' % ( folder.name, folder_path )
                    if not folder.parent:
                        root_found = True
                    else:
                        folder = folder.parent
                folder_path = '%s %s' % ( folder_path, lfda.name )
                library = trans.app.model.Library.filter( trans.app.model.Library.table.c.root_folder_id == folder.id ).first()
                if library not in library_dataset_actions:
                    library_dataset_actions[ library ] = {}
                try:
                    library_dataset_actions[ library ][ folder_path ].append( adra.action )
                except:
                    library_dataset_actions[ library ][ folder_path ] = [ adra.action ]
        return trans.fill_template( '/admin/dataset_security/role.mako',
                                    role=role,
                                    in_users=in_users,
                                    out_users=out_users,
                                    in_groups=in_groups,
                                    out_groups=out_groups,
                                    library_dataset_actions=library_dataset_actions,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def role_members_edit( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = params.get( 'msg', '' )
        messagetype = params.get( 'messagetype', 'done' )
        role = trans.app.model.Role.get( int( params.role_id ) )
        in_users = [ trans.app.model.User.get( x ) for x in util.listify( params.in_users ) ]
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
        in_groups = [ trans.app.model.Group.get( x ) for x in util.listify( params.in_groups ) ]
        trans.app.security_agent.set_entity_role_associations( roles=[ role ], users=in_users, groups=in_groups )
        role.refresh()
        msg = "The role has been updated with %s associated users and %s associated groups" % ( str( len( in_users ) ), str( len( in_groups ) ) )
        trans.response.send_redirect( web.url_for( action='roles', msg=msg, messagetype=messagetype ) )
    @web.expose
    @web.require_admin
    def mark_role_deleted( self, trans, **kwd ):
        params = util.Params( kwd )
        role = trans.app.model.Role.get( int( params.role_id ) )
        role.deleted = True
        role.flush()
        msg = "The role has been marked as deleted."
        trans.response.send_redirect( web.url_for( action='roles', msg=msg, messagetype='done' ) )
    @web.expose
    @web.require_admin
    def deleted_roles( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        messagetype = params.get( 'messagetype', 'done' )
        # Build a list of tuples which are roles followed by lists of groups and users
        # [ ( role, [ group, group, group ], [ user, user ] ), ( role, [ group, group ], [ user ] ) ]
        roles_groups_users = []
        roles = trans.app.model.Role.query() \
            .filter( trans.app.model.Role.table.c.deleted==True ) \
            .order_by( trans.app.model.Role.table.c.name ) \
            .all()
        for role in roles:
            groups = []
            for gra in role.groups:
                groups.append( trans.app.model.Group.get( gra.group_id ) )
            users = []
            for ura in role.users:
                users.append( trans.app.model.User.get( ura.user_id ) )
            roles_groups_users.append( ( role, groups, users ) )
        return trans.fill_template( '/admin/dataset_security/deleted_roles.mako', 
                                    roles_groups_users=roles_groups_users, 
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def undelete_role( self, trans, **kwd ):
        params = util.Params( kwd )
        role = trans.app.model.Role.get( int( params.role_id ) )
        role.deleted = False
        role.flush()
        msg = "The role has been marked as not deleted."
        trans.response.send_redirect( web.url_for( action='roles', msg=msg, messagetype='done' ) )
    @web.expose
    @web.require_admin
    def purge_role( self, trans, **kwd ):
        # This method should only be called for a Role that has previously been deleted.
        # Purging a deleted Role deletes all of the following from the database:
        # - UserRoleAssociations where role_id == Role.id
        # - DefaultUserPermissions where role_id == Role.id
        # - DefaultHistoryPermissions where role_id == Role.id
        # - GroupRoleAssociations where role_id == Role.id
        # - ActionDatasetRoleAssociations where role_id == Role.id
        params = util.Params( kwd )
        role = trans.app.model.Role.get( int( params.role_id ) )
        if not role.deleted:
            # We should never reach here, but just in case there is a bug somewhere...
            msg = "The role has not been deleted, so it cannot be purged."
            trans.response.send_redirect( web.url_for( action='roles', msg=msg, messagetype='error' ) )
        # Delete UserRoleAssociations
        for ura in role.users:
            user = trans.app.model.User.get( ura.user_id )
            # Delete DefaultUserPermissions for associated users
            for dup in user.default_permissions:
                if role == dup.role:
                    dup.delete()
                    dup.flush()
            # Delete DefaultHistoryPermissions for associated users
            for history in user.histories:
                for dhp in history.default_permissions:
                    if role == dhp.role:
                        dhp.delete()
                        dhp.flush()
            ura.delete()
            ura.flush()
        # Delete GroupRoleAssociations
        for gra in role.groups:
            gra.delete()
            gra.flush()
        # Delete ActionDatasetRoleAssociations
        for adra in role.actions:
            adra.delete()
            adra.flush()
        msg = "The following have been purged from the database for the role: "
        msg += "DefaultUserPermissions, DefaultHistoryPermissions, UserRoleAssociations, GroupRoleAssociations, ActionDatasetRoleAssociations."
        trans.response.send_redirect( web.url_for( action='deleted_roles', msg=msg, messagetype='done' ) )

    # Galaxy Group Stuff
    @web.expose
    @web.require_admin
    def groups( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        messagetype = params.get( 'messagetype', 'done' )
        # Build a list of tuples which are groups followed by lists of members and roles
        # [ ( group, [ member, member, member ], [ role, role ] ), ( group, [ member, member ], [ role ] ) ]
        groups_members_roles = []
        groups = trans.app.model.Group.query() \
            .filter( trans.app.model.Group.table.c.deleted==False ) \
            .order_by( trans.app.model.Group.table.c.name ) \
            .all()
        for group in groups:
            members = []
            for uga in group.members:
                members.append( trans.app.model.User.get( uga.user_id ) )
            roles = []
            for gra in group.roles:
                roles.append( trans.app.model.Role.get( gra.role_id ) )
            groups_members_roles.append( ( group, members, roles ) )
        return trans.fill_template( '/admin/dataset_security/groups.mako', 
                                    groups_members_roles=groups_members_roles, 
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def create_group( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        messagetype = params.get( 'messagetype', 'done' )
        users = trans.app.model.User.filter( trans.app.model.User.table.c.deleted==False ) \
                                    .order_by( trans.app.model.User.table.c.email ).all()
        roles = trans.app.model.Role.query() \
                .filter( and_( trans.app.model.Role.table.c.deleted == False, 
                               trans.app.model.Role.table.c.type != trans.app.model.Role.types.PRIVATE ) ) \
                .order_by( trans.app.model.Role.table.c.name ).all()
        return trans.fill_template( '/admin/dataset_security/group_create.mako', users=users, roles=roles, msg=msg, messagetype=messagetype )
    @web.expose
    @web.require_admin
    def new_group( self, trans, **kwd ):
        params = util.Params( kwd )
        name = params.name
        if not name:
            msg = "Enter a valid name"
        elif trans.app.model.Group.filter( trans.app.model.Group.table.c.name==name ).first():
            msg = "A group with that name already exists"
        else:
            # Create the group
            group = trans.app.model.Group( name )
            group.flush()
            # Add the members
            members = util.listify( params.members )
            for user_id in members:
                user = trans.app.model.User.get( user_id )
                # Create the UserGroupAssociation
                uga = trans.app.model.UserGroupAssociation( user, group )
                uga.flush()
            # Add the roles
            roles = util.listify( params.roles )
            for role_id in roles:
                role = trans.app.model.Role.get( role_id )
                # Create the GroupRoleAssociation
                gra = trans.app.model.GroupRoleAssociation( group, role )
                gra.flush()
            msg = "The new group has been created with %s members and %s associated roles" % ( str( len( members ) ), str( len( roles ) ) )
            trans.response.send_redirect( web.url_for( controller='admin', action='groups', msg=msg, messagetype='done' ) )
        trans.response.send_redirect( web.url_for( controller='admin', action='create_group', msg=msg, messagetype='error' ) )
    @web.expose
    @web.require_admin
    def group_members_edit( self, trans, **kwd ):
        params = util.Params( kwd )
        group_id = params.get( 'group_id', None )
        if not group_id:
            # TODO: for some reason this is if condition is necessary for functional tests, need to figure out why...
            msg = 'Group identifier was not sent in the request.'
            trans.response.send_redirect( web.url_for( controller='admin', action='groups', msg=msg, messagetype='error' ) )
        elif 'submit_button' in kwd:
            # TODO: why do we reach here in the functional tests????  The action in the template form is /admin/update_group_members...
            self.update_group_members( trans, **kwd )
        group = trans.app.model.Group.get( int( group_id ) )
        group.refresh()
        members = []
        for uga in group.members:
            members.append ( trans.app.model.User.get( uga.user_id ) )
        users = trans.app.model.User.filter( trans.app.model.User.table.c.deleted==False ).order_by( trans.app.model.User.table.c.email ).all()
        msg = "%s currently has %s members" % ( group.name, len( members ) )
        return trans.fill_template( '/admin/dataset_security/group_members_edit.mako', group=group, members=members, users=users, msg=msg, messagetype='done' )
    @web.expose
    @web.require_admin
    def update_group_members( self, trans, **kwd ):
        params = util.Params( kwd )
        group_id = int( params.group_id )
        members = util.listify( params.members )
        group = trans.app.model.Group.get( group_id )
        group.refresh()
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
            user = trans.app.model.User.get( user_id )
            if user not in group.members:
                uga = trans.app.model.UserGroupAssociation( user, group )
                uga.flush()
        msg = "Group membership has been updated with a total of %d members" % len( members )
        trans.response.send_redirect( web.url_for( action='groups', msg=msg, messagetype='done' ) )
    @web.expose
    @web.require_admin
    def group_roles_edit( self, trans, **kwd ):
        params = util.Params( kwd )
        group_id = params.get( 'group_id', None )
        if not group_id:
            # TODO: FIXME: for some reason this is if condition is necessary for functional tests, need to figure out why...
            msg = 'Group identifier was not sent in the request.'
            trans.response.send_redirect( web.url_for( controller='admin', action='groups', msg=msg, messagetype='error' ) )
        elif 'submit_button' in kwd:
            # TODO: FIXME: why do we reach here in the functional tests????  The action in the template form is /admin/update_group_members...
            self.update_group_roles( trans, **kwd )
        group = trans.app.model.Group.get( int( group_id ) )
        group_roles = []
        for gra in group.roles:
            group_roles.append ( trans.app.model.Role.get( gra.role_id ) )
        msg = "%s is currently associated with %s roles" % ( group.name, len( group_roles ) )
        return trans.fill_template( '/admin/dataset_security/group_roles_edit.mako', 
                                    group=group,
                                    group_roles=group_roles,
                                    roles=trans.app.model.Role.filter( trans.app.model.Role.table.c.type != trans.app.model.Role.types.PRIVATE ) \
                                                              .order_by( trans.app.model.Role.table.c.name ).all(),
                                    msg=msg,
                                    messagetype='done' )
    @web.expose
    @web.require_admin
    def update_group_roles( self, trans, **kwd ):
        params = util.Params( kwd )
        group_id = int( params.group_id )
        roles = util.listify( params.roles )
        group = trans.app.model.Group.get( group_id )
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
            role = trans.app.model.Role.get( role_id )
            if role not in group.roles:
                gra = trans.app.model.GroupRoleAssociation( group, role )
                gra.flush()
        msg = "Group updated with a total of %s associated roles" % len( roles )
        trans.response.send_redirect( web.url_for( action='groups', msg=msg, messagetype='done' ) )
    @web.expose
    @web.require_admin
    def mark_group_deleted( self, trans, **kwd ):
        params = util.Params( kwd )
        group = trans.app.model.Group.get( int( params.group_id ) )
        group.deleted = True
        group.flush()
        msg = "The group has been marked as deleted."
        trans.response.send_redirect( web.url_for( action='groups', msg=msg, messagetype='done' ) )
    @web.expose
    @web.require_admin
    def deleted_groups( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        messagetype = params.get( 'messagetype', 'done' )
        # Build a list of tuples which are groups followed by lists of members and roles
        # [ ( group, [ member, member, member ], [ role, role ] ), ( group, [ member, member ], [ role ] ) ]
        groups_members_roles = []
        groups = trans.app.model.Group.query() \
            .filter( trans.app.model.Group.table.c.deleted==True ) \
            .order_by( trans.app.model.Group.table.c.name ) \
            .all()
        for group in groups:
            members = []
            for uga in group.members:
                members.append( trans.app.model.User.get( uga.user_id ) )
            roles = []
            for gra in group.roles:
                roles.append( trans.app.model.Role.get( gra.role_id ) )
            groups_members_roles.append( ( group, members, roles ) )
        return trans.fill_template( '/admin/dataset_security/deleted_groups.mako', 
                                    groups_members_roles=groups_members_roles, 
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def undelete_group( self, trans, **kwd ):
        params = util.Params( kwd )
        group = trans.app.model.Group.get( int( params.group_id ) )
        group.deleted = False
        group.flush()
        msg = "The group has been marked as not deleted."
        trans.response.send_redirect( web.url_for( action='groups', msg=msg, messagetype='done' ) )
    @web.expose
    @web.require_admin
    def purge_group( self, trans, **kwd ):
        # This method should only be called for a Group that has previously been deleted.
        # Purging a deleted Group simply deletes all UserGroupAssociations and GroupRoleAssociations.
        params = util.Params( kwd )
        group = trans.app.model.Group.get( int( params.group_id ) )
        if not group.deleted:
            # We should never reach here, but just in case there is a bug somewhere...
            msg = "The group has not been deleted, so it cannot be purged."
            trans.response.send_redirect( web.url_for( action='groups', msg=msg, messagetype='error' ) )
        # Delete UserGroupAssociations
        for uga in group.users:
            uga.delete()
            uga.flush()
        # Delete GroupRoleAssociations
        for gra in group.roles:
            gra.delete()
            gra.flush()
        # Delete the Group
        msg = "The following have been purged from the database for the group: UserGroupAssociations, GroupRoleAssociations."
        trans.response.send_redirect( web.url_for( action='deleted_groups', msg=msg, messagetype='done' ) )

    # Galaxy User Stuff
    @web.expose
    @web.require_admin
    def create_new_user( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        email = ''
        password = ''
        confirm = ''
        subscribe = False
        messagetype = params.get( 'messagetype', 'done' )
        if 'user_create_button' in kwd:
            if 'email' in kwd:
                email = kwd[ 'email' ]
            if 'password' in kwd:
                password = kwd[ 'password' ]
            if 'confirm' in kwd:
                confirm = kwd[ 'confirm' ]
            if 'subscribe' in kwd:
                subscribe = kwd[ 'subscribe' ]
            messagetype = 'error'
            if len( email ) == 0 or "@" not in email or "." not in email:
                msg = "Please enter a real email address"
            elif len( email) > 255:
                msg = "Email address exceeds maximum allowable length"
            elif trans.app.model.User.filter( trans.app.model.User.table.c.email==email ).first():
                msg = "User with that email already exists"
            elif len( password ) < 6:
                msg = "Please use a password of at least 6 characters"
            elif password != confirm:
                msg = "Passwords do not match"
            else:
                user = trans.app.model.User( email=email )
                user.set_password_cleartext( password )
                user.flush()
                trans.app.security_agent.create_private_user_role( user )
                trans.app.security_agent.user_set_default_permissions( user, history=False, dataset=False )
                trans.log_event( "Admin created a new account for user %s" % email )
                msg = 'Created new user account'
                messagetype = 'done'
                #subscribe user to email list
                if subscribe:
                    mail = os.popen( "%s -t" % trans.app.config.sendmail_path, 'w' )
                    mail.write( "To: %s\nFrom: %s\nSubject: Join Mailing List\n\nJoin Mailing list." % ( trans.app.config.mailing_join_addr, email ) )
                    if mail.close():
                        msg + ". However, subscribing to the mailing list has failed."
                        messagetype = 'error'
                trans.response.send_redirect( web.url_for( action='users', msg=msg, messagetype=messagetype ) )
        return trans.fill_template( '/admin/user/create.mako',
                                    msg=msg,
                                    messagetype=messagetype,
                                    email=email,
                                    password=password,
                                    confirm=confirm,
                                    subscribe=subscribe )
    @web.expose
    @web.require_admin
    def reset_user_password( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        user_id = int( params.user_id )
        user = trans.app.model.User.filter( trans.app.model.User.table.c.id==user_id ).first()
        password = ''
        confirm = ''
        messagetype = params.get( 'messagetype', 'done' )
        if 'reset_user_password_button' in kwd:
            if 'password' in kwd:
                password = kwd[ 'password' ]
            if 'confirm' in kwd:
                confirm = kwd[ 'confirm' ]
            messagetype = 'error'
            if len( password ) < 6:
                msg = "Please use a password of at least 6 characters"
            elif password != confirm:
                msg = "Passwords do not match"
            else:
                user.set_password_cleartext( password )
                user.flush()
                trans.log_event( "Admin reset password for user %s" % user.email )
                msg = 'Password reset'
                messagetype = 'done'
                trans.response.send_redirect( web.url_for( action='users', msg=msg, messagetype=messagetype ) )
        return trans.fill_template( '/admin/user/reset_password.mako',
                                    msg=msg,
                                    messagetype=messagetype,
                                    user=user,
                                    password=password,
                                    confirm=confirm )
    @web.expose
    @web.require_admin
    def mark_user_deleted( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        messagetype = params.get( 'messagetype', 'done' )
        user = trans.app.model.User.get( int( params.user_id ) )
        user.deleted = True
        user.flush()
        msg = "The user has been marked as deleted."
        trans.response.send_redirect( web.url_for( action='users', msg=msg, messagetype='done' ) )
    @web.expose
    @web.require_admin
    def undelete_user( self, trans, **kwd ):
        params = util.Params( kwd )
        user = trans.app.model.User.get( int( params.user_id ) )
        user.deleted = False
        user.flush()
        msg = "The user has been marked as not deleted."
        trans.response.send_redirect( web.url_for( action='users', msg=msg, messagetype='done' ) )
    @web.expose
    @web.require_admin
    def purge_user( self, trans, **kwd ):
        # This method should only be called for a User that has previously been deleted.
        # We keep the User in the database ( marked as purged ), and stuff associated
        # with the user's private role in case we want the ability to unpurge the user 
        # some time in the future.
        # Purging a deleted User deletes all of the following:
        # - DefaultUserPermissions where user_id == User.id EXCEPT FOR THE PRIVATE ROLE
        # - History where user_id = User.id
        #    - DefaultHistoryPermissions where history_id == History.id EXCEPT FOR THE PRIVATE ROLE
        #    - HistoryDatasetAssociation where history_id = History.id
        #    - Dataset where HistoryDatasetAssociation.dataset_id = Dataset.id
        # - UserGroupAssociation where user_id == User.id
        # - UserRoleAssociation where user_id == User.id EXCEPT FOR THE PRIVATE ROLE
        # Purging Histories and Datasets must be handled via the cleanup_datasets.py script
        params = util.Params( kwd )
        user = trans.app.model.User.get( int( params.user_id ) )
        if not user.deleted:
            # We should never reach here, but just in case there is a bug somewhere...
            msg = "The account has not been deleted, so it cannot be purged."
            trans.response.send_redirect( web.url_for( action='users', msg=msg, messagetype='error' ) )
        private_role = trans.app.security_agent.get_private_user_role( user )
        # Delete DefaultUserPermissions EXCEPT FOR THE PRIVATE ROLE
        for dup in user.default_permissions:
            if dup.role_id != private_role.id:
                dup.delete()
                dup.flush()
        # Delete History
        for h in user.active_histories:
            h.refresh()
            # Delete DefaultHistoryPermissions EXCEPT FOR THE PRIVATE ROLE
            for dp in h.default_permissions:
                if dp.role_id != private_role.id:
                    dp.delete()
                    dp.flush()
            for hda in h.active_datasets:
                # Delete HistoryDatasetAssociation
                d = trans.app.model.Dataset.get( hda.dataset_id )
                # Delete Dataset
                if not d.deleted:
                    d.deleted = True
                    d.flush()
                hda.deleted = True
                hda.flush()
            h.deleted = True
            h.flush()
        # Delete UserGroupAssociations
        for uga in user.groups:
            uga.delete()
            uga.flush()
        # Delete UserRoleAssociations EXCEPT FOR THE PRIVATE ROLE
        for ura in user.roles:
            if ura.role_id != private_role.id:
                ura.delete()
                ura.flush()
        # Purge the user
        user.purged = True
        user.flush()
        msg = "The user has been marked as purged."
        trans.response.send_redirect( web.url_for( action='deleted_users', msg=msg, messagetype='done' ) )
    @web.expose
    @web.require_admin
    def deleted_users( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        messagetype = params.get( 'messagetype', 'done' )
        users = trans.app.model.User.filter( and_( trans.app.model.User.table.c.deleted==True, trans.app.model.User.table.c.purged==False ) ) \
                                 .order_by( trans.app.model.User.table.c.email ) \
                                 .all()
        return trans.fill_template( '/admin/user/deleted_users.mako', users=users, msg=msg, messagetype=messagetype )
    @web.expose
    @web.require_admin
    def users( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        messagetype = params.get( 'messagetype', 'done' )
        # Build a list of tuples which are users followed by lists of groups and roles
        # [ ( user, [ group, group, group ], [ role, role ] ), ( user, [ group, group ], [ role ] ) ]
        users_groups_roles = []
        users = trans.app.model.User.filter( trans.app.model.User.table.c.deleted==False ).order_by( trans.app.model.User.table.c.email ).all()
        for user in users:
            groups = []
            for uga in user.groups:
                groups.append( trans.app.model.Group.get( uga.group_id ) )
            roles = []
            for ura in user.non_private_roles:
                roles.append( trans.app.model.Role.get( ura.role_id ) )
            users_groups_roles.append( ( user, groups, roles ) )
        return trans.fill_template( '/admin/dataset_security/users.mako',
                                    users_groups_roles=users_groups_roles,
                                    allow_user_deletion=trans.app.config.allow_user_deletion,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def user( self, trans, **kwd ):
        params = util.Params( kwd )
        user_id = int( params.user_id )
        msg = params.get( 'msg', '' )
        messagetype = params.get( 'messagetype', 'done' )
        user = trans.app.model.User.get( user_id )
        # Get the groups and roles to which the user belongs
        groups = trans.app.model.Group.query() \
                    .select_from( ( outerjoin( trans.app.model.Group, trans.app.model.UserGroupAssociation ) ) \
                    .outerjoin( trans.app.model.User ) ) \
                    .filter( and_( trans.app.model.Group.deleted==False, trans.app.model.User.id==user_id ) ) \
                    .order_by( trans.app.model.Group.table.c.name ) \
                    .all()
        roles = []
        for ura in user.roles:
            roles.append( trans.app.model.Role.get( ura.role_id ) )
        msg += 'User %s is currently a member of %s groups and is associated with %s roles' % ( user.email, str( len( groups ) ), str( len( roles ) ) )
        return trans.fill_template( '/admin/dataset_security/user.mako', 
                                    user=user, 
                                    groups=groups,
                                    roles=roles,
                                    msg=msg,
                                    messagetype='done' )
    @web.expose
    @web.require_admin
    def user_groups_edit( self, trans, **kwd ):
        params = util.Params( kwd )
        user = trans.app.model.User.get( int( params.user_id ) )
        user_groups = []
        for uga in user.groups:
            user_groups.append ( trans.app.model.Group.get( uga.group_id ) )
        groups = trans.app.model.Group.query() \
            .filter( trans.app.model.Group.table.c.deleted==False ) \
            .order_by( trans.app.model.Group.table.c.name ) \
            .all()
        msg = 'User %s is currently a member of %d groups' % ( user.email, len( user_groups ) )
        return trans.fill_template( '/admin/dataset_security/user_groups_edit.mako', 
                                    user=user,
                                    user_groups=user_groups,
                                    groups=groups,
                                    msg=msg,
                                    messagetype='done' )
    @web.expose
    @web.require_admin
    def remove_user_from_group( self, trans, **kwd ):
        params = util.Params( kwd )
        user_id = int( params.user_id )
        group_id = int( params.group_id )
        uga = trans.app.model.UserGroupAssociation.filter( and_( trans.app.model.UserGroupAssociation.table.c.user_id==user_id,
                                                                 trans.app.model.UserGroupAssociation.table.c.group_id==group_id ) ).first()
        uga.delete()
        uga.flush()
        msg = "User removed from group.  "
        trans.response.send_redirect( web.url_for( action='user', user_id=user_id, msg=msg, messagetype='done' ) )
    @web.expose
    @web.require_admin
    def remove_user_from_role( self, trans, **kwd ):
        params = util.Params( kwd )
        user_id = int( params.user_id )
        role_id = int( params.role_id )
        ura = trans.app.model.UserRoleAssociation.filter( and_( trans.app.model.UserRoleAssociation.table.c.user_id==user_id,
                                                                trans.app.model.UserRoleAssociation.table.c.role_id==role_id ) ).first()
        ura.delete()
        ura.flush()
        msg = "User removed from role.  "
        trans.response.send_redirect( web.url_for( action='user', user_id=user_id, msg=msg, messagetype='done' ) )
    @web.expose
    @web.require_admin
    def update_user_groups( self, trans, **kwd ):
        params = util.Params( kwd )
        user_id = int( params.user_id )
        groups = util.listify( params.groups )
        user = trans.app.model.User.get( user_id )
        # First remove existing UserGroupAssociations that are not in the received groups param
        for uga in user.groups:
            if uga.group_id not in groups:
                # Delete the UserGroupAssociation
                uga.delete()
                uga.flush()
        # Then add all new groups to the user
        for group_id in groups:
            group = trans.app.model.Group.get( group_id )
            if group not in user.groups:
                uga = trans.app.model.UserGroupAssociation( user, group )
                uga.flush()
        msg = "User %s now belongs to %s groups" % ( user.email, len( groups ) )
        trans.response.send_redirect( web.url_for( action='users', msg=msg, messagetype='done' ) )

    # Galaxy Library Stuff
    @web.expose
    @web.require_admin
    def library_browser( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        messagetype = params.get( 'messagetype', 'done' )
        created_lfda_ids = params.get( 'created_lfda_ids', '' )
        return trans.fill_template( '/admin/library/browser.mako', 
                                    libraries=trans.app.model.Library.filter( trans.app.model.Library.table.c.deleted==False ) \
                                                                     .order_by( trans.app.model.Library.name ).all(),
                                    created_lfda_ids=created_lfda_ids,
                                    deleted=False,
                                    msg=msg,
                                    messagetype=messagetype )
    libraries = library_browser
    @web.expose
    @web.require_admin
    def library( self, trans, id=None, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'new', False ):
            action = 'new'
        elif params.get( 'rename', False ):
            action = 'rename'
        elif params.get( 'delete', False ):
            action = 'delete'
        else:
            msg = 'Invalid action attempted on library'
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
        if not id and not action == 'new':
            msg = "You must specify a library to %s." % action
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
        if not action == 'new':
            library = trans.app.model.Library.get( int( id ) )
        if action == 'new':
            if params.new == 'submitted':
                library = trans.app.model.Library( name = util.restore_text( params.name ), 
                                                   description = util.restore_text( params.description ) )
                root_folder = trans.app.model.LibraryFolder( name = util.restore_text( params.name ), description = "" )
                root_folder.flush()
                library.root_folder = root_folder
                library.flush()
                msg = 'The new library named %s has been created' % library.name
                return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='done' ) )
            return trans.fill_template( '/admin/library/new_library.mako', msg=msg, messagetype=messagetype )
        elif action == 'rename':
            if params.rename == 'submitted':
                new_name = util.restore_text( params.name )
                new_description = util.restore_text( params.description )
                if not new_name:
                    msg = 'Enter a valid name'
                    return trans.fill_template( '/admin/library/rename_library.mako', library=library, msg=msg, messagetype='error' )
                else:
                    if params.get( 'root_folder', False ):
                        root_folder = library.root_folder
                        root_folder.name = new_name
                        root_folder.flush()
                    library.name = new_name
                    library.description = new_description
                    library.flush()
                    msg = 'The library has been renamed to %s' % new_name
                    return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='done' ) )
            return trans.fill_template( '/admin/library/rename_library.mako', library=library, msg=msg, messagetype=messagetype )
        elif action == 'delete':
            def delete_folder( library_folder ):
                for folder in library_folder.active_folders:
                    delete_folder( folder )
                for lfda in library_folder.active_datasets:
                    # We don't set lfda.dataset.deleted to True here because the cleanup_dataset script
                    # will eventually remove it from disk.  The purge_library method below sets the dataset
                    # to deleted.  This allows for the library to be undeleted ( before it is purged ), 
                    # restoring all of its contents.
                    lfda.deleted = True
                    lfda.flush()
                library_folder.deleted = True
                library_folder.flush()
            delete_folder( library.root_folder )
            library.deleted = True
            library.flush()
            msg = 'The library and all of its contents have been marked deleted'
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='done' ) )
    @web.expose
    @web.require_admin
    def deleted_libraries( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        messagetype = params.get( 'messagetype', 'done' )
        libraries=trans.app.model.Library.filter( and_( trans.app.model.Library.table.c.deleted==True,
                                                        trans.app.model.Library.table.c.purged==False ) ) \
                                         .order_by( trans.app.model.Library.table.c.name ).all()
        return trans.fill_template( '/admin/library/browser.mako', 
                                    libraries=libraries,
                                    deleted=True,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def undelete_library( self, trans, **kwd ):
        params = util.Params( kwd )
        library = trans.app.model.Library.get( int( params.id ) )
        def undelete_folder( library_folder ):
            for folder in library_folder.folders:
                undelete_folder( folder )
            for lfda in library_folder.datasets:
                lfda.deleted = False
                lfda.flush()
            library_folder.deleted = False
            library_folder.flush()
        undelete_folder( library.root_folder )
        library.deleted = False
        library.flush()
        msg = "The library and all of its contents have been marked not deleted"
        return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='done' ) )
    @web.expose
    @web.require_admin
    def purge_library( self, trans, **kwd ):
        params = util.Params( kwd )
        library = trans.app.model.Library.get( int( params.id ) )
        def purge_folder( library_folder ):
            for lf in library_folder.folders:
                purge_folder( lf )
            for lfda in library_folder.datasets:
                lfda.refresh()
                dataset = lfda.dataset
                dataset.refresh()
                # If the dataset is not associated with any additional undeleted folders, then we can delete it.
                # We don't set dataset.purged to True here because the cleanup_datasets script will do that for
                # us, as well as removing the file from disk.
                if not dataset.deleted and len( dataset.active_library_associations ) <= 1: # This is our current lfda
                    dataset.deleted = True
                    dataset.flush()
                lfda.deleted = True
                lfda.flush()
            library_folder.purged = True
            library_folder.flush()
        purge_folder( library.root_folder )
        library.purged = True
        library.flush()
        msg = "The library and all of its contents have been purged, datasets will be removed from disk via the cleanup_datasets script"
        return trans.response.send_redirect( web.url_for( action='deleted_libraries', msg=msg, messagetype='done' ) )
    @web.expose
    @web.require_admin
    def folder( self, trans, id, **kwd ):
        params = util.Params( kwd )
        msg = params.msg
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'new', False ):
            action = 'new'
        elif params.get( 'rename', False ):
            action = 'rename'
        elif params.get( 'delete', False ):
            action = 'delete'
        else:
            msg = "Invalid action attempted on folder."
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
        folder = trans.app.model.LibraryFolder.get( id )
        if not folder:
            msg = "Invalid folder specified, id: %s" % str( id )
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
        if action == 'new':
            if params.new == 'submitted':
                new_folder = trans.app.model.LibraryFolder( name=util.restore_text( params.name ),
                                                            description=util.restore_text( params.description ) )
                # We are associating the last used genome build with folders, so we will always
                # initialize a new folder with the first dbkey in util.dbnames which is currently
                # ?    unspecified (?)
                new_folder.genome_build = util.dbnames.default_value
                folder.add_folder( new_folder )
                new_folder.flush()
                msg = 'The new folder named %s has been added to this library' % new_folder.name
                return trans.response.send_redirect( web.url_for( action='folder', id=new_folder.id, msg=msg, messagetype='done' ) )
            return trans.fill_template( '/admin/library/new_folder.mako', folder=folder, msg=msg, messagetype=messagetype )
        elif action == 'rename':
            if params.rename == 'submitted':
                new_name = util.restore_text( params.name )
                new_description = util.restore_text( params.description )
                if not new_name:
                    msg = 'Enter a valid name'
                    return trans.fill_template( '/admin/library/rename_folder.mako', folder=folder, msg=msg, messagetype='error' )
                else:
                    folder.name = new_name
                    folder.description = new_description
                    folder.flush()
                    msg = 'The folder has been renamed to %s' % new_name
                    return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='done' ) )
            return trans.fill_template( '/admin/library/rename_folder.mako', folder=folder, msg=msg, messagetype=messagetype )
        elif action == 'delete':
            def delete_folder( folder ):
                folder.refresh()
                for subfolder in folder.active_folders:
                    delete_folder( subfolder )
                for lfda in folder.active_datasets:
                    lfda.deleted = True
                    lfda.flush()
                folder.deleted = True
                folder.flush()
            delete_folder( folder )
            msg = 'The folder %s and all of its contents have been marked deleted' % folder.name
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='done' ) )
    @web.expose
    @web.require_admin
    def dataset( self, trans, id=None, name="Unnamed", info='no info', extension=None, folder_id=None, dbkey=None, **kwd ):
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
        messagetype = params.get( 'messagetype', 'done' )

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
                        raise BadFileException( 'problem uncompressing gzipped data.' )
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
                    adra = trans.app.model.ActionDatasetRoleAssociation( RBACAgent.permitted_actions.DATASET_ACCESS.action, dataset.dataset, role )
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
        if params.get( 'new_dataset_button', False ):
            # Copied from upload tool action
            data_file = params.get( 'file_data', '' )
            url_paste = params.get( 'url_paste', '' )
            server_dir = params.get( 'server_dir', 'None' )
            if data_file == '' and url_paste == '' and server_dir in [ 'None', '' ]:
                if trans.app.config.library_import_dir is not None:
                    msg = 'Select a file, enter a URL or Text, or select a server directory.'
                else:
                    msg = 'Select a file, enter a URL or enter Text.'
                trans.response.send_redirect( web.url_for( action='dataset', folder_id=folder_id, msg=msg, messagetype='done' ) )
            space_to_tab = params.get( 'space_to_tab', False )
            if space_to_tab and space_to_tab not in [ "None", None ]:
                space_to_tab = True
            roles = []
            role_ids = params.get( 'roles', [] )
            for role_id in util.listify( role_ids ):
                roles.append( trans.app.model.Role.get( role_id ) )
            temp_name = ""
            data_list = []
            created_lfda_ids = ''
            if 'filename' in dir( data_file ):
                file_name = data_file.filename
                file_name = file_name.split( '\\' )[-1]
                file_name = file_name.split( '/' )[-1]
                created_lfda = add_file( data_file.file,
                                         file_name,
                                         extension,
                                         dbkey,
                                         last_used_build,
                                         roles,
                                         info="uploaded file",
                                         space_to_tab=space_to_tab )
                created_lfda_ids = str( created_lfda.id )
            elif url_paste not in [ None, "" ]:
                if url_paste.lower().find( 'http://' ) >= 0 or url_paste.lower().find( 'ftp://' ) >= 0:
                    url_paste = url_paste.replace( '\r', '' ).split( '\n' )
                    for line in url_paste:
                        line = line.rstrip( '\r\n' )
                        if line:
                            created_lfda = add_file( urllib.urlopen( line ),
                                                     line,
                                                     extension,
                                                     dbkey,
                                                     last_used_build,
                                                     roles,
                                                     info="uploaded url",
                                                     space_to_tab=space_to_tab )
                            created_lfda_ids = '%s,%s' % ( created_lfda_ids, str( created_lfda.id ) )
                else:
                    is_valid = False
                    for line in url_paste:
                        line = line.rstrip( '\r\n' )
                        if line:
                            is_valid = True
                            break
                    if is_valid:
                        created_lfda = add_file( StringIO.StringIO( url_paste ),
                                                 'Pasted Entry',
                                                 extension,
                                                 dbkey,
                                                 last_used_build,
                                                 roles,
                                                 info="pasted entry",
                                                 space_to_tab=space_to_tab )
                        created_lfda_ids = '%s,%s' % ( created_lfda_ids, str( created_lfda.id ) )
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
                    created_lfda = add_file( open( full_file, 'rb' ),
                                             file,
                                             extension,
                                             dbkey,
                                             last_used_build,
                                             roles,
                                             info="imported file",
                                             space_to_tab=space_to_tab )
                    created_lfda_ids = '%s,%s' % ( created_lfda_ids, str( created_lfda.id ) )
            if created_lfda_ids:
                created_lfda_ids = created_lfda_ids.lstrip( ',' )
                total_added = len( created_lfda_ids.split( ',' ) )
                msg = "%i new datasets added to the library ( each is selected below ).  " % total_added
                msg += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                trans.response.send_redirect( web.url_for( action='library_browser', created_lfda_ids=created_lfda_ids, msg=msg, messagetype='done' ) )
            else:
                msg = "Upload failed"
                trans.response.send_redirect( web.url_for( action='library_browser', created_lfda_ids=created_lfda_ids, msg=msg, messagetype='error' ) )

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
                                        msg=msg,
                                        messagetype=messagetype )
        else:
            if id.count( ',' ):
                ids = id.split( ',' )
                id = None
            else:
                ids = None
        # id specified, display attributes form
        if id:
            lda = trans.app.model.LibraryFolderDatasetAssociation.get( id )
            if not lda:
                msg = "Invalid dataset specified, id: %s" %str( id )
                return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )

            # Copied from edit attributes for 'regular' datasets with some additions
            p = util.Params(kwd, safe=False)
            if p.update_roles:
                # The user clicked the Save button on the 'Associate With Roles' form
                permissions = {}
                for k, v in trans.app.model.Dataset.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( p.get( k + '_in', [] ) ) ]
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
                msg = 'Attributes updated for dataset %s' % lda.name
                return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='done' ) )
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
                msg = 'Attributes updated for dataset %s' % lda.name
                return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='done' ) )
            elif p.delete:
                # The user selected the "Remove this dataset from the library" pop-up menu option
                lda.deleted = True
                lda.flush()
                msg = 'Dataset %s has been removed from this library' % lda.name
                trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='done' ) )
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
                                        msg=msg,
                                        messagetype=messagetype )
        # multiple ids specfied, display permission form for each one...
        elif ids:
            lfdas = []
            for id in [ int( id ) for id in ids ]:
                lfda = trans.app.model.LibraryFolderDatasetAssociation.get( id )
                if lfda is None:
                    msg = 'You specified an invalid dataset id: %s' %str( id )
                    trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
                lfdas.append( lfda )
            if len( lfdas ) < 2:
                msg = 'You must specify at least two datasets on which to modify permissions, ids you sent: %s' % str( ids )
                trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
            if 'update_roles' in kwd:
                #p = util.Params( kwd )
                permissions = {}
                for k, v in trans.app.model.Dataset.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                for lfda in lfdas:
                    trans.app.security_agent.set_dataset_permissions( lfda.dataset, permissions )
                    lfda.dataset.refresh()
                msg = 'Permissions and roles have been updated on %d datasets' % len( lfdas )
                trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='done' ) )
            # Ensure that the permissions across all datasets are identical.  Otherwise, we can't update together.
            tmp = []
            for lfda in lfdas:
                perms = trans.app.security_agent.get_dataset_permissions( lfda.dataset )
                if perms not in tmp:
                    tmp.append( perms )
            if len( tmp ) != 1:
                msg = 'The datasets you selected do not have identical permissions, so they can not be updated together'
                trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
            else:
                return trans.fill_template( "/admin/library/dataset.mako", dataset=lfdas )
    @web.expose
    @web.require_admin
    def add_dataset_to_folder_from_history( self, trans, ids="", folder_id=None, **kwd ):
        try:
            folder = trans.app.model.LibraryFolder.get( folder_id )
        except:
            msg = "Invalid folder id: %s" % str( folder_id )
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
        params = util.Params( kwd )
        msg = params.get( 'msg', None )
        messagetype = params.get( 'messagetype', 'done' )
        # See if the current history is empty
        history = trans.get_history()
        history.refresh()
        if not history.active_datasets:
            msg = 'Your current history is empty'
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
        if params.get( 'add_dataset_from_history_button', False ):
            if not isinstance( ids, list ):
                if ids:
                    ids = ids.split( "," )
                else:
                    ids = []
            dataset_names = []
            if ids:
                for data_id in ids:
                    data = trans.app.model.HistoryDatasetAssociation.get( data_id )
                    if data:
                        data.to_library_dataset_folder_association( target_folder = folder )
                        dataset_names.append( data.name )
                    else:
                        msg = "The requested dataset id %s is invalid" % str( data_id )
                        return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
                if dataset_names:
                    msg = "Added the following datasets to the library folder: %s" % ( ", ".join( dataset_names ) )
                    return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='done' ) )
            else:
                msg = 'Select at least one dataset from the list'
                messagetype = 'error'
        return trans.fill_template( "/admin/library/add_dataset_from_history.mako", history=history, folder=folder, msg=msg, messagetype=messagetype )
        
    def check_gzip( self, temp_name ):
        """
        Utility method to check gzipped uploads
        """
        temp = open( temp_name, "U" )
        magic_check = temp.read( 2 )
        temp.close()
        if magic_check != util.gzip_magic:
            return ( False, False )
        CHUNK_SIZE = 2**15 # 32Kb
        gzipped_file = gzip.GzipFile( temp_name )
        chunk = gzipped_file.read( CHUNK_SIZE )
        gzipped_file.close()
        #if self.check_html( temp_name, chunk=chunk ) or self.check_binary( temp_name, chunk=chunk ):
        #    return( True, False )
        return ( True, True )
    @web.expose
    @web.require_admin
    def datasets( self, trans, **kwd ):
        # This method is used by the select list labeled "Perform action on selected datasets" on the admin library browser.
        params = util.Params( kwd )
        msg = params.msg
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'action_on_datasets_button', False ):
            if not params.dataset_ids:
                msg = "At least one dataset must be selected for %s" % params.action
                trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
            dataset_ids = util.listify( params.dataset_ids )
            if params.action == 'edit':
                trans.response.send_redirect( web.url_for( action='dataset', id=",".join( dataset_ids ), msg=msg, messagetype=messagetype ) )
            elif params.action == 'delete':
                for id in dataset_ids:
                    lfda = trans.app.model.LibraryFolderDatasetAssociation.get( id )
                    lfda.deleted = True
                    lfda.flush()
                    msg = "The selected datasets have been removed from this library"
                trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='done' ) )
            else:
                msg = "Action %s is not yet implemented" % str( params.action )
                trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
        else:
            trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype=messagetype ) )
    @web.expose
    @web.require_admin
    def delete_dataset( self, trans, id=None, **kwd):
        if id:
            # id is a LibraryFolderDatasetAssociation.id
            lfda = trans.app.model.LibraryFolderDatasetAssociation.get( id )
            lfda.deleted = True
            lfda.flush()
            msg = "Dataset %s was deleted from library folder %s" % ( lfda.name, lfda.folder.name )
            trans.response.send_redirect( web.url_for( action='folder', 
                                                       id=str( lfda.folder.id ),
                                                       msg=msg,
                                                       messagetype='done' ) )
        msg = "You did not specify a dataset to delete."
        return trans.response.send_redirect( web.url_for( action='folder',
                                                          id=str( lfda.folder.id ),
                                                          msg=msg,
                                                          messagetype='error' ) )

    @web.expose
    @web.require_admin
    def memdump( self, trans, ids = 'None', sorts = 'None', pages = 'None', new_id = None, new_sort = None, **kwd ):
        if self.app.memdump is None:
            return trans.show_error_message( "Memdump is not enabled (set <code>use_memdump = True</code> in universe_wsgi.ini)" )
        heap = self.app.memdump.get()
        p = util.Params( kwd )
        msg = None
        if p.dump:
            heap = self.app.memdump.get( update = True )
            msg = "Heap dump complete"
        elif p.setref:
            self.app.memdump.setref()
            msg = "Reference point set (dump to see delta from this point)"
        ids = ids.split( ',' )
        sorts = sorts.split( ',' )
        if new_id is not None:
            ids.append( new_id )
            sorts.append( 'None' )
        elif new_sort is not None:
            sorts[-1] = new_sort
        breadcrumb = "<a href='%s' class='breadcrumb'>heap</a>" % web.url_for()
        # new lists so we can assemble breadcrumb links
        new_ids = []
        new_sorts = []
        for id, sort in zip( ids, sorts ):
            new_ids.append( id )
            if id != 'None':
                breadcrumb += "<a href='%s' class='breadcrumb'>[%s]</a>" % ( web.url_for( ids=','.join( new_ids ), sorts=','.join( new_sorts ) ), id )
                heap = heap[int(id)]
            new_sorts.append( sort )
            if sort != 'None':
                breadcrumb += "<a href='%s' class='breadcrumb'>.by('%s')</a>" % ( web.url_for( ids=','.join( new_ids ), sorts=','.join( new_sorts ) ), sort )
                heap = heap.by( sort )
        ids = ','.join( new_ids )
        sorts = ','.join( new_sorts )
        if p.theone:
            breadcrumb += ".theone"
            heap = heap.theone
        return trans.fill_template( '/admin/memdump.mako', heap = heap, ids = ids, sorts = sorts, breadcrumb = breadcrumb, msg = msg )
