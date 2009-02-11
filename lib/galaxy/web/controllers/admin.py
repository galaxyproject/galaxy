import shutil, StringIO, operator, urllib, gzip, tempfile
from galaxy import util, datatypes
from galaxy.web.base.controller import *
from galaxy.web.controllers.dataset import upload_dataset
from galaxy.model.orm import *

import logging
log = logging.getLogger( __name__ )

class Admin( BaseController ):
    @web.expose
    @web.require_admin
    def index( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
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
        msg = util.restore_text( params.get( 'msg', ''  ) )
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
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        roles = trans.app.model.Role.filter( and_( trans.app.model.Role.table.c.deleted==False,
                                                   trans.app.model.Role.table.c.type != trans.app.model.Role.types.PRIVATE ) ) \
                                    .order_by( trans.app.model.Role.table.c.name ).all()
        return trans.fill_template( '/admin/dataset_security/roles.mako',
                                    roles=roles,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def create_role( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'create_role_button', False ):
            name = util.restore_text( params.name )
            description = util.restore_text( params.description )
            in_users = util.listify( params.get( 'in_users', [] ) )
            in_groups = util.listify( params.get( 'in_groups', [] ) )
            if not name or not description:
                msg = "Enter a valid name and a description"
            elif trans.app.model.Role.filter( trans.app.model.Role.table.c.name==name ).first():
                msg = "A role with that name already exists"
            else:
                # Create the role
                role = trans.app.model.Role( name=name, description=description, type=trans.app.model.Role.types.ADMIN )
                role.flush()
                # Create the UserRoleAssociations
                for user in [ trans.app.model.User.get( x ) for x in in_users ]:
                    ura = trans.app.model.UserRoleAssociation( user, role )
                    ura.flush()
                # Create the GroupRoleAssociations
                for group in [ trans.app.model.Group.get( x ) for x in in_groups ]:
                    gra = trans.app.model.GroupRoleAssociation( group, role )
                    gra.flush()
                msg = "Role '%s' has been created with %d associated users and %d associated groups" % ( role.name, len( in_users ), len( in_groups ) )
                trans.response.send_redirect( web.url_for( controller='admin', action='roles', msg=util.sanitize_text( msg ), messagetype='done' ) )
            trans.response.send_redirect( web.url_for( controller='admin', action='create_role', msg=util.sanitize_text( msg ), messagetype='error' ) )
        out_users = []
        for user in trans.app.model.User.filter( trans.app.model.User.table.c.deleted==False ).order_by( trans.app.model.User.table.c.email ).all():
            out_users.append( ( user.id, user.email ) )
        out_groups = []
        for group in trans.app.model.Group.filter( trans.app.model.Group.table.c.deleted==False ).order_by( trans.app.model.Group.table.c.name ).all():
            out_groups.append( ( group.id, group.name ) )
        return trans.fill_template( '/admin/dataset_security/role_create.mako',
                                    in_users=[],
                                    out_users=out_users,
                                    in_groups=[],
                                    out_groups=out_groups,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def role( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        role = trans.app.model.Role.get( int( params.role_id ) )
        if params.get( 'role_members_edit_button', False ):
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
            msg = "Role '%s' has been updated with %d associated users and %d associated groups" % ( role.name, len( in_users ), len( in_groups ) )
            trans.response.send_redirect( web.url_for( action='roles', msg=util.sanitize_text( msg ), messagetype=messagetype ) )
        elif params.get( 'rename', False ):
            if params.rename == 'submitted':
                old_name = role.name
                new_name = util.restore_text( params.name )
                new_description = util.restore_text( params.description )
                if not new_name:
                    msg = 'Enter a valid name'
                    return trans.fill_template( '/admin/dataset_security/role_rename.mako', role=role, msg=msg, messagetype='error' )
                elif trans.app.model.Role.filter( trans.app.model.Role.table.c.name==new_name ).first():
                    msg = 'A role with that name already exists'
                    return trans.fill_template( '/admin/dataset_security/role_rename.mako', role=role, msg=msg, messagetype='error' )
                else:
                    role.name = new_name
                    role.description = new_description
                    role.flush()
                    msg = "Role '%s' has been renamed to '%s'" % ( old_name, new_name )
                    return trans.response.send_redirect( web.url_for( action='roles', msg=util.sanitize_text( msg ), messagetype='done' ) )
            return trans.fill_template( '/admin/dataset_security/role_rename.mako', role=role, msg=msg, messagetype=messagetype )
        in_users = []
        out_users = []
        in_groups = []
        out_groups = []
        for user in trans.app.model.User.filter( trans.app.model.User.table.c.deleted==False ).order_by( trans.app.model.User.table.c.email ).all():
            if user in [ x.user for x in role.users ]:
                in_users.append( ( user.id, user.email ) )
            else:
                out_users.append( ( user.id, user.email ) )
        for group in trans.app.model.Group.filter( trans.app.model.Group.table.c.deleted==False ).order_by( trans.app.model.Group.table.c.name ).all():
            if group in [ x.group for x in role.groups ]:
                in_groups.append( ( group.id, group.name ) )
            else:
                out_groups.append( ( group.id, group.name ) )
        # Build a list of tuples that are LibraryDatasetDatasetAssociationss followed by a list of actions
        # whose DatasetPermissions is associated with the Role
        # [ ( LibraryDatasetDatasetAssociation [ action, action ] ) ]
        library_dataset_actions = {}
        for dp in role.actions:
            for ldda in trans.app.model.LibraryDatasetDatasetAssociation \
                            .filter( trans.app.model.LibraryDatasetDatasetAssociation.dataset_id==dp.dataset_id ) \
                            .all():
                root_found = False
                folder_path = ''
                folder = ldda.folder
                while not root_found:
                    folder_path = '%s / %s' % ( folder.name, folder_path )
                    if not folder.parent:
                        root_found = True
                    else:
                        folder = folder.parent
                folder_path = '%s %s' % ( folder_path, ldda.name )
                library = trans.app.model.Library.filter( trans.app.model.Library.table.c.root_folder_id == folder.id ).first()
                if library not in library_dataset_actions:
                    library_dataset_actions[ library ] = {}
                try:
                    library_dataset_actions[ library ][ folder_path ].append( dp.action )
                except:
                    library_dataset_actions[ library ][ folder_path ] = [ dp.action ]
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
    def mark_role_deleted( self, trans, **kwd ):
        params = util.Params( kwd )
        role = trans.app.model.Role.get( int( params.role_id ) )
        role.deleted = True
        role.flush()
        msg = "Role '%s' has been marked as deleted." % role.name
        trans.response.send_redirect( web.url_for( action='roles', msg=util.sanitize_text( msg ), messagetype='done' ) )
    @web.expose
    @web.require_admin
    def deleted_roles( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
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
        msg = "Role '%s' has been marked as not deleted." % role.name
        trans.response.send_redirect( web.url_for( action='roles', msg=util.sanitize_text( msg ), messagetype='done' ) )
    @web.expose
    @web.require_admin
    def purge_role( self, trans, **kwd ):
        # This method should only be called for a Role that has previously been deleted.
        # Purging a deleted Role deletes all of the following from the database:
        # - UserRoleAssociations where role_id == Role.id
        # - DefaultUserPermissions where role_id == Role.id
        # - DefaultHistoryPermissions where role_id == Role.id
        # - GroupRoleAssociations where role_id == Role.id
        # - DatasetPermissionss where role_id == Role.id
        params = util.Params( kwd )
        role = trans.app.model.Role.get( int( params.role_id ) )
        if not role.deleted:
            # We should never reach here, but just in case there is a bug somewhere...
            msg = "Role '%s' has not been deleted, so it cannot be purged." % role.name
            trans.response.send_redirect( web.url_for( action='roles', msg=util.sanitize_text( msg ), messagetype='error' ) )
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
        # Delete DatasetPermissionss
        for dp in role.actions:
            dp.delete()
            dp.flush()
        msg = "The following have been purged from the database for role '%s': " % role.name
        msg += "DefaultUserPermissions, DefaultHistoryPermissions, UserRoleAssociations, GroupRoleAssociations, DatasetPermissionss."
        trans.response.send_redirect( web.url_for( action='deleted_roles', msg=util.sanitize_text( msg ), messagetype='done' ) )

    # Galaxy Group Stuff
    @web.expose
    @web.require_admin
    def groups( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
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
    def group( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        group = trans.app.model.Group.get( int( params.group_id ) )
        if params.get( 'group_roles_users_edit_button', False ):
            in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( params.in_roles ) ]
            in_users = [ trans.app.model.User.get( x ) for x in util.listify( params.in_users ) ]
            trans.app.security_agent.set_entity_group_associations( groups=[ group ], roles=in_roles, users=in_users )
            group.refresh()
            msg += "Group '%s' has been updated with %d associated roles and %d associated users" % ( group.name, len( in_roles ), len( in_users ) )
            trans.response.send_redirect( web.url_for( action='groups', msg=util.sanitize_text( msg ), messagetype=messagetype ) )
        if params.get( 'rename', False ):
            if params.rename == 'submitted':
                old_name = group.name
                new_name = util.restore_text( params.name )
                if not new_name:
                    msg = 'Enter a valid name'
                    return trans.fill_template( '/admin/dataset_security/group_rename.mako', group=group, msg=msg, messagetype='error' )
                elif trans.app.model.Group.filter( trans.app.model.Group.table.c.name==new_name ).first():
                    msg = 'A group with that name already exists'
                    return trans.fill_template( '/admin/dataset_security/group_rename.mako', group=group, msg=msg, messagetype='error' )
                else:
                    group.name = new_name
                    group.flush()
                    msg = "Group '%s' has been renamed to '%s'" % ( old_name, new_name )
                    return trans.response.send_redirect( web.url_for( action='groups', msg=util.sanitize_text( msg ), messagetype='done' ) )
            return trans.fill_template( '/admin/dataset_security/group_rename.mako', group=group, msg=msg, messagetype=messagetype )
        in_roles = []
        out_roles = []
        in_users = []
        out_users = []
        for role in trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.table.c.name ).all():
            if role in [ x.role for x in group.roles ]:
                in_roles.append( ( role.id, role.name ) )
            else:
                out_roles.append( ( role.id, role.name ) )
        for user in trans.app.model.User.filter( trans.app.model.User.table.c.deleted==False ).order_by( trans.app.model.User.table.c.email ).all():
            if user in [ x.user for x in group.users ]:
                in_users.append( ( user.id, user.email ) )
            else:
                out_users.append( ( user.id, user.email ) )
        msg += 'Group %s is currently associated with %d roles and %d users' % ( group.name, len( in_roles ), len( in_users ) )
        return trans.fill_template( '/admin/dataset_security/group.mako',
                                    group=group,
                                    in_roles=in_roles,
                                    out_roles=out_roles,
                                    in_users=in_users,
                                    out_users=out_users,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def create_group( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'create_group_button', False ):
            name = util.restore_text( params.name )
            in_users = util.listify( params.get( 'in_users', [] ) )
            in_roles = util.listify( params.get( 'in_roles', [] ) )
            if not name:
                msg = "Enter a valid name"
            elif trans.app.model.Group.filter( trans.app.model.Group.table.c.name==name ).first():
                msg = "A group with that name already exists"
            else:
                # Create the group
                group = trans.app.model.Group( name=name )
                group.flush()
                # Create the UserRoleAssociations
                for user in [ trans.app.model.User.get( x ) for x in in_users ]:
                    uga = trans.app.model.UserGroupAssociation( user, group )
                    uga.flush()
                # Create the GroupRoleAssociations
                for role in [ trans.app.model.Role.get( x ) for x in in_roles ]:
                    gra = trans.app.model.GroupRoleAssociation( group, role )
                    gra.flush()
                msg = "Group '%s' has been created with %d associated users and %d associated roles" % ( name, len( in_users ), len( in_roles ) )
                trans.response.send_redirect( web.url_for( controller='admin', action='groups', msg=util.sanitize_text( msg ), messagetype='done' ) )
            trans.response.send_redirect( web.url_for( controller='admin', action='create_group', msg=util.sanitize_text( msg ), messagetype='error' ) )
        out_users = []
        for user in trans.app.model.User.filter( trans.app.model.User.table.c.deleted==False ).order_by( trans.app.model.User.table.c.email ).all():
            out_users.append( ( user.id, user.email ) )
        out_roles = []
        for role in trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.table.c.name ).all():
            out_roles.append( ( role.id, role.name ) )
        return trans.fill_template( '/admin/dataset_security/group_create.mako',
                                    in_users=[],
                                    out_users=out_users,
                                    in_roles=[],
                                    out_roles=out_roles,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def mark_group_deleted( self, trans, **kwd ):
        params = util.Params( kwd )
        group = trans.app.model.Group.get( int( params.group_id ) )
        group.deleted = True
        group.flush()
        msg = "Group '%s' has been marked as deleted." % group.name
        trans.response.send_redirect( web.url_for( action='groups', msg=util.sanitize_text( msg ), messagetype='done' ) )
    @web.expose
    @web.require_admin
    def deleted_groups( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
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
        msg = "Group '%s' has been marked as not deleted." % group.name
        trans.response.send_redirect( web.url_for( action='groups', msg=util.sanitize_text( msg ), messagetype='done' ) )
    @web.expose
    @web.require_admin
    def purge_group( self, trans, **kwd ):
        # This method should only be called for a Group that has previously been deleted.
        # Purging a deleted Group simply deletes all UserGroupAssociations and GroupRoleAssociations.
        params = util.Params( kwd )
        group = trans.app.model.Group.get( int( params.group_id ) )
        if not group.deleted:
            # We should never reach here, but just in case there is a bug somewhere...
            msg = "Group '%s' has not been deleted, so it cannot be purged." % group.name
            trans.response.send_redirect( web.url_for( action='groups', msg=util.sanitize_text( msg ), messagetype='error' ) )
        # Delete UserGroupAssociations
        for uga in group.users:
            uga.delete()
            uga.flush()
        # Delete GroupRoleAssociations
        for gra in group.roles:
            gra.delete()
            gra.flush()
        # Delete the Group
        msg = "The following have been purged from the database for group '%s': UserGroupAssociations, GroupRoleAssociations." % group.name
        trans.response.send_redirect( web.url_for( action='deleted_groups', msg=util.sanitize_text( msg ), messagetype='done' ) )

    # Galaxy User Stuff
    @web.expose
    @web.require_admin
    def create_new_user( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
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
                trans.response.send_redirect( web.url_for( action='users', msg=util.sanitize_text( msg ), messagetype=messagetype ) )
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
        msg = util.restore_text( params.get( 'msg', ''  ) )
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
                trans.response.send_redirect( web.url_for( action='users', msg=util.sanitize_text( msg ), messagetype=messagetype ) )
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
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        user = trans.app.model.User.get( int( params.user_id ) )
        user.deleted = True
        user.flush()
        msg = "User '%s' has been marked as deleted." % user.email
        trans.response.send_redirect( web.url_for( action='users', msg=util.sanitize_text( msg ), messagetype='done' ) )
    @web.expose
    @web.require_admin
    def undelete_user( self, trans, **kwd ):
        params = util.Params( kwd )
        user = trans.app.model.User.get( int( params.user_id ) )
        user.deleted = False
        user.flush()
        msg = "User '%s' has been marked as not deleted." % user.email
        trans.response.send_redirect( web.url_for( action='users', msg=util.sanitize_text( msg ), messagetype='done' ) )
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
            msg = "User '%s' has not been deleted, so it cannot be purged." % user.email
            trans.response.send_redirect( web.url_for( action='users', msg=util.sanitize_text( msg ), messagetype='error' ) )
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
        msg = "User '%s' has been marked as purged." % user.email
        trans.response.send_redirect( web.url_for( action='deleted_users', msg=util.sanitize_text( msg ), messagetype='done' ) )
    @web.expose
    @web.require_admin
    def deleted_users( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        users = trans.app.model.User.filter( and_( trans.app.model.User.table.c.deleted==True, trans.app.model.User.table.c.purged==False ) ) \
                                 .order_by( trans.app.model.User.table.c.email ) \
                                 .all()
        return trans.fill_template( '/admin/user/deleted_users.mako', users=users, msg=msg, messagetype=messagetype )
    @web.expose
    @web.require_admin
    def users( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
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
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        user = trans.app.model.User.get( int( params.user_id ) )
        if params.get( 'user_roles_groups_edit_button', False ):
            in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( params.in_roles ) ]
            in_groups = [ trans.app.model.Group.get( x ) for x in util.listify( params.in_groups ) ]
            trans.app.security_agent.set_entity_user_associations( users=[ user ], roles=in_roles, groups=in_groups )
            user.refresh()
            msg += "User '%s' has been updated with %d associated roles and %d associated groups (private roles are not displayed)" % \
                ( user.email, len( in_roles ), len( in_groups ) )
            trans.response.send_redirect( web.url_for( action='users', msg=util.sanitize_text( msg ), messagetype=messagetype ) )
        in_roles = []
        out_roles = []
        in_groups = []
        out_groups = []
        for role in trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.table.c.name ).all():
            if role in [ x.role for x in user.roles ]:
                in_roles.append( ( role.id, role.name ) )
            else:
                out_roles.append( ( role.id, role.name ) )
        for group in trans.app.model.Group.filter( trans.app.model.Group.table.c.deleted==False ).order_by( trans.app.model.Group.table.c.name ).all():
            if group in [ x.group for x in user.groups ]:
                in_groups.append( ( group.id, group.name ) )
            else:
                out_groups.append( ( group.id, group.name ) )
        msg += "User '%s' is currently associated with %d roles and is a member of %d groups" % ( user.email, len( in_roles ), len( in_groups ) )
        return trans.fill_template( '/admin/dataset_security/user.mako',
                                    user=user,
                                    in_roles=in_roles,
                                    out_roles=out_roles,
                                    in_groups=in_groups,
                                    out_groups=out_groups,
                                    msg=msg,
                                    messagetype=messagetype )
    # Utility methods to enable removal of associations - redirects are key
    @web.expose
    @web.require_admin
    def remove_group_from_role( self, trans, **kwd ):
        params = util.Params( kwd )
        group_id = int( params.group_id )
        group = trans.app.model.Group.get( group_id )
        role_id = int( params.role_id )
        role = trans.app.model.Role.get( role_id )
        gra = trans.app.model.GroupRoleAssociation.filter( and_( trans.app.model.GroupRoleAssociation.table.c.group_id==group_id,
                                                                 trans.app.model.GroupRoleAssociation.table.c.role_id==role_id ) ).first()
        gra.delete()
        gra.flush()
        msg = "Group '%s' removed from role '%s'" % ( group.name, role.name )
        trans.response.send_redirect( web.url_for( action='roles', msg=util.sanitize_text( msg ), messagetype='done' ) )
    @web.expose
    @web.require_admin
    def remove_group_from_user( self, trans, **kwd ):
        params = util.Params( kwd )
        group_id = int( params.group_id )
        group = trans.app.model.Group.get( group_id )
        user_id = int( params.user_id )
        user = trans.app.model.User.get( user_id )
        uga = trans.app.model.UserGroupAssociation.filter( and_( trans.app.model.UserGroupAssociation.table.c.group_id==group_id,
                                                                 trans.app.model.UserGroupAssociation.table.c.user_id==user_id ) ).first()
        uga.delete()
        uga.flush()
        msg = "Group '%s' removed from user '%s'" % ( group.name, user.email )
        trans.response.send_redirect( web.url_for( action='users', msg=util.sanitize_text( msg ), messagetype='done' ) )
    @web.expose
    @web.require_admin
    def remove_role_from_group( self, trans, **kwd ):
        params = util.Params( kwd )
        role_id = int( params.role_id )
        role = trans.app.model.Role.get( role_id )
        group_id = int( params.group_id )
        group = trans.app.model.Group.get( group_id )
        gra = trans.app.model.GroupRoleAssociation.filter( and_( trans.app.model.GroupRoleAssociation.table.c.role_id==role_id,
                                                                 trans.app.model.GroupRoleAssociation.table.c.group_id==group_id ) ).first()
        gra.delete()
        gra.flush()
        msg = "Role '%s' removed from group '%s'" % ( role.name, group.name )
        trans.response.send_redirect( web.url_for( action='groups', msg=util.sanitize_text( msg ), messagetype='done' ) )
    @web.expose
    @web.require_admin
    def remove_role_from_user( self, trans, **kwd ):
        params = util.Params( kwd )
        user_id = int( params.user_id )
        user = trans.app.model.User.get( user_id )
        role_id = int( params.role_id )
        role = trans.app.model.Role.get( role_id )
        ura = trans.app.model.UserRoleAssociation.filter( and_( trans.app.model.UserRoleAssociation.table.c.user_id==user_id,
                                                                trans.app.model.UserRoleAssociation.table.c.role_id==role_id ) ).first()
        ura.delete()
        ura.flush()
        msg = "Role '%s' removed from user '%s'" % ( role.name, user.email )
        trans.response.send_redirect( web.url_for( action='users', msg=util.sanitize_text( msg ), messagetype='done' ) )
    @web.expose
    @web.require_admin
    def remove_user_from_group( self, trans, **kwd ):
        params = util.Params( kwd )
        user_id = int( params.user_id )
        user = trans.app.model.User.get( user_id )
        group_id = int( params.group_id )
        group = trans.app.model.Group.get( group_id )
        uga = trans.app.model.UserGroupAssociation.filter( and_( trans.app.model.UserGroupAssociation.table.c.user_id==user_id,
                                                                 trans.app.model.UserGroupAssociation.table.c.group_id==group_id ) ).first()
        uga.delete()
        uga.flush()
        msg = "User '%s' removed from group '%s'" % ( user.email, group.name )
        trans.response.send_redirect( web.url_for( action='groups', msg=util.sanitize_text( msg ), messagetype='done' ) )
    @web.expose
    @web.require_admin
    def remove_user_from_role( self, trans, **kwd ):
        params = util.Params( kwd )
        user_id = int( params.user_id )
        user = trans.app.model.User.get( user_id )
        role_id = int( params.role_id )
        role = trans.app.model.Role.get( role_id )
        ura = trans.app.model.UserRoleAssociation.filter( and_( trans.app.model.UserRoleAssociation.table.c.user_id==user_id,
                                                                trans.app.model.UserRoleAssociation.table.c.role_id==role_id ) ).first()
        ura.delete()
        ura.flush()
        msg = "User '%s' removed from role '%s'" % ( user.email, role.name )
        trans.response.send_redirect( web.url_for( action='roles', msg=util.sanitize_text( msg ), messagetype='done' ) )

    # Galaxy Library Stuff
    @web.expose
    @web.require_admin
    def library_browser( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        created_ldda_ids = params.get( 'created_ldda_ids', '' )
        return trans.fill_template( '/admin/library/browser.mako', 
                                    libraries=trans.app.model.Library.filter( trans.app.model.Library.table.c.deleted==False ) \
                                                                     .order_by( trans.app.model.Library.name ).all(),
                                    created_ldda_ids=created_ldda_ids,
                                    deleted=False,
                                    msg=msg,
                                    messagetype=messagetype )
    libraries = library_browser
    @web.expose
    @web.require_admin
    def library( self, trans, id=None, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'new', False ):
            action = 'new'
        elif params.get( 'manage', False ):
            action = 'manage'
        elif params.get( 'delete', False ):
            action = 'delete'
        elif params.get( 'update_roles', False ):
            action = 'update_roles'
        else:
            msg = 'Invalid action attempted on library'
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='library_browser',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if not id and not action == 'new':
            msg = "You must specify a library to %s." % action
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='library_browser',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
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
                return trans.response.send_redirect( web.url_for( action='library_browser', msg=util.sanitize_text( msg ), messagetype='done' ) )
            return trans.fill_template( '/admin/library/new_library.mako', msg=msg, messagetype=messagetype )
        elif action == 'manage':
            if params.get( 'rename_library_button', False ):
                old_name = library.name
                new_name = util.restore_text( params.name )
                new_description = util.restore_text( params.description )
                if not new_name:
                    msg = 'Enter a valid name'
                    return trans.fill_template( '/admin/library/manage_library.mako', library=library, msg=msg, messagetype='error' )
                else:
                    if params.get( 'root_folder', False ):
                        root_folder = library.root_folder
                        root_folder.name = new_name
                        root_folder.flush()
                        root_folder.refresh()
                    library.name = new_name
                    library.description = new_description
                    library.flush()
                    msg = "Library '%s' has been renamed to '%s'" % ( old_name, new_name )
                    return trans.response.send_redirect( web.url_for( controller='admin',
                                                                      action='library',
                                                                      id=id,
                                                                      manage=True,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='done' ) )
            return trans.fill_template( '/admin/library/manage_library.mako', library=library, msg=msg, messagetype=messagetype )
        elif action == 'delete':
            # TODO: need to revamp the way we delete libraries, folders and contained LibraryDatasets.
            def delete_folder( library_folder ):
                for folder in library_folder.active_folders:
                    delete_folder( folder )
                for ldda in library_folder.active_datasets:
                    # We don't set ldda.dataset.deleted to True here because the cleanup_dataset script
                    # will eventually remove it from disk.  The purge_library method below sets the dataset
                    # to deleted.  This allows for the library to be undeleted ( before it is purged ), 
                    # restoring all of its contents.
                    ldda.deleted = True
                    ldda.flush()
                library_folder.deleted = True
                library_folder.flush()
            delete_folder( library.root_folder )
            library.deleted = True
            library.flush()
            msg = "Library '%s' and all of its contents have been marked deleted" % library.name
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=util.sanitize_text( msg ), messagetype='done' ) )
        elif action == 'update_roles':
            # The user clicked the Save button on the 'Associate With Roles' form
            permissions = {}
            for k, v in trans.app.model.Library.permitted_actions.items():
                in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
            trans.app.security_agent.set_all_library_permissions( library, permissions )
            library.refresh()
            msg = "Permissions updated for library '%s'" % library.name
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='library',
                                                              id=id,
                                                              manage=True,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='done' ) )
    @web.expose
    @web.require_admin
    def deleted_libraries( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
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
            for ldda in library_folder.datasets:
                ldda.deleted = False
                ldda.flush()
            library_folder.deleted = False
            library_folder.flush()
        undelete_folder( library.root_folder )
        library.deleted = False
        library.flush()
        msg = "Library '%s' and all of its contents have been marked not deleted" % library.name
        return trans.response.send_redirect( web.url_for( action='library_browser', msg=util.sanitize_text( msg ), messagetype='done' ) )
    @web.expose
    @web.require_admin
    def purge_library( self, trans, **kwd ):
        params = util.Params( kwd )
        library = trans.app.model.Library.get( int( params.id ) )
        def purge_folder( library_folder ):
            for lf in library_folder.folders:
                purge_folder( lf )
            for ldda in library_folder.datasets:
                ldda.refresh()
                dataset = ldda.dataset
                dataset.refresh()
                # If the dataset is not associated with any additional undeleted folders, then we can delete it.
                # We don't set dataset.purged to True here because the cleanup_datasets script will do that for
                # us, as well as removing the file from disk.
                if not dataset.deleted and len( dataset.active_library_associations ) <= 1: # This is our current ldda
                    dataset.deleted = True
                    dataset.flush()
                ldda.deleted = True
                ldda.flush()
            library_folder.purged = True
            library_folder.flush()
        purge_folder( library.root_folder )
        library.purged = True
        library.flush()
        msg = "Library '%s' and all of its contents have been purged, datasets will be removed from disk via the cleanup_datasets script" % library.name
        return trans.response.send_redirect( web.url_for( action='deleted_libraries', msg=util.sanitize_text( msg ), messagetype='done' ) )
    @web.expose
    @web.require_admin
    def folder( self, trans, id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'new', False ):
            action = 'new'
        elif params.get( 'manage', False ):
            action = 'manage'
        elif params.get( 'delete', False ):
            action = 'delete'
        elif params.get( 'update_roles', False ):
            action = 'update_roles'
        else:
            msg = "Invalid action attempted on folder."
            return trans.response.send_redirect( web.url_for( controller='admin', action='library_browser', msg=util.sanitize_text( msg ), messagetype='error' ) )
        folder = trans.app.model.LibraryFolder.get( id )
        if not folder:
            msg = "Invalid folder specified, id: %s" % str( id )
            return trans.response.send_redirect( web.url_for( controller='admin', action='library_browser', msg=util.sanitize_text( msg ), messagetype='error' ) )
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
                msg = "New folder named '%s' has been added to the library" % new_folder.name
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='folder',
                                                                  id=id,
                                                                  manage=True,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            return trans.fill_template( '/admin/library/new_folder.mako', folder=folder, msg=msg, messagetype=messagetype )
        elif action == 'manage':
            if params.get( 'rename_folder_button', False ):
                old_name = folder.name
                new_name = util.restore_text( params.name )
                new_description = util.restore_text( params.description )
                if not new_name:
                    msg = 'Enter a valid name'
                    return trans.fill_template( '/admin/library/manage_folder.mako', folder=folder, msg=msg, messagetype='error' )
                else:
                    folder.name = new_name
                    folder.description = new_description
                    folder.flush()
                    msg = "Folder '%s' has been renamed to '%s'" % ( old_name, new_name )
                    return trans.response.send_redirect( web.url_for( controller='admin',
                                                                      action='folder',
                                                                      id=id,
                                                                      manage=True,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='done' ) )
            return trans.fill_template( '/admin/library/manage_folder.mako', folder=folder, msg=msg, messagetype=messagetype )
        elif action == 'delete':
            # TODO: need to revamp the way we delete folders and contained LibraryDatasets
            def delete_folder( folder ):
                folder.refresh()
                for subfolder in folder.active_folders:
                    delete_folder( subfolder )
                for ldda in folder.active_datasets:
                    ldda.deleted = True
                    ldda.flush()
                folder.deleted = True
                folder.flush()
            delete_folder( folder )
            msg = "Folder '%s' and all of its contents have been marked deleted" % folder.name
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=util.sanitize_text( msg ), messagetype='done' ) )
        elif action =='update_roles':
            # The user clicked the Save button on the 'Associate With Roles' form
            permissions = {}
            for k, v in trans.app.model.Library.permitted_actions.items():
                in_roles = [ trans.app.model.Role.get( int( x ) ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
            trans.app.security_agent.set_all_library_permissions( folder, permissions )
            folder.refresh()
            msg = "Permissions updated for folder '%s'" % folder.name
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='folder',
                                                              id=id,
                                                              manage=True,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='done' ) )
    @web.expose
    @web.require_admin
    def library_dataset( self, trans, id=None, name=None, info=None, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        library_dataset = trans.app.model.LibraryDataset.get( id )
        if not library_dataset:
            msg = "Invalid library dataset specified, id: %s" %str( id )
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='library_browser',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if params.get( 'edit_attributes_button', False ):
            library_dataset.name  = name
            library_dataset.info  = info
            msg = 'Attributes updated for library dataset %s' % library_dataset.name
        elif params.get( 'change_version', False ):
            target_lda = trans.app.model.LibraryDatasetDatasetAssociation.get( kwd.get( 'set_lda_id' ) )
            library_dataset.library_dataset_dataset_association = target_lda
            trans.app.model.flush()
            msg = 'The current version of this library dataset has been updated to be %s' % target_lda.name
        elif params.get( 'update_roles', False ):
            # The user clicked the Save button on the 'Edit permissions and role associations' form
            permissions = {}
            for k, v in trans.app.model.Library.permitted_actions.items():
                in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
            trans.app.security_agent.set_all_library_permissions( library_dataset, permissions )
            library_dataset.refresh()
            msg = 'Permissions and roles have been updated for library dataset %s' % library_dataset.name
        return trans.fill_template( "/admin/library/manage_library_dataset.mako", 
                                    library_dataset=library_dataset,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def dataset( self, trans, ldda_id=None, name="Unnamed", info='no info', extension=None, folder_id=None, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )        
        dbkey = params.get( 'dbkey', None )
        if isinstance( dbkey, list ):
            last_used_build = dbkey[0]
        else:
            last_used_build = dbkey
        if folder_id and not last_used_build:
            folder = trans.app.model.LibraryFolder.get( folder_id )
            last_used_build = folder.genome_build
        data_files = []
        try:
            replace_dataset = trans.app.model.LibraryDataset.get( params.get( 'replace_id', None ) )
        except:
            replace_dataset = None
        if params.get( 'new_dataset_button', False ):
            created_ldda_ids = upload_dataset( trans,
                                               controller='admin', 
                                               folder_id=folder_id, 
                                               replace_dataset=replace_dataset,
                                               **kwd )
            if created_ldda_ids:
                total_added = len( created_ldda_ids.split( ',' ) )
                msg = "%i new datasets added to the library ( each is selected below ).  " % total_added
                msg += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='library_browser',
                                                           created_ldda_ids=created_ldda_ids, 
                                                           msg=util.sanitize_text( msg ), 
                                                           messagetype='done' ) )
            else:
                msg = "Upload failed"
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='library_browser',
                                                           created_ldda_ids=created_ldda_ids,
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='error' ) )
        elif not ldda_id or replace_dataset:
            # No dataset(s) specified, so display the upload form.
            # Send list of data formats to the form so the "extension" select list can be populated dynamically
            file_formats = trans.app.datatypes_registry.upload_file_formats
            # Send list of genome builds to the form so the "dbkey" select list can be populated dynamically
            def get_dbkey_options( last_used_build ):
                for dbkey, build_name in util.dbnames:
                    yield build_name, dbkey, ( dbkey==last_used_build )
            dbkeys = get_dbkey_options( last_used_build )
            # Send list of roles to the form so the dataset can be associated with 1 or more of them.
            roles = trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.c.name ).all()
            # Send the current history to enable importing datasets from history to library
            history = trans.get_history()
            history.refresh()
            return trans.fill_template( '/admin/library/new_dataset.mako', 
                                        folder_id=folder_id,
                                        file_formats=file_formats,
                                        dbkeys=dbkeys,
                                        last_used_build=last_used_build,
                                        roles=roles,
                                        history=history,
                                        msg=msg,
                                        messagetype=messagetype,
                                        replace_dataset=replace_dataset )
        else:
            if ldda_id.count( ',' ):
                ldda_ids = ldda_id.split( ',' )
                ldda_id = None
            else:
                ldda_ids = None
        if ldda_id:
            # ldda_id specified, display attributes form
            ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( ldda_id )
            if not ldda:
                msg = "Invalid LibraryDatasetDatasetAssociation specified, id: %s" % str( ldda_id )
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='library_browser',
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='error' ) )
            if params.get( 'update_roles', False ):
                # The user clicked the Save button on the 'Associate With Roles' form
                permissions = {}
                for k, v in trans.app.model.Dataset.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                trans.app.security_agent.set_all_dataset_permissions( ldda.dataset, permissions )
                # Set/display library security info
                permissions = {}
                for k, v in trans.app.model.Library.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                trans.app.security_agent.set_all_library_permissions( ldda, permissions )
                ldda.dataset.refresh()
                msg = "Permissions updated for dataset '%s'" % ldda.name
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='dataset',
                                                                  ldda_id=ldda_id,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            elif params.get( 'change', False ):
                # The user clicked the Save button on the 'Change data type' form
                trans.app.datatypes_registry.change_datatype( ldda, params.datatype )
                trans.app.model.flush()
                msg = "Data type changed for dataset '%s'" % ldda.name
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='dataset',
                                                                  ldda_id=ldda_id,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            elif params.get( 'save', False ):
                # The user clicked the Save button on the 'Edit Attributes' form
                ldda.name  = name
                ldda.info  = info
                # The following for loop will save all metadata_spec items
                for name, spec in ldda.datatype.metadata_spec.items():
                    if spec.get("readonly"):
                        continue
                    optional = params.get( "is_" + name, None )
                    if optional and optional == 'true':
                        # optional element... == 'true' actually means it is NOT checked (and therefore ommitted)
                        setattr( ldda.metadata, name, None )
                    else:
                        setattr( ldda.metadata, name, spec.unwrap( params.get ( name, None ) ) )
                ldda.metadata.dbkey = dbkey
                ldda.datatype.after_edit( ldda )
                trans.app.model.flush()
                msg = 'Attributes updated for dataset %s' % ldda.name
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='dataset',
                                                                  ldda_id=ldda_id,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            elif params.get( 'detect', False ):
                # The user clicked the Auto-detect button on the 'Edit Attributes' form
                for name, spec in ldda.datatype.metadata_spec.items():
                    # We need to be careful about the attributes we are resetting
                    if name not in [ 'name', 'info', 'dbkey' ]:
                        if spec.get( 'default' ):
                            setattr( ldda.metadata, name, spec.unwrap( spec.get( 'default' ) ) )
                ldda.datatype.set_meta( ldda )
                ldda.datatype.after_edit( ldda )
                trans.app.model.flush()
                msg = 'Attributes updated for dataset %s' % ldda.name
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='dataset',
                                                                  ldda_id=ldda_id,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            elif params.get( 'delete', False ):
                # TODO: need to revamp the way we remove datasets from disk.
                # The user selected the "Remove this dataset from the library" pop-up menu option
                ldda.deleted = True
                ldda.flush()
                msg = 'Dataset %s has been removed from this library' % ldda.name
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='library_browser',
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='done' ) )
            ldda.datatype.before_edit( ldda )
            if "dbkey" in ldda.datatype.metadata_spec and not ldda.metadata.dbkey:
                # Copy dbkey into metadata, for backwards compatability
                # This looks like it does nothing, but getting the dbkey
                # returns the metadata dbkey unless it is None, in which
                # case it resorts to the old dbkey.  Setting the dbkey
                # sets it properly in the metadata
                ldda.metadata.dbkey = ldda.dbkey
            # let's not overwrite the imported datatypes module with the variable datatypes?
            ### the built-in 'id' is overwritten in lots of places as well
            ldatatypes = [x for x in trans.app.datatypes_registry.datatypes_by_extension.iterkeys()]
            ldatatypes.sort()
            return trans.fill_template( "/admin/library/manage_dataset.mako", 
                                        dataset=ldda, 
                                        datatypes=ldatatypes,
                                        msg=msg,
                                        messagetype=messagetype )
        elif ldda_ids:
            # Multiple ids specfied, display permission form, permissions will be updated for all simultaneously.
            lddas = []
            for ldda_id in [ int( ldda_id ) for ldda_id in ldda_ids ]:
                ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( ldda_id )
                if ldda is None:
                    msg = 'You specified an invalid LibraryDatasetDatasetAssociation id: %s' %str( ldda_id )
                    trans.response.send_redirect( web.url_for( controller='admin',
                                                               action='library_browser',
                                                               msg=util.sanitize_text( msg ),
                                                               messagetype='error' ) )
                lddas.append( ldda )
            if len( lddas ) < 2:
                msg = 'You must specify at least two datasets on which to modify permissions, ids you sent: %s' % str( ldda_ids )
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='library_browser',
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='error' ) )
            if 'update_roles' in kwd:
                #p = util.Params( kwd )
                permissions = {}
                for k, v in trans.app.model.Dataset.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                for ldda in lddas:
                    trans.app.security_agent.set_all_dataset_permissions( ldda.dataset, permissions )
                    ldda.dataset.refresh()
                msg = 'Permissions and roles have been updated on %d datasets' % len( lddas )
                return trans.fill_template( "/admin/library/manage_dataset.mako", msg=msg, messagetype=messagetype, dataset=lddas )
            # Ensure that the permissions across all datasets are identical.  Otherwise, we can't update together.
            tmp = []
            for ldda in lddas:
                perms = trans.app.security_agent.get_dataset_permissions( ldda.dataset )
                if perms not in tmp:
                    tmp.append( perms )
            if len( tmp ) != 1:
                msg = 'The datasets you selected do not have identical permissions, so they can not be updated together'
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='library_browser',
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='error' ) )
            else:
                return trans.fill_template( "/admin/library/manage_dataset.mako", msg=msg, messagetype=messagetype, dataset=lddas )
    @web.expose
    @web.require_admin
    def add_history_datasets_to_library( self, trans, ids="", folder_id=None, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        try:
            folder = trans.app.model.LibraryFolder.get( int( folder_id ) )
        except:
            msg = "Invalid folder id: %s" % str( folder_id )
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=util.sanitize_text( msg ), messagetype='error' ) )
        # See if the current history is empty
        history = trans.get_history()
        history.refresh()
        if not history.active_datasets:
            msg = 'Your current history is empty'
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=util.sanitize_text( msg ), messagetype='error' ) )
        if params.get( 'add_dataset_from_history_button', False ):
            dataset_names = []
            ids = util.listify( ids )
            if ids:
                for data_id in ids:
                    data = trans.app.model.HistoryDatasetAssociation.get( data_id )
                    if data:
                        data.to_library_dataset_dataset_association( target_folder=folder )
                        dataset_names.append( data.name )
                    else:
                        msg = "The requested dataset id %s is invalid" % str( data_id )
                        return trans.response.send_redirect( web.url_for( action='library_browser', msg=util.sanitize_text( msg ), messagetype='error' ) )
                if dataset_names:
                    msg = "Added the following datasets to the library folder: %s" % ( ", ".join( dataset_names ) )
                    return trans.response.send_redirect( web.url_for( action='library_browser', msg=util.sanitize_text( msg ), messagetype='done' ) )
            else:
                msg = 'Select at least one dataset from the list'
                messagetype = 'error'
        return trans.fill_template( "/admin/library/new_dataset.mako", history=history, folder=folder, msg=msg, messagetype=messagetype )
    @web.expose
    @web.require_admin
    def library_item_info_template( self, trans, id=None, new_element_count=0, library_id=None, folder_id=None,
                                    library_dataset_id=None, library_dataset_dataset_association_id=None, **kwd ):
        new_element_count = int( new_element_count )
        library_item_info_template = None
        #library_item_info_template = library = folder = library_dataset = library_dataset_dataset_association = None
        try:
            library_item_info_template = trans.app.model.LibraryItemInfoTemplate.get( id )
        except:
            library_item_info_template = None
        msg = ""
        messagetype="done"
        if id and not library_item_info_template:
            msg = "Invalid library info template specified, id: %s" %str( id )
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=util.sanitize_text( msg ), messagetype='error' ) )
        if 'library_item_info_template_create_button' in kwd:
            #create template then display edit screen
            library_item_info_template = trans.app.model.LibraryItemInfoTemplate()
            library_item_info_template.name = kwd.get( 'name', 'unnamed' )
            library_item_info_template.description = kwd.get( 'description', '' )
            library_item_info_template.flush()
            # Create template association
            if library_id:
                library_item_info_template_assoc = trans.app.model.LibraryInfoTemplateAssociation()
                library_item_info_template_assoc.library = trans.app.model.Library.get( library_id )
            elif folder_id:
                library_item_info_template_assoc = trans.app.model.LibraryFolderInfoTemplateAssociation()
                library_item_info_template_assoc.folder = trans.app.model.LibraryFolder.get( folder_id )
            elif library_dataset_id:
                library_item_info_template_assoc = trans.app.model.LibraryDatasetInfoTemplateAssociation()
                library_item_info_template_assoc.library_dataset = trans.app.model.LibraryDataset.get( library_dataset_id )
            elif library_dataset_dataset_association_id:
                library_item_info_template_assoc = trans.app.model.LibraryDatasetDatasetInfoTemplateAssociation()
                library_item_info_template_assoc.library_dataset_dataset_association = trans.app.model.LibraryDatasetDatasetAssociation.get( library_dataset_dataset_association_id )
            library_item_info_template_assoc.library_item_info_template = library_item_info_template
            library_item_info_template_assoc.flush()
            #now create and add elements
            for i in range( int( kwd.get( 'set_element_count', 0 ) ) ):
                elem_name = kwd.get( 'new_element_name_%i' % i, None )
                elem_description = kwd.get( 'new_element_description_%i' % i, None )
                #skip any elements that have a missing name and description
                if not elem_name:
                    elem_name = elem_description #if we have a description but no name, the description will be both; a name cannot be empty, but a description can
                if elem_name:
                    library_item_info_template.add_element( name = elem_name, description = elem_description )
        elif 'library_item_info_template_edit_button' in kwd:
            #save changes to existing attributes
            #only set name if nonempty/nonNone is passed, but always set description
            name = kwd.get( 'name', None )
            if name:
                library_item_info_template.name = name
            library_item_info_template.description = kwd.get( 'description', '' )
            library_item_info_template.flush()
            #save changes to exisiting elements
            for elem_id in kwd.get( 'element_ids', [] ):
                library_item_info_template_element = trans.app.model.LibraryItemInfoTemplateElement.get( elem_id )
                name = kwd.get( 'element_name_%s' % elem_id, None )
                if name:
                    library_item_info_template_element.name = name
                library_item_info_template_element.description = kwd.get( 'element_description_%s' % elem_id, None )
                library_item_info_template_element.flush()
            #add new elements
            for i in range( int( kwd.get( 'set_element_count', 0 ) ) ):
                elem_name = kwd.get( 'new_element_name_%i' % i, None )
                elem_description = kwd.get( 'new_element_description_%i' % i, None )
                #skip any elements that have a missing name and description
                if not elem_name:
                    elem_name = elem_description #if we have a description but no name, the description will be both; a name cannot be empty, but a description can
                if elem_name:
                    library_item_info_template.add_element( name = elem_name, description = elem_description )
            library_item_info_template.refresh()
        return trans.fill_template( "/admin/library/item_info_template.mako",
                                    library_item_info_template = library_item_info_template,
                                    new_element_count=new_element_count,
                                    library_id=library_id,
                                    library_dataset_id=library_dataset_id,
                                    library_dataset_dataset_association_id=library_dataset_dataset_association_id,
                                    folder_id=folder_id,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def download_dataset_from_folder(self, trans, id, **kwd):
        """Catches the dataset id and displays file contents as directed"""
        # id must refer to a LibraryDatasetDatasetAssociation object
        ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
        if not ldda.dataset:
            msg = 'Invalid LibraryDatasetDatasetAssociation id %s received for file downlaod' % str( id )
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=util.sanitize_text( msg ), messagetype='error' ) )
        mime = trans.app.datatypes_registry.get_mimetype_by_extension( ldda.extension.lower() )
        trans.response.set_content_type( mime )
        fStat = os.stat( ldda.file_name )
        trans.response.headers[ 'Content-Length' ] = int( fStat.st_size )
        valid_chars = '.,^_-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        fname = ldda.name
        fname = ''.join( c in valid_chars and c or '_' for c in fname )[ 0:150 ]
        trans.response.headers[ "Content-Disposition" ] = "attachment; filename=GalaxyLibraryDataset-%s-[%s]" % ( str( id ), fname )
        try:
            return open( ldda.file_name )
        except: 
            msg = 'This dataset contains no content'
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=util.sanitize_text( msg ), messagetype='error' ) )
    @web.expose
    @web.require_admin
    def datasets( self, trans, **kwd ):
        # This method is used by the select list labeled "Perform action on selected datasets"
        # on the admin library browser.
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'action_on_datasets_button', False ):
            if not params.ldda_ids:
                msg = "At least one dataset must be selected for %s" % params.action
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='library_browser',
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='error' ) )
            ldda_ids = util.listify( params.ldda_ids )
            if params.action == 'edit':
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='dataset',
                                                           ldda_id=",".join( ldda_ids ),
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype=messagetype ) )
            elif params.action == 'delete':
                for id in ldda_ids:
                    ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
                    ldda.deleted = True
                    ldda.flush()
                    msg = "The selected datasets have been removed from this library"
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='library_browser',
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='done' ) )
            else:
                msg = "Action %s is not yet implemented" % str( params.action )
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='library_browser',
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='error' ) )
        else:
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='library_browser',
                                                       msg=util.sanitize_text( msg ),
                                                       messagetype=messagetype ) )
    @web.expose
    @web.require_admin
    def delete_dataset( self, trans, id=None, **kwd):
        if id:
            # id is a LibraryDatasetDatasetAssociation.id
            ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
            ldda.deleted = True
            ldda.flush()
            msg = "Dataset %s was deleted from library folder %s" % ( ldda.name, ldda.folder.name )
            trans.response.send_redirect( web.url_for( action='folder', 
                                                       id=str( ldda.folder.id ),
                                                       msg=util.sanitize_text( msg ),
                                                       messagetype='done' ) )
        msg = "You did not specify a dataset to delete."
        return trans.response.send_redirect( web.url_for( action='folder',
                                                          id=str( ldda.folder.id ),
                                                          msg=util.sanitize_text( msg ),
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
