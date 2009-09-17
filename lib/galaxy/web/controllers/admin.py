import string, sys
from datetime import datetime, timedelta
from galaxy import util, datatypes
from galaxy.web.base.controller import *
from galaxy.model.orm import *
from galaxy.web.controllers.forms import get_all_forms, get_form_widgets
from galaxy.web.framework.helpers import time_ago, iff, grids
import logging
log = logging.getLogger( __name__ )

class UserListGrid( grids.Grid ):
    class EmailColumn( grids.GridColumn ):
        def get_value( self, trans, grid, user ):
            return user.email
    class UserNameColumn( grids.GridColumn ):
        def get_value( self, trans, grid, user ):
            if user.username:
                return user.username
            return 'not set'
    class GroupsColumn( grids.GridColumn ):
        def get_value( self, trans, grid, user ):
            if user.groups:
                return len( user.groups )
            return 0
    class RolesColumn( grids.GridColumn ):
        def get_value( self, trans, grid, user ):
            if user.roles:
                return len( user.roles )
            return 0
    class ExternalColumn( grids.GridColumn ):
        def get_value( self, trans, grid, user ):
            if user.external:
                return 'yes'
            return 'no'
    class LastLoginColumn( grids.GridColumn ):
        def get_value( self, trans, grid, user ):
            if user.galaxy_sessions:
                return self.format( user.galaxy_sessions[ 0 ].update_time )
            return 'never'
    # Grid definition
    title = "Users"
    model_class = model.User
    template='/admin/user/grid.mako'
    columns = [
        EmailColumn( "Email", link=( lambda item: dict( operation="user", id=item.id ) ), attach_popup=True ),
        UserNameColumn( "User Name", attach_popup=False ),
        GroupsColumn( "Groups", attach_popup=False ),
        RolesColumn( "Roles", attach_popup=False ),
        ExternalColumn( "External", attach_popup=False ),
        LastLoginColumn( "Last Login", format=time_ago ),
        # Valid for filtering but invisible
        grids.GridColumn( "Deleted", key="deleted", visible=False )
    ]
    operations = [
        grids.GridOperation( "reset_password", condition=( lambda item: not item.deleted ), allow_multiple=True )
    ]
    #TODO: enhance to account for trans.app.config.allow_user_deletion here so that we can eliminate these operations if 
    # the setting is False
    operations.append( grids.GridOperation( "delete", condition=( lambda item: not item.deleted ), allow_multiple=True ) )
    operations.append( grids.GridOperation( "undelete", condition=( lambda item: item.deleted ), allow_multiple=True ) )
    operations.append( grids.GridOperation( "purge", condition=( lambda item: item.deleted ), allow_multiple=True ) )
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    default_filter = dict( deleted=False )
    def get_current_item( self, trans ):
        return trans.user
    def build_initial_query( self, session ):
        return session.query( self.model_class )
    def apply_default_filter( self, trans, query, **kwargs ):
        email_filter = kwargs.get( "email_filter", None )
        if email_filter:
            if email_filter == 'all':
                return query
            else:
                return query.filter( or_( trans.app.model.User.table.c.email.like( '%s' % email_filter.lower() + '%' ),
                                          trans.app.model.User.table.c.email.like( '%s' % email_filter.upper() + '%' ) ) )
        elif query.count() > 200:
            return query.filter( or_( trans.app.model.User.table.c.email.like( 'A%' ),
                                      trans.app.model.User.table.c.email.like( 'a%' ) ) )
        return query

