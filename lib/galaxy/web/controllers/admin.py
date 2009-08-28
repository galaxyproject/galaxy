import shutil, StringIO, operator, urllib, gzip, tempfile, string, sys
from datetime import datetime, timedelta
from galaxy import util, datatypes
from galaxy.web.base.controller import *
from galaxy.model.orm import *
from galaxy.web.controllers.forms import get_all_forms, get_form_widgets
# Older py compatibility
try:
    set()
except:
    from sets import Set as set

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
            create_group_for_role = params.get( 'create_group_for_role', 'no' )
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
                if create_group_for_role == 'yes':
                    # Create the group
                    group = trans.app.model.Group( name=name )
                    group.flush()
                    msg = "Group '%s' has been created, and role '%s' has been created with %d associated users and %d associated groups" % \
                    ( group.name, role.name, len( in_users ), len( in_groups ) )
                else:
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
                folder = ldda.library_dataset.folder
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
        roles = trans.app.model.Role.query() \
            .filter( trans.app.model.Role.table.c.deleted==True ) \
            .order_by( trans.app.model.Role.table.c.name ) \
            .all()
        return trans.fill_template( '/admin/dataset_security/deleted_roles.mako', 
                                    roles=roles, 
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
        for dp in role.dataset_actions:
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
        groups = trans.app.model.Group.query() \
            .filter( trans.app.model.Group.table.c.deleted==False ) \
            .order_by( trans.app.model.Group.table.c.name ) \
            .all()
        return trans.fill_template( '/admin/dataset_security/groups.mako', 
                                    groups=groups, 
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
        groups = trans.app.model.Group.query() \
            .filter( trans.app.model.Group.table.c.deleted==True ) \
            .order_by( trans.app.model.Group.table.c.name ) \
            .all()
        return trans.fill_template( '/admin/dataset_security/deleted_groups.mako', 
                                    groups=groups, 
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
                if trans.app.config.use_remote_user:
                    user.external = True
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
        # - History where user_id = User.id
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
        # Delete History
        for h in user.active_histories:
            h.refresh()
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
        users = trans.app.model.User.filter( trans.app.model.User.table.c.deleted==False ).order_by( trans.app.model.User.table.c.email ).all()
        return trans.fill_template( '/admin/dataset_security/users.mako',
                                    users=users,
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
        private_role = trans.app.security_agent.get_private_user_role( user )
        if params.get( 'user_roles_groups_edit_button', False ):
            # Make sure the user is not dis-associating himself from his private role
            out_roles = [ trans.app.model.Role.get( x ) for x in util.listify( params.out_roles ) ]
            if private_role in out_roles:
                msg += "You cannot eliminate a user's private role association.  "
                messagetype = 'error'
            in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( params.in_roles ) ]
            out_groups = [ trans.app.model.Group.get( x ) for x in util.listify( params.out_groups ) ]
            in_groups = [ trans.app.model.Group.get( x ) for x in util.listify( params.in_groups ) ]
            if in_roles:
                trans.app.security_agent.set_entity_user_associations( users=[ user ], roles=in_roles, groups=in_groups )
                user.refresh()
                msg += "User '%s' has been updated with %d associated roles and %d associated groups (private roles are not displayed)" % \
                    ( user.email, len( in_roles ), len( in_groups ) )
                trans.response.send_redirect( web.url_for( action='users', msg=util.sanitize_text( msg ), messagetype=messagetype ) )
        in_roles = []
        out_roles = []
        in_groups = []
        out_groups = []
        for role in trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ) \
                                        .order_by( trans.app.model.Role.table.c.name ).all():
            if role in [ x.role for x in user.roles ]:
                in_roles.append( ( role.id, role.name ) )
            elif role.type != trans.app.model.Role.types.PRIVATE:
                # There is a 1 to 1 mapping between a user and a PRIVATE role, so private roles should
                # not be listed in the roles form fields, except for the currently selected user's private
                # role, which should always be in in_roles.  The check above is added as an additional
                # precaution, since for a period of time we were including private roles in the form fields.
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

    # Galaxy Library Stuff
    @web.expose
    @web.require_admin
    def browse_libraries( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        return trans.fill_template( '/admin/library/browse_libraries.mako', 
                                    libraries=trans.app.model.Library.filter( trans.app.model.Library.table.c.deleted==False ) \
                                                                     .order_by( trans.app.model.Library.name ).all(),
                                    deleted=False,
                                    show_deleted=False,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def browse_library( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        id = params.get( 'id', None )
        deleted = util.string_as_bool( params.get( 'deleted', False ) )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        if not id:
            msg = "You must specify a library id."
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='browse_libraries',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        library = library=trans.app.model.Library.get( id )
        if not library:
            msg = "Invalid library id ( %s )."
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='browse_libraries',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        created_ldda_ids = params.get( 'created_ldda_ids', '' )
        return trans.fill_template( '/admin/library/browse_library.mako', 
                                    library=trans.app.model.Library.get( id ),
                                    deleted=deleted,
                                    created_ldda_ids=created_ldda_ids,
                                    forms=get_all_forms( trans, filter=dict(deleted=False) ),
                                    msg=msg,
                                    messagetype=messagetype,
                                    show_deleted=show_deleted )
    @web.expose
    @web.require_admin
    def library( self, trans, id=None, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'new', False ):
            action = 'new'
        elif params.get( 'delete', False ):
            action = 'delete'
        elif params.get( 'permissions', False ):
            action = 'permissions'
        else:
            action = 'information'
        if not id and not action == 'new':
            msg = "You must specify a library to %s." % action
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='browse_libraries',
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
                msg = "The new library named '%s' has been created" % library.name
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='browse_library',
                                                                  id=library.id,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            return trans.fill_template( '/admin/library/new_library.mako', msg=msg, messagetype=messagetype )
        elif action == 'information':
            # See if we have any associated templates
            info_association = library.get_info_association()
            if info_association:
                template = info_association.template
                # See if we have any field contents
                info = info_association.info
                if info:
                    widgets = get_form_widgets( trans, template, info.content )
                else:
                    widgets = get_form_widgets( trans, template )
            else:
                widgets = []
            if params.get( 'rename_library_button', False ):
                old_name = library.name
                new_name = util.restore_text( params.name )
                new_description = util.restore_text( params.description )
                if not new_name:
                    msg = 'Enter a valid name'
                    return trans.fill_template( '/admin/library/library_info.mako',
                                                library=library,
                                                widgets=widgets,
                                                msg=msg,
                                                messagetype='error' )
                else:
                    library.name = new_name
                    library.description = new_description
                    library.flush()
                    # Rename the root_folder
                    library.root_folder.name = new_name
                    library.root_folder.description = new_description
                    library.root_folder.flush()
                    msg = "Library '%s' has been renamed to '%s'" % ( old_name, new_name )
                    return trans.response.send_redirect( web.url_for( controller='admin',
                                                                      action='library',
                                                                      id=id,
                                                                      edit_info=True,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='done' ) )
            return trans.fill_template( '/admin/library/library_info.mako',
                                        library=library,
                                        widgets=widgets,
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'delete':
            def delete_folder( library_folder ):
                library_folder.refresh()
                for folder in library_folder.folders:
                    delete_folder( folder )
                for library_dataset in library_folder.datasets:
                    library_dataset.refresh()
                    ldda = library_dataset.library_dataset_dataset_association
                    if ldda:
                        ldda.refresh()
                        # We don't set ldda.dataset.deleted to True here because the cleanup_dataset script
                        # will eventually remove it from disk.  The purge_library method below sets the dataset
                        # to deleted.  This allows for the library to be undeleted ( before it is purged ), 
                        # restoring all of its contents.
                        ldda.deleted = True
                        ldda.flush()
                    library_dataset.deleted = True
                    library_dataset.flush()
                library_folder.deleted = True
                library_folder.flush()
            library.refresh()
            delete_folder( library.root_folder )
            library.deleted = True
            library.flush()
            msg = "Library '%s' and all of its contents have been marked deleted" % library.name
            return trans.response.send_redirect( web.url_for( action='browse_libraries', msg=util.sanitize_text( msg ), messagetype='done' ) )
        elif action == 'permissions':
            if params.get( 'update_roles_button', False ):
                # The user clicked the Save button on the 'Associate With Roles' form
                permissions = {}
                for k, v in trans.app.model.Library.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                trans.app.security_agent.set_all_library_permissions( library, permissions )
                library.refresh()
                # Copy the permissions to the root folder
                trans.app.security_agent.copy_library_permissions( library, library.root_folder )
                msg = "Permissions updated for library '%s'" % library.name
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='library',
                                                                  id=id,
                                                                  permissions=True,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            return trans.fill_template( '/admin/library/library_permissions.mako',
                                        library=library,
                                        msg=msg,
                                        messagetype=messagetype )
    @web.expose
    @web.require_admin
    def deleted_libraries( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        libraries=trans.app.model.Library.filter( and_( trans.app.model.Library.table.c.deleted==True,
                                                        trans.app.model.Library.table.c.purged==False ) ) \
                                         .order_by( trans.app.model.Library.table.c.name ).all()
        return trans.fill_template( '/admin/library/browse_libraries.mako', 
                                    libraries=libraries,
                                    deleted=True,
                                    msg=msg,
                                    messagetype=messagetype,
                                    show_deleted=True )
    @web.expose
    @web.require_admin
    def purge_library( self, trans, **kwd ):
        params = util.Params( kwd )
        library = trans.app.model.Library.get( int( params.id ) )
        def purge_folder( library_folder ):
            for lf in library_folder.folders:
                purge_folder( lf )
            library_folder.refresh()
            for library_dataset in library_folder.datasets:
                library_dataset.refresh()
                ldda = library_dataset.library_dataset_dataset_association
                if ldda:
                    ldda.refresh()
                    dataset = ldda.dataset
                    dataset.refresh()
                    # If the dataset is not associated with any additional undeleted folders, then we can delete it.
                    # We don't set dataset.purged to True here because the cleanup_datasets script will do that for
                    # us, as well as removing the file from disk.
                    #if not dataset.deleted and len( dataset.active_library_associations ) <= 1: # This is our current ldda
                    dataset.deleted = True
                    dataset.flush()
                    ldda.deleted = True
                    ldda.flush()
                library_dataset.deleted = True
                library_dataset.flush()
            library_folder.deleted = True
            library_folder.purged = True
            library_folder.flush()
        if not library.deleted:
            msg = "Library '%s' has not been marked deleted, so it cannot be purged" % ( library.name )
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='browse_libraries',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        else:
            purge_folder( library.root_folder )
            library.purged = True
            library.flush()
            msg = "Library '%s' and all of its contents have been purged, datasets will be removed from disk via the cleanup_datasets script" % library.name
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='deleted_libraries',
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='done' ) )
    @web.expose
    @web.require_admin
    def folder( self, trans, id, library_id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )            
        if params.get( 'new', False ):
            action = 'new'
        elif params.get( 'delete', False ):
            action = 'delete'
        elif params.get( 'permissions', False ):
            action = 'permissions'
        else:
            # 'information' will be the default
            action = 'information'
        folder = trans.app.model.LibraryFolder.get( int( id ) )
        if not folder:
            msg = "Invalid folder specified, id: %s" % str( id )
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
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
                # New folders default to having the same permissions as their parent folder
                trans.app.security_agent.copy_library_permissions( folder, new_folder )
                msg = "New folder named '%s' has been added to the library" % new_folder.name
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='browse_library',
                                                                  id=library_id,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            return trans.fill_template( '/admin/library/new_folder.mako',
                                        library_id=library_id,
                                        folder=folder,
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'information':
            # See if we have any associated templates
            info_association = folder.get_info_association()
            if info_association:
                template = info_association.template
                # See if we have any field contents
                info = info_association.info
                if info:
                    widgets = get_form_widgets( trans, template, info.content )
                else:
                    widgets = get_form_widgets( trans, template )
            else:
                widgets = []
            if params.get( 'rename_folder_button', False ):
                old_name = folder.name
                new_name = util.restore_text( params.name )
                new_description = util.restore_text( params.description )
                if not new_name:
                    msg = 'Enter a valid name'
                    return trans.fill_template( '/admin/library/folder_info.mako',
                                                folder=folder,
                                                library_id=library_id,
                                                widgets=widgets,
                                                msg=msg,
                                                messagetype='error' )
                else:
                    folder.name = new_name
                    folder.description = new_description
                    folder.flush()
                    msg = "Folder '%s' has been renamed to '%s'" % ( old_name, new_name )
                    return trans.response.send_redirect( web.url_for( controller='admin',
                                                                      action='folder',
                                                                      id=id,
                                                                      library_id=library_id,
                                                                      edit_info=True,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='done' ) )
            return trans.fill_template( '/admin/library/folder_info.mako',
                                        folder=folder,
                                        library_id=library_id,
                                        widgets=widgets,
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'delete':
            folder.deleted = True
            folder.flush()
            msg = "Folder '%s' and all of its contents have been marked deleted" % folder.name
            return trans.response.send_redirect( web.url_for( action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='done' ) )
        elif action =='permissions':
            if params.get( 'update_roles_button', False ):
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
                                                                  library_id=library_id,
                                                                  permissions=True,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='done' ) )
            return trans.fill_template( '/admin/library/folder_permissions.mako',
                                        folder=folder,
                                        library_id=library_id,
                                        msg=msg,
                                        messagetype=messagetype )
    @web.expose
    @web.require_admin
    def library_dataset( self, trans, id, library_id, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'permissions', False ):
            action = 'permissions'
        else:
            action = 'information'
        library_dataset = trans.app.model.LibraryDataset.get( id )
        if not library_dataset:
            msg = "Invalid library dataset specified, id: %s" %str( id )
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if action == 'information':
            if params.get( 'edit_attributes_button', False ):
                old_name = library_dataset.name
                new_name = util.restore_text( params.get( 'name', '' ) )
                new_info = util.restore_text( params.get( 'info', '' ) )
                if not new_name:
                    msg = 'Enter a valid name'
                    messagetype = 'error'
                else:
                    library_dataset.name = new_name
                    library_dataset.info = new_info
                    library_dataset.flush()
                    msg = "Dataset '%s' has been renamed to '%s'" % ( old_name, new_name )
                    messagetype = 'done'
            return trans.fill_template( '/admin/library/library_dataset_info.mako',
                                        library_dataset=library_dataset,
                                        library_id=library_id,
                                        msg=msg,
                                        messagetype=messagetype )
        elif action == 'permissions':
            if params.get( 'update_roles_button', False ):
                # The user clicked the Save button on the 'Edit permissions and role associations' form
                permissions = {}
                for k, v in trans.app.model.Library.permitted_actions.items():
                    in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                # Set the LIBRARY permissions on the LibraryDataset
                # NOTE: the LibraryDataset and LibraryDatasetDatasetAssociation will be set with the same permissions
                trans.app.security_agent.set_all_library_permissions( library_dataset, permissions )
                library_dataset.refresh()
                # Set the LIBRARY permissions on the LibraryDatasetDatasetAssociation
                trans.app.security_agent.set_all_library_permissions( library_dataset.library_dataset_dataset_association, permissions )
                library_dataset.library_dataset_dataset_association.refresh()
                msg = 'Permissions and roles have been updated for library dataset %s' % library_dataset.name
            return trans.fill_template( '/admin/library/library_dataset_permissions.mako',
                                        library_dataset=library_dataset,
                                        library_id=library_id,
                                        msg=msg,
                                        messagetype=messagetype )
    @web.expose
    @web.require_admin
    def library_dataset_dataset_association( self, trans, library_id, folder_id, id=None, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        deleted = util.string_as_bool( params.get( 'deleted', False ) )
        show_deleted = util.string_as_bool( params.get( 'show_deleted', False ) )
        dbkey = params.get( 'dbkey', None )
        if isinstance( dbkey, list ):
            last_used_build = dbkey[0]
        else:
            last_used_build = dbkey
        folder = trans.app.model.LibraryFolder.get( folder_id )
        if folder and last_used_build in [ 'None', None, '?' ]:
            last_used_build = folder.genome_build
        replace_id = params.get( 'replace_id', None )
        if replace_id:
            replace_dataset = trans.app.model.LibraryDataset.get( int( replace_id ) )
            if not last_used_build:
                last_used_build = replace_dataset.library_dataset_dataset_association.dbkey
        else:
            replace_dataset = None
        # Let's not overwrite the imported datatypes module with the variable datatypes?
        # The built-in 'id' is overwritten in lots of places as well
        ldatatypes = [ dtype_name for dtype_name, dtype_value in trans.app.datatypes_registry.datatypes_by_extension.iteritems() if dtype_value.allow_datatype_change ]
        ldatatypes.sort()
        if params.get( 'new_dataset_button', False ):
            upload_option = params.get( 'upload_option', 'upload_file' )
            created_ldda_ids = trans.webapp.controllers[ 'library_dataset' ].upload_dataset( trans,
                                                                                             controller='admin',
                                                                                             library_id=library_id,
                                                                                             folder_id=folder_id,
                                                                                             replace_dataset=replace_dataset,
                                                                                             **kwd )
            if created_ldda_ids:
                total_added = len( created_ldda_ids.split( ',' ) )
                if replace_dataset:
                    msg = "Added %d dataset versions to the library dataset '%s' in the folder '%s'." % ( total_added, replace_dataset.name, folder.name )
                else:
                    if not folder.parent:
                        # Libraries have the same name as their root_folder
                        msg = "Added %d datasets to the library '%s' ( each is selected ).  " % ( total_added, folder.name )
                    else:
                        msg = "Added %d datasets to the folder '%s' ( each is selected ).  " % ( total_added, folder.name )
                    msg += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                messagetype='done'
            else:
                msg = "Upload failed"
                messagetype='error'
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='browse_library',
                                                       id=library_id,
                                                       created_ldda_ids=created_ldda_ids,
                                                       msg=util.sanitize_text( msg ),
                                                       messagetype=messagetype ) )
        elif not id or replace_dataset:
            # See if we have any associated templates
            info_association = folder.get_info_association()
            if info_association:
                template = info_association.template
                widgets = get_form_widgets( trans, template )
            else:
                widgets = []
            upload_option = params.get( 'upload_option', 'upload_file' )
            # No dataset(s) specified, so display the upload form.  Send list of data formats to the form
            # so the "extension" select list can be populated dynamically
            file_formats = trans.app.datatypes_registry.upload_file_formats
            # Send list of genome builds to the form so the "dbkey" select list can be populated dynamically
            def get_dbkey_options( last_used_build ):
                for dbkey, build_name in util.dbnames:
                    yield build_name, dbkey, ( dbkey==last_used_build )
            dbkeys = get_dbkey_options( last_used_build )
            # Send list of roles to the form so the dataset can be associated with 1 or more of them.
            roles = trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.c.name ).all()
            # Send the current history to the form to enable importing datasets from history to library
            history = trans.get_history()
            history.refresh()
            return trans.fill_template( '/admin/library/new_dataset.mako',
                                        upload_option=upload_option,
                                        library_id=library_id,
                                        folder_id=folder_id,
                                        replace_id=replace_id,
                                        file_formats=file_formats,
                                        dbkeys=dbkeys,
                                        last_used_build=last_used_build,
                                        roles=roles,
                                        history=history,
                                        widgets=widgets,
                                        msg=msg,
                                        messagetype=messagetype,
                                        replace_dataset=replace_dataset )
        else:
            if params.get( 'permissions', False ):
                action = 'permissions'
            elif params.get( 'edit_info', False ):
                action = 'edit_info'
            else:
                action = 'info'
            if id.count( ',' ):
                ids = id.split( ',' )
                id = None
            else:
                ids = None
        if id:
            # ldda_id specified, display attributes form
            ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
            if not ldda:
                msg = "Invalid LibraryDatasetDatasetAssociation specified, id: %s" % str( id )
                return trans.response.send_redirect( web.url_for( controller='admin',
                                                                  action='browse_library',
                                                                  id=library_id,
                                                                  msg=util.sanitize_text( msg ),
                                                                  messagetype='error' ) )
            # See if we have any associated templates
            info_association = ldda.get_info_association()
            if info_association:
                template = info_association.template
                # See if we have any field contents
                info = info_association.info
                if info:
                    widgets = get_form_widgets( trans, template, info.content )
                else:
                    widgets = get_form_widgets( trans, template )
            else:
                widgets = []
            if action == 'permissions':
                if params.get( 'update_roles_button', False ):
                    permissions = {}
                    accessible = False
                    for k, v in trans.app.model.Dataset.permitted_actions.items():
                        # TODO: need to handle case where a user has the DATASET_MANAGE_PERMISSIONS permission, but not
                        # the DATASET_ACCESS permission, making the former useless.  Need to display a warning message.
                        in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                        # At least 1 user must have every role associated with this dataset, or the dataset is inaccessible
                        if v == trans.app.security_agent.permitted_actions.DATASET_ACCESS:
                            if len( in_roles ) > 1:
                                # Get the set of all users that are being associated with the dataset
                                in_roles_set = set()
                                for role in in_roles:
                                    in_roles_set.add( role )
                                users_set = set()
                                for role in in_roles:
                                    for ura in role.users:
                                        users_set.add( ura.user )
                                # Make sure that at least 1 user has every role being associated with the dataset
                                for user in users_set:
                                    user_roles_set = set()
                                    for ura in user.roles:
                                        user_roles_set.add( ura.role )
                                    if in_roles_set.issubset( user_roles_set ):
                                        accessible = True
                                        break
                            else:
                                accessible = True
                        if not accessible and v == trans.app.security_agent.permitted_actions.DATASET_ACCESS:
                            # Don't set the permissions for DATASET_ACCESS if inaccessbile, but set all other permissions
                            # TODO: keep access permissions as they originally were, rather than automatically making public
                            permissions[ trans.app.security_agent.get_action( v.action ) ] = []
                        else:
                            permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                    # Set the DATASET permissions on the Dataset
                    trans.app.security_agent.set_all_dataset_permissions( ldda.dataset, permissions )
                    ldda.dataset.refresh()
                    permissions = {}
                    for k, v in trans.app.model.Library.permitted_actions.items():
                        in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                        permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                    # Set the LIBRARY permissions on the LibraryDataset
                    # NOTE: the LibraryDataset and LibraryDatasetDatasetAssociation will be set with the same permissions
                    trans.app.security_agent.set_all_library_permissions( ldda.library_dataset, permissions )
                    ldda.library_dataset.refresh()
                    # Set the LIBRARY permissions on the LibraryDatasetDatasetAssociation
                    trans.app.security_agent.set_all_library_permissions( ldda, permissions )
                    ldda.refresh()
                    if not accessible:
                        msg = "At least 1 user must have every role associated with accessing dataset '%s'. " % ldda.name
                        msg += "The roles you attempted to associate for access would make this dataset inaccessible by everyone, "
                        msg += "so access permissions were not set.  All other permissions were updated for the dataset."
                        messagetype = 'error'
                    else:
                        msg = "Permissions updated for dataset '%s'" % ldda.name
                return trans.fill_template( '/admin/library/ldda_permissions.mako',
                                            ldda=ldda,
                                            library_id=library_id,
                                            msg=msg,
                                            messagetype=messagetype )
            elif action == 'info':
                return trans.fill_template( '/admin/library/ldda_info.mako',
                                            ldda=ldda,
                                            library_id=library_id,
                                            deleted=deleted,
                                            show_deleted=show_deleted,
                                            widgets=widgets,
                                            msg=msg,
                                            messagetype=messagetype )
            elif action == 'edit_info':
                if params.get( 'change', False ):
                    # The user clicked the Save button on the 'Change data type' form
                    if ldda.datatype.allow_datatype_change and trans.app.datatypes_registry.get_datatype_by_extension( params.datatype ).allow_datatype_change:
                        trans.app.datatypes_registry.change_datatype( ldda, params.datatype )
                        trans.app.model.flush()
                        msg = "Data type changed for library dataset '%s'" % ldda.name
                        return trans.fill_template( "/admin/library/ldda_edit_info.mako", 
                                                    ldda=ldda,
                                                    library_id=library_id,
                                                    datatypes=ldatatypes,
                                                    widgets=widgets,
                                                    msg=msg,
                                                    messagetype=messagetype )
                    else:
                        return trans.show_error_message( "You are unable to change datatypes in this manner. Changing %s to %s is not allowed." % ( ldda.extension, params.datatype ) )
                elif params.get( 'save', False ):
                    # The user clicked the Save button on the 'Edit Attributes' form
                    old_name = ldda.name
                    new_name = util.restore_text( params.get( 'name', '' ) )
                    new_info = util.restore_text( params.get( 'info', '' ) )
                    new_message = util.restore_text( params.get( 'message', '' ) )
                    if not new_name:
                        msg = 'Enter a valid name'
                        messagetype = 'error'
                    else:
                        ldda.name = new_name
                        ldda.info = new_info
                        ldda.message = new_message
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
                        msg = 'Attributes updated for library dataset %s' % ldda.name
                        messagetype = 'done'
                    return trans.fill_template( "/admin/library/ldda_edit_info.mako", 
                                                ldda=ldda,
                                                library_id=library_id,
                                                datatypes=ldatatypes,
                                                widgets=widgets,
                                                msg=msg,
                                                messagetype=messagetype )
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
                    msg = 'Attributes updated for library dataset %s' % ldda.name
                    return trans.fill_template( "/admin/library/ldda_edit_info.mako", 
                                                ldda=ldda,
                                                library_id=library_id,
                                                datatypes=ldatatypes,
                                                widgets=widgets,
                                                msg=msg,
                                                messagetype=messagetype )
                elif params.get( 'delete', False ):
                    ldda.deleted = True
                    ldda.flush()
                    msg = 'Dataset %s has been removed from this library' % ldda.name
                    return trans.fill_template( "/admin/library/ldda_edit_info.mako", 
                                                ldda=ldda,
                                                library_id=library_id,
                                                datatypes=ldatatypes,
                                                widgets=widgets,
                                                msg=msg,
                                                messagetype=messagetype )
                ldda.datatype.before_edit( ldda )
                if "dbkey" in ldda.datatype.metadata_spec and not ldda.metadata.dbkey:
                    # Copy dbkey into metadata, for backwards compatability
                    # This looks like it does nothing, but getting the dbkey
                    # returns the metadata dbkey unless it is None, in which
                    # case it resorts to the old dbkey.  Setting the dbkey
                    # sets it properly in the metadata
                    ldda.metadata.dbkey = ldda.dbkey
                return trans.fill_template( "/admin/library/ldda_edit_info.mako", 
                                            ldda=ldda,
                                            library_id=library_id,
                                            datatypes=ldatatypes,
                                            widgets=widgets,
                                            msg=msg,
                                            messagetype=messagetype )
        elif ids:
            # Multiple ids specfied, display permission form, permissions will be updated for all simultaneously.
            lddas = []
            for id in [ int( id ) for id in ids ]:
                ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
                if ldda is None:
                    msg = 'You specified an invalid LibraryDatasetDatasetAssociation id: %s' %str( id )
                    trans.response.send_redirect( web.url_for( controller='admin',
                                                               action='browse_library',
                                                               id=library_id,
                                                               msg=util.sanitize_text( msg ),
                                                               messagetype='error' ) )
                lddas.append( ldda )
            if len( lddas ) < 2:
                msg = 'You must specify at least two datasets on which to modify permissions, ids you sent: %s' % str( ids )
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='browse_library',
                                                           id=library_id,
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='error' ) )
            if action == 'permissions':
                if params.get( 'update_roles_button', False ):
                    permissions = {}
                    accessible = False
                    for k, v in trans.app.model.Dataset.permitted_actions.items():
                        # TODO: need to handle case where a user has the DATASET_MANAGE_PERMISSIONS permission, but not
                        # the DATASET_ACCESS permission, making the former useless.  Need to display a warning message.
                        in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( params.get( k + '_in', [] ) ) ]
                        # At least 1 user must have every role associated with this dataset, or the dataset is inaccessible
                        if v == trans.app.security_agent.permitted_actions.DATASET_ACCESS:
                            if len( in_roles ) > 1:
                                # Get the set of all users that are being associated with the dataset
                                in_roles_set = set()
                                for role in in_roles:
                                    in_roles_set.add( role )
                                users_set = set()
                                for role in in_roles:
                                    for ura in role.users:
                                        users_set.add( ura.user )
                                # Make sure that at least 1 user has every role being associated with the dataset
                                for user in users_set:
                                    user_roles_set = set()
                                    for ura in user.roles:
                                        user_roles_set.add( ura.role )
                                    if in_roles_set.issubset( user_roles_set ):
                                        accessible = True
                                        break
                            else:
                                accessible = True
                        if not accessible and v == trans.app.security_agent.permitted_actions.DATASET_ACCESS:
                            # Don't set the permissions for DATASET_ACCESS if inaccessbile, but set all other permissions
                            # TODO: keep access permissions as they originally were, rather than automatically making public
                            permissions[ trans.app.security_agent.get_action( v.action ) ] = []
                        else:
                            permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                    for ldda in lddas:
                        # Set the DATASET permissions on the Dataset
                        trans.app.security_agent.set_all_dataset_permissions( ldda.dataset, permissions )
                        ldda.dataset.refresh()
                    permissions = {}
                    for k, v in trans.app.model.Library.permitted_actions.items():
                        in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( kwd.get( k + '_in', [] ) ) ]
                        permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                    for ldda in lddas:
                        # Set the LIBRARY permissions on the LibraryDataset
                        # NOTE: the LibraryDataset and LibraryDatasetDatasetAssociation will be set with the same permissions
                        trans.app.security_agent.set_all_library_permissions( ldda.library_dataset, permissions )
                        ldda.library_dataset.refresh()
                        # Set the LIBRARY permissions on the LibraryDatasetDatasetAssociation
                        trans.app.security_agent.set_all_library_permissions( ldda, permissions )
                        ldda.refresh()
                    if not accessible:
                        msg = "At least 1 user must have every role associated with accessing these %d datasets. " % len( lddas )
                        msg += "The roles you attempted to associate for access would make these datasets inaccessible by everyone, "
                        msg += "so access permissions were not set.  All other permissions were updated for the datasets."
                        messagetype = 'error'
                    else:
                        msg = "Permissions have been updated on %d datasets" % len( lddas )
                    return trans.fill_template( "/admin/library/ldda_permissions.mako",
                                                ldda=lddas,
                                                library_id=library_id,
                                                msg=msg,
                                                messagetype=messagetype )
                # Ensure that the permissions across all library items are identical, otherwise we can't update them together.
                check_list = []
                for ldda in lddas:
                    permissions = []
                    # Check the library level permissions - the permissions on the LibraryDatasetDatasetAssociation
                    # will always be the same as the permissions on the associated LibraryDataset, so we only need to
                    # check one Library object
                    for library_permission in trans.app.security_agent.get_library_dataset_permissions( ldda.library_dataset ):
                        if library_permission.action not in permissions:
                            permissions.append( library_permission.action )
                    for dataset_permission in trans.app.security_agent.get_dataset_permissions( ldda.dataset ):
                        if dataset_permission.action not in permissions:
                            permissions.append( dataset_permission.action )
                    permissions.sort()
                    if not check_list:
                        check_list = permissions
                    if permissions != check_list:
                        msg = 'The datasets you selected do not have identical permissions, so they can not be updated together'
                        trans.response.send_redirect( web.url_for( controller='admin',
                                                                   action='browse_library',
                                                                   id=library_id,
                                                                   msg=util.sanitize_text( msg ),
                                                                   messagetype='error' ) )
                return trans.fill_template( "/admin/library/ldda_permissions.mako",
                                            ldda=lddas,
                                            library_id=library_id,
                                            msg=msg,
                                            messagetype=messagetype )
    @web.expose
    @web.require_admin
    def add_history_datasets_to_library( self, trans, library_id, folder_id, hda_ids='', **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        try:
            folder = trans.app.model.LibraryFolder.get( int( folder_id ) )
        except:
            msg = "Invalid folder id: %s" % str( folder_id )
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        replace_id = params.get( 'replace_id', None )
        if replace_id:
            replace_dataset = trans.app.model.LibraryDataset.get( replace_id )
        else:
            replace_dataset = None
        # See if the current history is empty
        history = trans.get_history()
        history.refresh()
        if not history.active_datasets:
            msg = 'Your current history is empty'
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        if params.get( 'add_history_datasets_to_library_button', False ):
            hda_ids = util.listify( hda_ids )
            if hda_ids:
                dataset_names = []
                created_ldda_ids = ''
                for hda_id in hda_ids:
                    hda = trans.app.model.HistoryDatasetAssociation.get( hda_id )
                    if hda:
                        ldda = hda.to_library_dataset_dataset_association( target_folder=folder, replace_dataset=replace_dataset )
                        created_ldda_ids = '%s,%s' % ( created_ldda_ids, str( ldda.id ) )
                        dataset_names.append( ldda.name )
                        if not replace_dataset:
                            # If replace_dataset is None, the Library level permissions will be taken from the folder and applied to the new 
                            # LDDA and LibraryDataset.
                            trans.app.security_agent.copy_library_permissions( folder, ldda )
                            trans.app.security_agent.copy_library_permissions( folder, ldda.library_dataset )
                        # Permissions must be the same on the LibraryDatasetDatasetAssociation and the associated LibraryDataset
                        trans.app.security_agent.copy_library_permissions( ldda.library_dataset, ldda )
                    else:
                        msg = "The requested HistoryDatasetAssociation id %s is invalid" % str( hda_id )
                        return trans.response.send_redirect( web.url_for( controller='admin',
                                                                          action='browse_library',
                                                                          id=library_id,
                                                                          msg=util.sanitize_text( msg ),
                                                                          messagetype='error' ) )
                if created_ldda_ids:
                    created_ldda_ids = created_ldda_ids.lstrip( ',' )
                    ldda_id_list = created_ldda_ids.split( ',' )
                    total_added = len( ldda_id_list )
                    if replace_dataset:
                        msg = "Added %d dataset versions to the library dataset '%s' in the folder '%s'." % ( total_added, replace_dataset.name, folder.name )
                    else:
                        if not folder.parent:
                            # Libraries have the same name as their root_folder
                            msg = "Added %d datasets to the library '%s' ( each is selected ).  " % ( total_added, folder.name )
                        else:
                            msg = "Added %d datasets to the folder '%s' ( each is selected ).  " % ( total_added, folder.name )
                        msg += "Click the Go button at the bottom of this page to edit the permissions on these datasets if necessary."
                    return trans.response.send_redirect( web.url_for( controller='admin',
                                                                      action='browse_library',
                                                                      id=library_id,
                                                                      created_ldda_ids=created_ldda_ids,
                                                                      msg=util.sanitize_text( msg ),
                                                                      messagetype='done' ) )
            else:
                msg = 'Select at least one dataset from the list of active datasets in your current history'
                messagetype = 'error'
                last_used_build = folder.genome_build
                upload_option = params.get( 'upload_option', 'import_from_history' )
                # Send list of data formats to the form so the "extension" select list can be populated dynamically
                file_formats = trans.app.datatypes_registry.upload_file_formats
                # Send list of genome builds to the form so the "dbkey" select list can be populated dynamically
                def get_dbkey_options( last_used_build ):
                    for dbkey, build_name in util.dbnames:
                        yield build_name, dbkey, ( dbkey==last_used_build )
                dbkeys = get_dbkey_options( last_used_build )
                # Send list of roles to the form so the dataset can be associated with 1 or more of them.
                roles = trans.app.model.Role.filter( trans.app.model.Role.table.c.deleted==False ).order_by( trans.app.model.Role.c.name ).all()
                return trans.fill_template( "/admin/library/new_dataset.mako",
                                            upload_option=upload_option,
                                            library_id=library_id,
                                            folder_id=folder_id,
                                            replace_id=replace_id,
                                            file_formats=file_formats,
                                            dbkeys=dbkeys,
                                            last_used_build=last_used_build,
                                            roles=roles,
                                            history=history,
                                            widgets=widgets,
                                            msg=msg,
                                            messagetype=messagetype )
    @web.expose
    @web.require_admin
    def info_template( self, trans, library_id, id=None, folder_id=None, ldda_id=None, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if id:
            library_item = trans.app.model.FormDefinition.get( int( id ) )
            library_item_desc = 'information template'
            response_action = 'info_template'
            response_id = id
        elif folder_id:
            library_item = trans.app.model.LibraryFolder.get( int( folder_id ) )
            library_item_desc = 'folder'
            response_action = 'folder'
            response_id = folder_id
        elif ldda_id:
            library_item = trans.app.model.LibraryDatasetDatasetAssociation.get( int( ldda_id ) )
            library_item_desc = 'library dataset'
            response_action = 'library_dataset_dataset_association'
            response_id = ldda_id
        else:
            library_item = trans.app.model.Library.get( int( library_id ) )
            library_item_desc = 'library'
            response_action = 'browse_library'
            response_id = library_id
        forms = get_all_forms( trans, filter=dict(deleted=False) )
        if not forms:
            msg = "There are no forms on which to base the template, so create a form and "
            msg += "try again to add the information template to the %s." % library_item_desc
            trans.response.send_redirect( web.url_for( controller='forms',
                                                       action='new',
                                                       new=True,
                                                       msg=msg,
                                                       messagetype='done' ) )
        if params.get( 'add', False ):
            if params.get( 'add_info_template_button', False ):
                form = trans.app.model.FormDefinition.get( int( kwd[ 'form_id' ] ) )
                #fields = list( copy.deepcopy( form.fields ) )
                form_values = trans.app.model.FormValues( form, [] )
                form_values.flush()
                if folder_id:
                    assoc = trans.app.model.LibraryFolderInfoAssociation( library_item, form, form_values )
                elif ldda_id:
                    assoc = trans.app.model.LibraryDatasetDatasetInfoAssociation( library_item, form, form_values )
                else:
                    assoc = trans.app.model.LibraryInfoAssociation( library_item, form, form_values )
                assoc.flush()
                msg = 'An information template based on the form "%s" has been added to this %s.' % ( form.name, library_item_desc )
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action=response_action,
                                                           id=response_id,
                                                           msg=msg,
                                                           message_type='done' ) )
            return trans.fill_template( '/admin/library/select_info_template.mako',
                                        library_item_name=library_item.name,
                                        library_item_desc=library_item_desc,
                                        library_id=library_id,
                                        folder_id=folder_id,
                                        ldda_id=ldda_id,
                                        forms=forms,
                                        msg=msg,
                                        messagetype=messagetype )
    @web.expose
    @web.require_admin
    def edit_template_info( self, trans, library_id, num_widgets, library_item_id=None, library_item_type=None, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        folder_id = None
        if library_item_type == 'library':
            library_item = trans.app.model.Library.get( library_item_id )
        elif library_item_type == 'library_dataset':
            library_item = trans.app.model.LibraryDataset.get( library_item_id )
        elif library_item_type == 'folder':
            library_item = trans.app.model.LibraryFolder.get( library_item_id )
        elif library_item_type == 'library_dataset_dataset_association':
            library_item = trans.app.model.LibraryDatasetDatasetAssociation.get( library_item_id )
            # This response_action method requires a folder_id
            folder_id = library_item.library_dataset.folder.id
        else:
            msg = "Invalid library item type ( %s ) specified, id ( %s )" % ( str( library_item_type ), str( library_item_id ) )
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
        # Save updated template field contents
        field_contents = []
        for index in range( int( num_widgets ) ):
            field_contents.append( util.restore_text( params.get( 'field_%i' % ( index ), ''  ) ) )
        if field_contents:
            # Since information templates are inherited, the template fields can be displayed on the information
            # page for a folder or library dataset when it has no info_association object.  If the user has added
            # field contents on an inherited template via a parent's info_association, we'll need to create a new
            # form_values and info_association for the current object.
            info_association = library_item.get_info_association( restrict=True )
            if info_association:
                template = info_association.template
                info = info_association.info
                form_values = trans.app.model.FormValues.get( info.id )
                # Update existing content only if it has changed
                if form_values.content != field_contents:
                    form_values.content = field_contents
                    form_values.flush()
            else:
                # Inherit the next available info_association so we can get the template
                info_association = library_item.get_info_association()
                template = info_association.template
                # Create a new FormValues object
                form_values = trans.app.model.FormValues( template, field_contents )
                form_values.flush()
                # Create a new info_association between the current library item and form_values
                if library_item_type == 'folder':
                    info_association = trans.app.model.LibraryFolderInfoAssociation( library_item, template, form_values )
                    info_association.flush()
                elif library_item_type == 'library_dataset_dataset_association':
                    info_association = trans.app.model.LibraryDatasetDatasetInfoAssociation( library_item, template, form_values )
                    info_association.flush()
        msg = 'The information has been updated.'
        return trans.response.send_redirect( web.url_for( controller='admin',
                                                          action=library_item_type,
                                                          id=library_item.id,
                                                          library_id=library_id,
                                                          folder_id=folder_id,
                                                          edit_info=True,
                                                          msg=util.sanitize_text( msg ),
                                                          messagetype='done' ) )
    @web.expose
    @web.require_admin
    def download_dataset_from_folder(self, trans, id, library_id=None, **kwd):
        """Catches the dataset id and displays file contents as directed"""
        # id must refer to a LibraryDatasetDatasetAssociation object
        ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
        if not ldda.dataset:
            msg = 'Invalid LibraryDatasetDatasetAssociation id %s received for file downlaod' % str( id )
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
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
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='browse_library',
                                                              id=library_id,
                                                              msg=util.sanitize_text( msg ),
                                                              messagetype='error' ) )
    @web.expose
    @web.require_admin
    def datasets( self, trans, library_id, **kwd ):
        # This method is used by the select list labeled "Perform action on selected datasets"
        # on the admin library browser.
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        if params.get( 'action_on_datasets_button', False ):
            if not params.ldda_ids:
                msg = "At least one dataset must be selected for %s" % params.action
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='browse_library',
                                                           id=library_id,
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='error' ) )
            ldda_ids = util.listify( params.ldda_ids )
            if params.action == 'edit':
                # We need the folder containing the LibraryDatasetDatasetAssociation(s)
                ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( ldda_ids[0] )
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='library_dataset_dataset_association',
                                                           library_id=library_id,
                                                           folder_id=ldda.library_dataset.folder.id,
                                                           id=",".join( ldda_ids ),
                                                           permissions=True,
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype=messagetype ) )
            elif params.action == 'delete':
                for id in ldda_ids:
                    ldda = trans.app.model.LibraryDatasetDatasetAssociation.get( id )
                    ldda.deleted = True
                    ldda.flush()
                msg = "The selected datasets have been removed from this library"
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='browse_library',
                                                           id=library_id,
                                                           show_deleted=False,
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='done' ) )
            else:
                msg = "Action %s is not yet implemented" % str( params.action )
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='browse_library',
                                                           id=library_id,
                                                           msg=util.sanitize_text( msg ),
                                                           messagetype='error' ) )
        else:
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='browse_library',
                                                           id=library_id,
                                                       msg=util.sanitize_text( msg ),
                                                       messagetype=messagetype ) )
    @web.expose
    @web.require_admin
    def delete_library_item( self, trans, library_id, library_item_id, library_item_type ):
        # This action will handle deleting all types of library items.  State is saved for libraries and
        # folders ( i.e., if undeleted, the state of contents of the library or folder will remain, so previously
        # deleted / purged contents will have the same state ).  When a library or folder has been deleted for
        # the amount of time defined in the cleanup_datasets.py script, the library or folder and all of its
        # contents will be purged.  The association between this method and the cleanup_datasets.py script
        # enables clean maintenance of libraries and library dataset disk files.  This is also why the following
        # 3 objects, and not any of the associations ( the cleanup_datasets.py scipot handles everything else ).
        library_item_types = { 'library': trans.app.model.Library,
                               'folder': trans.app.model.LibraryFolder,
                               'library_dataset': trans.app.model.LibraryDataset }
        if library_item_type not in library_item_types:
            msg = 'Bad library_item_type specified: %s' % str( library_item_type )
            messagetype = 'error'
        else:
            if library_item_type == 'library_dataset':
                library_item_desc = 'Dataset'
            else:
                library_item_desc = library_item_type.capitalize()
            library_item = library_item_types[ library_item_type ].get( int( library_item_id ) )
            library_item.deleted = True
            library_item.flush()
            msg = util.sanitize_text( "%s '%s' has been marked deleted" % ( library_item_desc, library_item.name ) )
            messagetype = 'done'
        if library_item_type == 'library':
            return self.browse_libraries( trans, msg=msg, messagetype=messagetype )
        else:
            return self.browse_library( trans, id=library_id , msg=msg, messagetype=messagetype )
    @web.expose
    @web.require_admin
    def undelete_library_item( self, trans, library_id, library_item_id, library_item_type ):
        # This action will handle undeleting all types of library items
        library_item_types = { 'library': trans.app.model.Library,
                               'folder': trans.app.model.LibraryFolder,
                               'library_dataset': trans.app.model.LibraryDataset }
        if library_item_type not in library_item_types:
            msg = 'Bad library_item_type specified: %s' % str( library_item_type )
            messagetype = 'error'
        else:
            if library_item_type == 'library_dataset':
                library_item_desc = 'Dataset'
            else:
                library_item_desc = library_item_type.capitalize()
            library_item = library_item_types[ library_item_type ].get( int( library_item_id ) )
            if library_item.purged:
                msg = '%s %s has been purged, so it cannot be undeleted' % ( library_item_desc, library_item.name )
                messagetype = 'error'
            else:
                library_item.deleted = False
                library_item.flush()
                msg = util.sanitize_text( "%s '%s' has been marked undeleted" % ( library_item_desc, library_item.name ) )
                messagetype = 'done'
        if library_item_type == 'library':
            return self.browse_libraries( trans, msg=msg, messagetype=messagetype )
        else:
            return self.browse_library( trans, id=library_id , msg=msg, messagetype=messagetype )
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

    @web.expose
    @web.require_admin
    def jobs( self, trans, stop = [], stop_msg = None, cutoff = 180, **kwd ):
        deleted = []
        msg = None
        messagetype = None
        job_ids = util.listify( stop )
        if job_ids and stop_msg in [ None, '' ]:
            msg = 'Please enter an error message to display to the user describing why the job was terminated'
            messagetype = 'error'
        elif job_ids:
            if stop_msg[-1] not in string.punctuation:
                stop_msg += '.'
            for job_id in job_ids:
                trans.app.job_manager.job_stop_queue.put( job_id, error_msg="This job was stopped by an administrator: %s  For more information or help" % stop_msg )
                deleted.append( str( job_id ) )
        if deleted:
            msg = 'Queued job'
            if len( deleted ) > 1:
                msg += 's'
            msg += ' for deletion: '
            msg += ', '.join( deleted )
            messagetype = 'done'
        cutoff_time = datetime.utcnow() - timedelta( seconds=int( cutoff ) )
        jobs = trans.app.model.Job.filter(
            and_( trans.app.model.Job.table.c.update_time < cutoff_time,
                or_( trans.app.model.Job.c.state == trans.app.model.Job.states.NEW,
                     trans.app.model.Job.c.state == trans.app.model.Job.states.QUEUED,
                     trans.app.model.Job.c.state == trans.app.model.Job.states.RUNNING,
                     trans.app.model.Job.c.state == trans.app.model.Job.states.UPLOAD,
                )
            )
        ).order_by(trans.app.model.Job.c.update_time.desc()).all()
        last_updated = {}
        for job in jobs:
            delta = datetime.utcnow() - job.update_time
            if delta > timedelta( minutes=60 ):
                last_updated[job.id] = '%s hours' % int( delta.seconds / 60 / 60 )
            else:
                last_updated[job.id] = '%s minutes' % int( delta.seconds / 60 )
        return trans.fill_template( '/admin/jobs.mako', jobs = jobs, last_updated = last_updated, cutoff = cutoff, msg = msg, messagetype = messagetype )
    @web.expose
    @web.require_admin
    def manage_request_types( self, trans, **kwd ):       
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        show_filter = util.restore_text( params.get( 'show_filter', 'Active'  ) )
        forms = get_all_forms(trans, all_versions=True)
        request_types_list = trans.app.model.RequestType.query().all()
        if show_filter == 'All':
            request_types = request_types_list
        elif show_filter == 'Deleted':
            request_types = [rt for rt in request_types_list if rt.deleted]
        else:
            request_types = [rt for rt in request_types_list if not rt.deleted]
        return trans.fill_template( '/admin/requests/manage_request_types.mako', 
                                    request_types=request_types,
                                    forms=forms,
                                    show_filter=show_filter,
                                    msg=msg,
                                    messagetype=messagetype )
    @web.expose
    @web.require_admin
    def request_type( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )   
        if params.get( 'create', False ):
            return trans.fill_template( '/admin/requests/create_request_type.mako', 
                                        forms=get_all_forms( trans, 
                                                             filter=dict(deleted=False) ),
                                        msg=msg,
                                        messagetype=messagetype)
        elif params.get( 'define_states_button', False ):
            return trans.fill_template( '/admin/requests/add_states.mako',
                                        request_type_name=util.restore_text( params.name ),
                                        desc=util.restore_text( params.description ),
                                        num_states=int(util.restore_text( params.num_states )),
                                        request_form_id=int(util.restore_text( params.request_form_id )),
                                        sample_form_id=int(util.restore_text( params.sample_form_id )),
                                        msg=msg,
                                        messagetype=messagetype)            
        elif params.get( 'save_request_type', False ):
            st, msg = self._save_request_type(trans, **kwd)
            if not st:
                return trans.fill_template( '/admin/requests/create_request_type.mako', 
                                            forms=get_all_forms( trans ),
                                            msg=msg,
                                            messagetype='error')
            return trans.response.send_redirect( web.url_for( controller='admin',
                                                              action='manage_request_types',
                                                              msg='Request type <b>%s</b> has been created' % st.name,
                                                              messagetype='done') )
        elif params.get('view', False):
            rt = trans.app.model.RequestType.get(int(util.restore_text( params.id )))
            ss_list = trans.app.model.SampleState.filter(trans.app.model.SampleState.table.c.request_type_id == rt.id).all()
            return trans.fill_template( '/admin/requests/view_request_type.mako', 
                                        request_type=rt,
                                        forms=get_all_forms( trans ),
                                        states_list=ss_list,
                                        deleted=False,
                                        show_deleted=False,
                                        msg=msg,
                                        messagetype=messagetype )

    def _save_request_type(self, trans, **kwd):
        params = util.Params( kwd )
        num_states = int( util.restore_text( params.get( 'num_states', 0 ) ))
        proceed = True
        for i in range( num_states ):
            if not util.restore_text( params.get( 'state_name_%i' % i, None ) ):
                proceed = False
                break
        if not proceed:
            msg = "All the state name(s) must be completed."
            return None, msg
        rt = trans.app.model.RequestType() 
        rt.name = util.restore_text( params.name ) 
        rt.desc = util.restore_text( params.description ) or ""
        rt.request_form = trans.app.model.FormDefinition.get(int( params.request_form_id ))
        rt.sample_form = trans.app.model.FormDefinition.get(int( params.sample_form_id ))
        rt.flush()
        # set sample states
        ss_list = trans.app.model.SampleState.filter(trans.app.model.SampleState.table.c.request_type_id == rt.id).all()
        for ss in ss_list:
            ss.delete()
            ss.flush()
        for i in range( num_states ):
            name = util.restore_text( params.get( 'state_name_%i' % i, None ))
            desc = util.restore_text( params.get( 'state_desc_%i' % i, None ))
            ss = trans.app.model.SampleState(name, desc, rt) 
            ss.flush()
        msg = "The new request type named '%s' with %s state(s) has been created" % (rt.name, num_states)
        return rt, msg

    @web.expose
    @web.require_admin
    def delete_request_type( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        rt = trans.app.model.RequestType.get(int(util.restore_text( params.request_type_id )))
        rt.deleted = True
        rt.flush()
        return trans.response.send_redirect( web.url_for( controller='admin',
                                                          action='manage_request_types',
                                                          msg='Request type <b>%s</b> has been deleted' % rt.name,
                                                          messagetype='done') )
        
    @web.expose
    @web.require_admin
    def undelete_request_type( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = util.restore_text( params.get( 'msg', ''  ) )
        messagetype = params.get( 'messagetype', 'done' )
        rt = trans.app.model.RequestType.get(int(util.restore_text( params.request_type_id )))
        rt.deleted = False
        rt.flush()
        return trans.response.send_redirect( web.url_for( controller='admin',
                                                          action='manage_request_types',
                                                          msg='Request type <b>%s</b> has been undeleted' % rt.name,
                                                          messagetype='done') )