class Admin( BaseController ):
    
    user_list_grid = UserListGrid()
    
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
    def create_new_user( self, trans, **kwargs ):
        email = ''
        password = ''
        confirm = ''
        subscribe = False
        email_filter = kwargs.get( 'email_filter', 'A' )
        if 'user_create_button' in kwargs:
            message = ''
            status = ''
            email = kwargs.get( 'email' , None )
            password = kwargs.get( 'password', None )
            confirm = kwargs.get( 'confirm', None )
            subscribe = kwargs.get( 'subscribe', None )
            if not email:
                message = 'Enter a valid email address'
            elif not password:
                message = 'Enter a valid password'
            elif not confirm:
                message = 'Confirm the password'
            elif len( email ) == 0 or "@" not in email or "." not in email:
                message = 'Enter a real email address'
            elif len( email) > 255:
                message = 'Email address exceeds maximum allowable length'
            elif trans.app.model.User.filter_by( email=email ).all():
                message = 'User with that email already exists'
            elif len( password ) < 6:
                message = 'Use a password of at least 6 characters'
            elif password != confirm:
                message = 'Passwords do not match'
            if message:
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='users',
                                                           email_filter=email_filter,
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            else:
                user = trans.app.model.User( email=email )
                user.set_password_cleartext( password )
                if trans.app.config.use_remote_user:
                    user.external = True
                user.flush()
                trans.app.security_agent.create_private_user_role( user )
                trans.app.security_agent.user_set_default_permissions( user, history=False, dataset=False )
                message = 'Created new user account (%s)' % user.email
                status = 'done'
                #subscribe user to email list
                if subscribe:
                    mail = os.popen( "%s -t" % trans.app.config.sendmail_path, 'w' )
                    mail.write( "To: %s\nFrom: %s\nSubject: Join Mailing List\n\nJoin Mailing list." % ( trans.app.config.mailing_join_addr, email ) )
                    if mail.close():
                        message + ". However, subscribing to the mailing list has failed."
                        status = 'error'
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='users',
                                                           email_filter=email_filter,
                                                           message=util.sanitize_text( message ),
                                                           status=status ) )
        return trans.fill_template( '/admin/user/create.mako',
                                    email_filter=email_filter,
                                    email=email,
                                    password=password,
                                    confirm=confirm,
                                    subscribe=subscribe )
    @web.expose
    @web.require_admin
    def reset_user_password( self, trans, **kwd ):
        id = kwd.get( 'id', None )
        if not id:
            message = "No user ids received for resetting passwords"
            trans.response.send_redirect( web.url_for( action='users', message=message, status='error' ) )
        ids = util.listify( id )
        if 'reset_user_password_button' in kwd:
            message = ''
            status = ''
            for user_id in ids:
                user = get_user( trans, user_id )
                password = kwd.get( 'password', None )
                confirm = kwd.get( 'confirm' , None )
                if len( password ) < 6:
                    message = "Please use a password of at least 6 characters"
                    status = 'error'
                    break
                elif password != confirm:
                    message = "Passwords do not match"
                    status = 'error'
                    break
                else:
                    user.set_password_cleartext( password )
                    user.flush()
            if not message and not status:
                message = "Passwords reset for %d users" % len( ids )
                status = 'done'
            trans.response.send_redirect( web.url_for( action='users',
                                                       message=util.sanitize_text( message ),
                                                       status=status ) )
        users = [ get_user( trans, user_id ) for user_id in ids ]
        if len( ids ) > 1:
            id=','.join( id )
        return trans.fill_template( '/admin/user/reset_password.mako',
                                    id=id,
                                    users=users,
                                    password='',
                                    confirm='' )
    @web.expose
    @web.require_admin
    def mark_user_deleted( self, trans, **kwd ):
        id = kwd.get( 'id', None )
        if not id:
            message = "No user ids received for deleting"
            trans.response.send_redirect( web.url_for( action='users', message=message, status='error' ) )
        ids = util.listify( id )
        for user_id in ids:
            user = get_user( trans, user_id )
            user.deleted = True
            user.flush()
        message = "Deleted %d users" % len( ids )
        trans.response.send_redirect( web.url_for( action='users', message=util.sanitize_text( message ), status='done' ) )
    @web.expose
    @web.require_admin
    def undelete_user( self, trans, **kwd ):
        id = kwd.get( 'id', None )
        if not id:
            message = "No user ids received for undeleting"
            trans.response.send_redirect( web.url_for( action='users', message=message, status='error' ) )
        ids = util.listify( id )
        count = 0
        for user_id in ids:
            user = get_user( trans, user_id )
            if user.deleted:
                user.deleted = False
                user.flush()
                count += 1
        message = "Undeleted %d users" % count
        trans.response.send_redirect( web.url_for( action='users',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )
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
        id = kwd.get( 'id', None )
        if not id:
            message = "No user ids received for purging"
            trans.response.send_redirect( web.url_for( action='users',
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        ids = util.listify( id )
        for user_id in ids:
            user = get_user( trans, user_id )
            if not user.deleted:
                # We should never reach here, but just in case there is a bug somewhere...
                message = "User '%s' has not been deleted, so it cannot be purged." % user.email
                trans.response.send_redirect( web.url_for( action='users',
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
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
        message = "Purged %d users" % len( ids )
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='users',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )
    @web.expose
    @web.require_admin
    def users( self, trans, **kwargs ):      
        if 'operation' in kwargs:
            operation = kwargs['operation'].lower()
            if operation == "user":
                return self.user( trans, **kwargs )
            if operation == "reset_password":
                return self.reset_user_password( trans, **kwargs )
            if operation == "delete":
                return self.mark_user_deleted( trans, **kwargs )
            if operation == "undelete":
                return self.undelete_user( trans, **kwargs )
            if operation == "purge":
                return self.purge_user( trans, **kwargs )
            if operation == "create":
                return self.create_new_user( trans, **kwargs )
        # Render the list view
        return self.user_list_grid( trans, **kwargs )
    @web.expose
    @web.require_admin
    def user( self, trans, **kwd ):
        user_id = kwd.get( 'id', None )
        message = ''
        status = ''
        if not user_id:
            message += "Invalid user id (%s) received" % str( user_id )
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='users',
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        user = get_user( trans, user_id )
        private_role = trans.app.security_agent.get_private_user_role( user )
        if kwd.get( 'user_roles_groups_edit_button', False ):
            # Make sure the user is not dis-associating himself from his private role
            out_roles = kwd.get( 'out_roles', [] )
            if out_roles:
                out_roles = [ trans.app.model.Role.get( x ) for x in util.listify( out_roles ) ]
            if private_role in out_roles:
                message += "You cannot eliminate a user's private role association.  "
                status = 'error'
            in_roles = kwd.get( 'in_roles', [] )
            if in_roles:
                in_roles = [ trans.app.model.Role.get( x ) for x in util.listify( in_roles ) ]
            out_groups = kwd.get( 'out_groups', [] )
            if out_groups:
                out_groups = [ trans.app.model.Group.get( x ) for x in util.listify( out_groups ) ]
            in_groups = kwd.get( 'in_groups', [] )
            if in_groups:
                in_groups = [ trans.app.model.Group.get( x ) for x in util.listify( in_groups ) ]
            if in_roles:
                trans.app.security_agent.set_entity_user_associations( users=[ user ], roles=in_roles, groups=in_groups )
                user.refresh()
                message += "User '%s' has been updated with %d associated roles and %d associated groups (private roles are not displayed)" % \
                    ( user.email, len( in_roles ), len( in_groups ) )
                trans.response.send_redirect( web.url_for( action='users',
                                                           message=util.sanitize_text( message ),
                                                           status='done' ) )
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
        for group in trans.app.model.Group.filter( trans.app.model.Group.table.c.deleted==False ) \
                                          .order_by( trans.app.model.Group.table.c.name ).all():
            if group in [ x.group for x in user.groups ]:
                in_groups.append( ( group.id, group.name ) )
            else:
                out_groups.append( ( group.id, group.name ) )
        message += "User '%s' is currently associated with %d roles and is a member of %d groups" % \
            ( user.email, len( in_roles ), len( in_groups ) )
        if not status:
            status = 'done'
        return trans.fill_template( '/admin/user/user.mako',
                                    user=user,
                                    in_roles=in_roles,
                                    out_roles=out_roles,
                                    in_groups=in_groups,
                                    out_groups=out_groups,
                                    msg=message,
                                    messagetype=status )
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

## ---- Utility methods -------------------------------------------------------
        
def get_user( trans, id ):
    """Get a User from the database by id."""
    # Load user from database
    id = trans.security.decode_id( id )
    user = trans.sa_session.query( model.User ).get( id )
    if not user:
        err+msg( "User not found" )
    return user
