import logging
import os
from datetime import datetime, timedelta
import six
from string import punctuation as PUNCTUATION

from sqlalchemy import and_, false, func, or_

import galaxy.queue_worker
from galaxy import util, web
from galaxy.util import inflector
from galaxy.web.form_builder import CheckboxField
from tool_shed.util import repository_util
from tool_shed.util.web_util import escape

log = logging.getLogger( __name__ )


class Admin( object ):
    # Override these
    user_list_grid = None
    role_list_grid = None
    group_list_grid = None
    quota_list_grid = None
    repository_list_grid = None
    tool_version_list_grid = None
    delete_operation = None
    undelete_operation = None
    purge_operation = None

    @web.expose
    @web.require_admin
    def index( self, trans, **kwd ):
        message = escape( kwd.get( 'message', ''  ) )
        status = kwd.get( 'status', 'done' )
        if trans.webapp.name == 'galaxy':
            is_repo_installed = trans.install_model.context.query( trans.install_model.ToolShedRepository ).first() is not None
            installing_repository_ids = repository_util.get_ids_of_tool_shed_repositories_being_installed( trans.app, as_string=True )
            return trans.fill_template( '/webapps/galaxy/admin/index.mako',
                                        is_repo_installed=is_repo_installed,
                                        installing_repository_ids=installing_repository_ids,
                                        message=message,
                                        status=status )
        else:
            return trans.fill_template( '/webapps/tool_shed/admin/index.mako',
                                        message=message,
                                        status=status )

    @web.expose
    @web.require_admin
    def center( self, trans, **kwd ):
        message = escape( kwd.get( 'message', ''  ) )
        status = kwd.get( 'status', 'done' )
        if trans.webapp.name == 'galaxy':
            is_repo_installed = trans.install_model.context.query( trans.install_model.ToolShedRepository ).first() is not None
            installing_repository_ids = repository_util.get_ids_of_tool_shed_repositories_being_installed( trans.app, as_string=True )
            return trans.fill_template( '/webapps/galaxy/admin/center.mako',
                                        is_repo_installed=is_repo_installed,
                                        installing_repository_ids=installing_repository_ids,
                                        message=message,
                                        status=status )
        else:
            return trans.fill_template( '/webapps/tool_shed/admin/center.mako',
                                        message=message,
                                        status=status )

    @web.expose
    @web.require_admin
    def package_tool( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        toolbox = self.app.toolbox
        tool_id = None
        if params.get( 'package_tool_button', False ):
            tool_id = params.get('tool_id', None)
            try:
                tool_tarball = trans.app.toolbox.package_tool( trans, tool_id )
                trans.response.set_content_type( 'application/x-gzip' )
                download_file = open( tool_tarball )
                os.unlink( tool_tarball )
                tarball_path, filename = os.path.split( tool_tarball )
                trans.response.headers[ "Content-Disposition" ] = 'attachment; filename="%s.tgz"' % ( tool_id )
                return download_file
            except Exception:
                return trans.fill_template( '/admin/package_tool.mako',
                                            tool_id=tool_id,
                                            toolbox=toolbox,
                                            message=message,
                                            status='error' )

    @web.expose
    @web.require_admin
    def reload_tool( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        toolbox = self.app.toolbox
        tool_id = None
        if params.get( 'reload_tool_button', False ):
            tool_id = kwd.get( 'tool_id', None )
            galaxy.queue_worker.send_control_task(trans.app, 'reload_tool', noop_self=True, kwargs={'tool_id': tool_id} )
            message, status = trans.app.toolbox.reload_tool_by_id( tool_id )
        return trans.fill_template( '/admin/reload_tool.mako',
                                    tool_id=tool_id,
                                    toolbox=toolbox,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def tool_versions( self, trans, **kwd ):
        if 'message' not in kwd or not kwd[ 'message' ]:
            kwd[ 'message' ] = 'Tool ids for tools that are currently loaded into the tool panel are highlighted in green (click to display).'
        return self.tool_version_list_grid( trans, **kwd )

    @web.expose
    @web.require_admin
    def roles( self, trans, **kwargs ):
        if 'operation' in kwargs:
            operation = kwargs[ 'operation' ].lower().replace( '+', ' ' )
            if operation == "roles":
                return self.role( trans, **kwargs )
            if operation == "create":
                return self.create_role( trans, **kwargs )
            if operation == "delete":
                return self.mark_role_deleted( trans, **kwargs )
            if operation == "undelete":
                return self.undelete_role( trans, **kwargs )
            if operation == "purge":
                return self.purge_role( trans, **kwargs )
            if operation == "manage users and groups":
                return self.manage_users_and_groups_for_role( trans, **kwargs )
            if operation == "manage role associations":
                # This is currently used only in the Tool Shed.
                return self.manage_role_associations( trans, **kwargs )
            if operation == "rename":
                return self.rename_role( trans, **kwargs )
        # Render the list view
        return self.role_list_grid( trans, **kwargs )

    @web.expose
    @web.require_admin
    def create_role( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        name = util.restore_text( params.get( 'name', '' ) )
        description = util.restore_text( params.get( 'description', '' ) )
        in_users = util.listify( params.get( 'in_users', [] ) )
        out_users = util.listify( params.get( 'out_users', [] ) )
        in_groups = util.listify( params.get( 'in_groups', [] ) )
        out_groups = util.listify( params.get( 'out_groups', [] ) )
        create_group_for_role = params.get( 'create_group_for_role', '' )
        create_group_for_role_checked = CheckboxField.is_checked( create_group_for_role )
        ok = True
        if params.get( 'create_role_button', False ):
            if not name or not description:
                message = "Enter a valid name and a description."
                status = 'error'
                ok = False
            elif trans.sa_session.query( trans.app.model.Role ).filter( trans.app.model.Role.table.c.name == name ).first():
                message = "Role names must be unique and a role with that name already exists, so choose another name."
                status = 'error'
                ok = False
            else:
                # Create the role
                role = trans.app.model.Role( name=name, description=description, type=trans.app.model.Role.types.ADMIN )
                trans.sa_session.add( role )
                # Create the UserRoleAssociations
                for user in [ trans.sa_session.query( trans.app.model.User ).get( x ) for x in in_users ]:
                    ura = trans.app.model.UserRoleAssociation( user, role )
                    trans.sa_session.add( ura )
                # Create the GroupRoleAssociations
                for group in [ trans.sa_session.query( trans.app.model.Group ).get( x ) for x in in_groups ]:
                    gra = trans.app.model.GroupRoleAssociation( group, role )
                    trans.sa_session.add( gra )
                if create_group_for_role_checked:
                    # Create the group
                    group = trans.app.model.Group( name=name )
                    trans.sa_session.add( group )
                    # Associate the group with the role
                    gra = trans.model.GroupRoleAssociation( group, role )
                    trans.sa_session.add( gra )
                    num_in_groups = len( in_groups ) + 1
                else:
                    num_in_groups = len( in_groups )
                trans.sa_session.flush()
                message = "Role '%s' has been created with %d associated users and %d associated groups.  " \
                    % ( role.name, len( in_users ), num_in_groups )
                if create_group_for_role_checked:
                    message += 'One of the groups associated with this role is the newly created group with the same name.'
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='roles',
                                                           message=util.sanitize_text( message ),
                                                           status='done' ) )
        if ok:
            for user in trans.sa_session.query( trans.app.model.User ) \
                                        .filter( trans.app.model.User.table.c.deleted == false() ) \
                                        .order_by( trans.app.model.User.table.c.email ):
                out_users.append( ( user.id, user.email ) )
            for group in trans.sa_session.query( trans.app.model.Group ) \
                                         .filter( trans.app.model.Group.table.c.deleted == false() ) \
                                         .order_by( trans.app.model.Group.table.c.name ):
                out_groups.append( ( group.id, group.name ) )
        return trans.fill_template( '/admin/dataset_security/role/role_create.mako',
                                    name=name,
                                    description=description,
                                    in_users=in_users,
                                    out_users=out_users,
                                    in_groups=in_groups,
                                    out_groups=out_groups,
                                    create_group_for_role_checked=create_group_for_role_checked,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def rename_role( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            message = "No role ids received for renaming"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       message=message,
                                                       status='error' ) )
        role = get_role( trans, id )
        if params.get( 'rename_role_button', False ):
            old_name = role.name
            new_name = util.restore_text( params.name )
            new_description = util.restore_text( params.description )
            if not new_name:
                message = 'Enter a valid name'
                status = 'error'
            else:
                existing_role = trans.sa_session.query( trans.app.model.Role ).filter( trans.app.model.Role.table.c.name == new_name ).first()
                if existing_role and existing_role.id != role.id:
                    message = 'A role with that name already exists'
                    status = 'error'
                else:
                    if not ( role.name == new_name and role.description == new_description ):
                        role.name = new_name
                        role.description = new_description
                        trans.sa_session.add( role )
                        trans.sa_session.flush()
                        message = "Role '%s' has been renamed to '%s'" % ( old_name, new_name )
                    return trans.response.send_redirect( web.url_for( controller='admin',
                                                                      action='roles',
                                                                      message=util.sanitize_text( message ),
                                                                      status='done' ) )
        return trans.fill_template( '/admin/dataset_security/role/role_rename.mako',
                                    role=role,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def manage_users_and_groups_for_role( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            message = "No role ids received for managing users and groups"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       message=message,
                                                       status='error' ) )
        role = get_role( trans, id )
        if params.get( 'role_members_edit_button', False ):
            in_users = [ trans.sa_session.query( trans.app.model.User ).get( x ) for x in util.listify( params.in_users ) ]
            if trans.webapp.name == 'galaxy':
                for ura in role.users:
                    user = trans.sa_session.query( trans.app.model.User ).get( ura.user_id )
                    if user not in in_users:
                        # Delete DefaultUserPermissions for previously associated users that have been removed from the role
                        for dup in user.default_permissions:
                            if role == dup.role:
                                trans.sa_session.delete( dup )
                        # Delete DefaultHistoryPermissions for previously associated users that have been removed from the role
                        for history in user.histories:
                            for dhp in history.default_permissions:
                                if role == dhp.role:
                                    trans.sa_session.delete( dhp )
                        trans.sa_session.flush()
            in_groups = [ trans.sa_session.query( trans.app.model.Group ).get( x ) for x in util.listify( params.in_groups ) ]
            trans.app.security_agent.set_entity_role_associations( roles=[ role ], users=in_users, groups=in_groups )
            trans.sa_session.refresh( role )
            message = "Role '%s' has been updated with %d associated users and %d associated groups" % ( role.name, len( in_users ), len( in_groups ) )
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       message=util.sanitize_text( message ),
                                                       status=status ) )
        in_users = []
        out_users = []
        in_groups = []
        out_groups = []
        for user in trans.sa_session.query( trans.app.model.User ) \
                                    .filter( trans.app.model.User.table.c.deleted == false() ) \
                                    .order_by( trans.app.model.User.table.c.email ):
            if user in [ x.user for x in role.users ]:
                in_users.append( ( user.id, user.email ) )
            else:
                out_users.append( ( user.id, user.email ) )
        for group in trans.sa_session.query( trans.app.model.Group ) \
                                     .filter( trans.app.model.Group.table.c.deleted == false() ) \
                                     .order_by( trans.app.model.Group.table.c.name ):
            if group in [ x.group for x in role.groups ]:
                in_groups.append( ( group.id, group.name ) )
            else:
                out_groups.append( ( group.id, group.name ) )
        library_dataset_actions = {}
        if trans.webapp.name == 'galaxy' and len(role.dataset_actions) < 25:
            # Build a list of tuples that are LibraryDatasetDatasetAssociationss followed by a list of actions
            # whose DatasetPermissions is associated with the Role
            # [ ( LibraryDatasetDatasetAssociation [ action, action ] ) ]
            for dp in role.dataset_actions:
                for ldda in trans.sa_session.query( trans.app.model.LibraryDatasetDatasetAssociation ) \
                                            .filter( trans.app.model.LibraryDatasetDatasetAssociation.dataset_id == dp.dataset_id ):
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
                    library = trans.sa_session.query( trans.app.model.Library ) \
                                              .filter( trans.app.model.Library.table.c.root_folder_id == folder.id ) \
                                              .first()
                    if library not in library_dataset_actions:
                        library_dataset_actions[ library ] = {}
                    try:
                        library_dataset_actions[ library ][ folder_path ].append( dp.action )
                    except:
                        library_dataset_actions[ library ][ folder_path ] = [ dp.action ]
        else:
            message = "Not showing associated datasets, there are too many."
            status = 'info'
        return trans.fill_template( '/admin/dataset_security/role/role.mako',
                                    role=role,
                                    in_users=in_users,
                                    out_users=out_users,
                                    in_groups=in_groups,
                                    out_groups=out_groups,
                                    library_dataset_actions=library_dataset_actions,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def mark_role_deleted( self, trans, **kwd ):
        id = kwd.get( 'id', None )
        if not id:
            message = "No role ids received for deleting"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Deleted %d roles: " % len( ids )
        for role_id in ids:
            role = get_role( trans, role_id )
            role.deleted = True
            trans.sa_session.add( role )
            trans.sa_session.flush()
            message += " %s " % role.name
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='roles',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    @web.expose
    @web.require_admin
    def undelete_role( self, trans, **kwd ):
        id = kwd.get( 'id', None )
        if not id:
            message = "No role ids received for undeleting"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        count = 0
        undeleted_roles = ""
        for role_id in ids:
            role = get_role( trans, role_id )
            if not role.deleted:
                message = "Role '%s' has not been deleted, so it cannot be undeleted." % role.name
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='roles',
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            role.deleted = False
            trans.sa_session.add( role )
            trans.sa_session.flush()
            count += 1
            undeleted_roles += " %s" % role.name
        message = "Undeleted %d roles: %s" % ( count, undeleted_roles )
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='roles',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

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
        id = kwd.get( 'id', None )
        if not id:
            message = "No role ids received for purging"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='roles',
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Purged %d roles: " % len( ids )
        for role_id in ids:
            role = get_role( trans, role_id )
            if not role.deleted:
                message = "Role '%s' has not been deleted, so it cannot be purged." % role.name
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='roles',
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            # Delete UserRoleAssociations
            for ura in role.users:
                user = trans.sa_session.query( trans.app.model.User ).get( ura.user_id )
                # Delete DefaultUserPermissions for associated users
                for dup in user.default_permissions:
                    if role == dup.role:
                        trans.sa_session.delete( dup )
                # Delete DefaultHistoryPermissions for associated users
                for history in user.histories:
                    for dhp in history.default_permissions:
                        if role == dhp.role:
                            trans.sa_session.delete( dhp )
                trans.sa_session.delete( ura )
            # Delete GroupRoleAssociations
            for gra in role.groups:
                trans.sa_session.delete( gra )
            # Delete DatasetPermissionss
            for dp in role.dataset_actions:
                trans.sa_session.delete( dp )
            trans.sa_session.flush()
            message += " %s " % role.name
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='roles',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    @web.expose
    @web.require_admin
    def groups( self, trans, **kwargs ):
        if 'operation' in kwargs:
            operation = kwargs[ 'operation' ].lower().replace( '+', ' ' )
            if operation == "groups":
                return self.group( trans, **kwargs )
            if operation == "create":
                return self.create_group( trans, **kwargs )
            if operation == "delete":
                return self.mark_group_deleted( trans, **kwargs )
            if operation == "undelete":
                return self.undelete_group( trans, **kwargs )
            if operation == "purge":
                return self.purge_group( trans, **kwargs )
            if operation == "manage users and roles":
                return self.manage_users_and_roles_for_group( trans, **kwargs )
            if operation == "rename":
                return self.rename_group( trans, **kwargs )
        # Render the list view
        return self.group_list_grid( trans, **kwargs )

    @web.expose
    @web.require_admin
    def rename_group( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            message = "No group ids received for renaming"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='groups',
                                                       message=message,
                                                       status='error' ) )
        group = get_group( trans, id )
        if params.get( 'rename_group_button', False ):
            old_name = group.name
            new_name = util.restore_text( params.name )
            if not new_name:
                message = 'Enter a valid name'
                status = 'error'
            else:
                existing_group = trans.sa_session.query( trans.app.model.Group ).filter( trans.app.model.Group.table.c.name == new_name ).first()
                if existing_group and existing_group.id != group.id:
                    message = 'A group with that name already exists'
                    status = 'error'
                else:
                    if group.name != new_name:
                        group.name = new_name
                        trans.sa_session.add( group )
                        trans.sa_session.flush()
                        message = "Group '%s' has been renamed to '%s'" % ( old_name, new_name )
                    return trans.response.send_redirect( web.url_for( controller='admin',
                                                                      action='groups',
                                                                      message=util.sanitize_text( message ),
                                                                      status='done' ) )
        return trans.fill_template( '/admin/dataset_security/group/group_rename.mako',
                                    group=group,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def manage_users_and_roles_for_group( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        group = get_group( trans, params.id )
        if params.get( 'group_roles_users_edit_button', False ):
            in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in util.listify( params.in_roles ) ]
            in_users = [ trans.sa_session.query( trans.app.model.User ).get( x ) for x in util.listify( params.in_users ) ]
            trans.app.security_agent.set_entity_group_associations( groups=[ group ], roles=in_roles, users=in_users )
            trans.sa_session.refresh( group )
            message += "Group '%s' has been updated with %d associated roles and %d associated users" % ( group.name, len( in_roles ), len( in_users ) )
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='groups',
                                                       message=util.sanitize_text( message ),
                                                       status=status ) )
        in_roles = []
        out_roles = []
        in_users = []
        out_users = []
        for role in trans.sa_session.query(trans.app.model.Role ) \
                                    .filter( trans.app.model.Role.table.c.deleted == false() ) \
                                    .order_by( trans.app.model.Role.table.c.name ):
            if role in [ x.role for x in group.roles ]:
                in_roles.append( ( role.id, role.name ) )
            else:
                out_roles.append( ( role.id, role.name ) )
        for user in trans.sa_session.query( trans.app.model.User ) \
                                    .filter( trans.app.model.User.table.c.deleted == false() ) \
                                    .order_by( trans.app.model.User.table.c.email ):
            if user in [ x.user for x in group.users ]:
                in_users.append( ( user.id, user.email ) )
            else:
                out_users.append( ( user.id, user.email ) )
        message += 'Group %s is currently associated with %d roles and %d users' % ( group.name, len( in_roles ), len( in_users ) )
        return trans.fill_template( '/admin/dataset_security/group/group.mako',
                                    group=group,
                                    in_roles=in_roles,
                                    out_roles=out_roles,
                                    in_users=in_users,
                                    out_users=out_users,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def create_group( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        name = util.restore_text( params.get( 'name', '' ) )
        in_users = util.listify( params.get( 'in_users', [] ) )
        out_users = util.listify( params.get( 'out_users', [] ) )
        in_roles = util.listify( params.get( 'in_roles', [] ) )
        out_roles = util.listify( params.get( 'out_roles', [] ) )
        create_role_for_group = params.get( 'create_role_for_group', '' )
        create_role_for_group_checked = CheckboxField.is_checked( create_role_for_group )
        ok = True
        if params.get( 'create_group_button', False ):
            if not name:
                message = "Enter a valid name."
                status = 'error'
                ok = False
            elif trans.sa_session.query( trans.app.model.Group ).filter( trans.app.model.Group.table.c.name == name ).first():
                message = "Group names must be unique and a group with that name already exists, so choose another name."
                status = 'error'
                ok = False
            else:
                # Create the group
                group = trans.app.model.Group( name=name )
                trans.sa_session.add( group )
                trans.sa_session.flush()
                # Create the UserRoleAssociations
                for user in [ trans.sa_session.query( trans.app.model.User ).get( x ) for x in in_users ]:
                    uga = trans.app.model.UserGroupAssociation( user, group )
                    trans.sa_session.add( uga )
                # Create the GroupRoleAssociations
                for role in [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in in_roles ]:
                    gra = trans.app.model.GroupRoleAssociation( group, role )
                    trans.sa_session.add( gra )
                if create_role_for_group_checked:
                    # Create the role
                    role = trans.app.model.Role( name=name, description='Role for group %s' % name )
                    trans.sa_session.add( role )
                    # Associate the role with the group
                    gra = trans.model.GroupRoleAssociation( group, role )
                    trans.sa_session.add( gra )
                    num_in_roles = len( in_roles ) + 1
                else:
                    num_in_roles = len( in_roles )
                trans.sa_session.flush()
                message = "Group '%s' has been created with %d associated users and %d associated roles.  " \
                    % ( group.name, len( in_users ), num_in_roles )
                if create_role_for_group_checked:
                    message += 'One of the roles associated with this group is the newly created role with the same name.'
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='groups',
                                                           message=util.sanitize_text( message ),
                                                           status='done' ) )
        if ok:
            for user in trans.sa_session.query( trans.app.model.User ) \
                                        .filter( trans.app.model.User.table.c.deleted == false() ) \
                                        .order_by( trans.app.model.User.table.c.email ):
                out_users.append( ( user.id, user.email ) )
            for role in trans.sa_session.query( trans.app.model.Role ) \
                                        .filter( trans.app.model.Role.table.c.deleted == false() ) \
                                        .order_by( trans.app.model.Role.table.c.name ):
                out_roles.append( ( role.id, role.name ) )
        return trans.fill_template( '/admin/dataset_security/group/group_create.mako',
                                    name=name,
                                    in_users=in_users,
                                    out_users=out_users,
                                    in_roles=in_roles,
                                    out_roles=out_roles,
                                    create_role_for_group_checked=create_role_for_group_checked,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def mark_group_deleted( self, trans, **kwd ):
        params = util.Params( kwd )
        id = params.get( 'id', None )
        if not id:
            message = "No group ids received for marking deleted"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='groups',
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Deleted %d groups: " % len( ids )
        for group_id in ids:
            group = get_group( trans, group_id )
            group.deleted = True
            trans.sa_session.add( group )
            trans.sa_session.flush()
            message += " %s " % group.name
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='groups',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    @web.expose
    @web.require_admin
    def undelete_group( self, trans, **kwd ):
        id = kwd.get( 'id', None )
        if not id:
            message = "No group ids received for undeleting"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='groups',
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        count = 0
        undeleted_groups = ""
        for group_id in ids:
            group = get_group( trans, group_id )
            if not group.deleted:
                message = "Group '%s' has not been deleted, so it cannot be undeleted." % group.name
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='groups',
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            group.deleted = False
            trans.sa_session.add( group )
            trans.sa_session.flush()
            count += 1
            undeleted_groups += " %s" % group.name
        message = "Undeleted %d groups: %s" % ( count, undeleted_groups )
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='groups',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    @web.expose
    @web.require_admin
    def purge_group( self, trans, **kwd ):
        # This method should only be called for a Group that has previously been deleted.
        # Purging a deleted Group simply deletes all UserGroupAssociations and GroupRoleAssociations.
        id = kwd.get( 'id', None )
        if not id:
            message = "No group ids received for purging"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='groups',
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Purged %d groups: " % len( ids )
        for group_id in ids:
            group = get_group( trans, group_id )
            if not group.deleted:
                # We should never reach here, but just in case there is a bug somewhere...
                message = "Group '%s' has not been deleted, so it cannot be purged." % group.name
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='groups',
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            # Delete UserGroupAssociations
            for uga in group.users:
                trans.sa_session.delete( uga )
            # Delete GroupRoleAssociations
            for gra in group.roles:
                trans.sa_session.delete( gra )
            trans.sa_session.flush()
            message += " %s " % group.name
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='groups',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    @web.expose
    @web.require_admin
    def create_new_user( self, trans, **kwd ):
        return trans.response.send_redirect( web.url_for( controller='user',
                                                          action='create',
                                                          cntrller='admin' ) )

    @web.expose
    @web.require_admin
    def reset_user_password( self, trans, **kwd ):
        user_id = kwd.get( 'id', None )
        if not user_id:
            message = "No users received for resetting passwords."
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='users',
                                                       message=message,
                                                       status='error' ) )
        user_ids = util.listify( user_id )
        if 'reset_user_password_button' in kwd:
            message = ''
            status = ''
            for user_id in user_ids:
                user = get_user( trans, user_id )
                password = kwd.get( 'password', None )
                confirm = kwd.get( 'confirm', None )
                if len( password ) < 6:
                    message = "Use a password of at least 6 characters."
                    status = 'error'
                    break
                elif password != confirm:
                    message = "Passwords do not match."
                    status = 'error'
                    break
                else:
                    user.set_password_cleartext( password )
                    trans.sa_session.add( user )
                    trans.sa_session.flush()
            if not message and not status:
                message = "Passwords reset for %d %s." % ( len( user_ids ), inflector.cond_plural( len( user_ids ), 'user' ) )
                status = 'done'
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='users',
                                                       message=util.sanitize_text( message ),
                                                       status=status ) )
        users = [ get_user( trans, user_id ) for user_id in user_ids ]
        if len( user_ids ) > 1:
            user_id = ','.join( user_ids )
        return trans.fill_template( '/admin/user/reset_password.mako',
                                    id=user_id,
                                    users=users,
                                    password='',
                                    confirm='' )

    @web.expose
    @web.require_admin
    def mark_user_deleted( self, trans, **kwd ):
        id = kwd.get( 'id', None )
        if not id:
            message = "No user ids received for deleting"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='users',
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Deleted %d users: " % len( ids )
        for user_id in ids:
            user = get_user( trans, user_id )
            user.deleted = True
            trans.sa_session.add( user )
            trans.sa_session.flush()
            message += " %s " % user.email
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='users',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    @web.expose
    @web.require_admin
    def undelete_user( self, trans, **kwd ):
        id = kwd.get( 'id', None )
        if not id:
            message = "No user ids received for undeleting"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='users',
                                                       message=message,
                                                       status='error' ) )
        ids = util.listify( id )
        count = 0
        undeleted_users = ""
        for user_id in ids:
            user = get_user( trans, user_id )
            if not user.deleted:
                message = "User '%s' has not been deleted, so it cannot be undeleted." % user.email
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='users',
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            user.deleted = False
            trans.sa_session.add( user )
            trans.sa_session.flush()
            count += 1
            undeleted_users += " %s" % user.email
        message = "Undeleted %d users: %s" % ( count, undeleted_users )
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='users',
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
        # - UserAddress where user_id == User.id
        # Purging Histories and Datasets must be handled via the cleanup_datasets.py script
        id = kwd.get( 'id', None )
        if not id:
            message = "No user ids received for purging"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='users',
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        ids = util.listify( id )
        message = "Purged %d users: " % len( ids )
        for user_id in ids:
            user = get_user( trans, user_id )
            if not user.deleted:
                # We should never reach here, but just in case there is a bug somewhere...
                message = "User '%s' has not been deleted, so it cannot be purged." % user.email
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='users',
                                                           message=util.sanitize_text( message ),
                                                           status='error' ) )
            private_role = trans.app.security_agent.get_private_user_role( user )
            # Delete History
            for h in user.active_histories:
                trans.sa_session.refresh( h )
                for hda in h.active_datasets:
                    # Delete HistoryDatasetAssociation
                    d = trans.sa_session.query( trans.app.model.Dataset ).get( hda.dataset_id )
                    # Delete Dataset
                    if not d.deleted:
                        d.deleted = True
                        trans.sa_session.add( d )
                    hda.deleted = True
                    trans.sa_session.add( hda )
                h.deleted = True
                trans.sa_session.add( h )
            # Delete UserGroupAssociations
            for uga in user.groups:
                trans.sa_session.delete( uga )
            # Delete UserRoleAssociations EXCEPT FOR THE PRIVATE ROLE
            for ura in user.roles:
                if ura.role_id != private_role.id:
                    trans.sa_session.delete( ura )
            # Delete UserAddresses
            for address in user.addresses:
                trans.sa_session.delete( address )
            # Purge the user
            user.purged = True
            trans.sa_session.add( user )
            trans.sa_session.flush()
            message += "%s " % user.email
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='users',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )

    @web.expose
    @web.require_admin
    def users( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "roles":
                return self.user( trans, **kwd )
            elif operation == "reset password":
                return self.reset_user_password( trans, **kwd )
            elif operation == "delete":
                return self.mark_user_deleted( trans, **kwd )
            elif operation == "undelete":
                return self.undelete_user( trans, **kwd )
            elif operation == "purge":
                return self.purge_user( trans, **kwd )
            elif operation == "create":
                return self.create_new_user( trans, **kwd )
            elif operation == "information":
                user_id = kwd.get( 'id', None )
                if not user_id:
                    kwd[ 'message' ] = util.sanitize_text( "Invalid user id (%s) received" % str( user_id ) )
                    kwd[ 'status' ] = 'error'
                else:
                    return trans.response.send_redirect( web.url_for( controller='user', action='information', **kwd ) )
            elif operation == "manage roles and groups":
                return self.manage_roles_and_groups_for_user( trans, **kwd )
        if trans.app.config.allow_user_deletion:
            if self.delete_operation not in self.user_list_grid.operations:
                self.user_list_grid.operations.append( self.delete_operation )
            if self.undelete_operation not in self.user_list_grid.operations:
                self.user_list_grid.operations.append( self.undelete_operation )
            if self.purge_operation not in self.user_list_grid.operations:
                self.user_list_grid.operations.append( self.purge_operation )
        # Render the list view
        return self.user_list_grid( trans, **kwd )

    @web.expose
    @web.require_admin
    def name_autocomplete_data( self, trans, q=None, limit=None, timestamp=None ):
        """Return autocomplete data for user emails"""
        ac_data = ""
        for user in trans.sa_session.query( trans.app.model.User ).filter_by( deleted=False ).filter( func.lower( trans.app.model.User.email ).like( q.lower() + "%" ) ):
            ac_data = ac_data + user.email + "\n"
        return ac_data

    @web.expose
    @web.require_admin
    def manage_roles_and_groups_for_user( self, trans, **kwd ):
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
                out_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in util.listify( out_roles ) ]
            if private_role in out_roles:
                message += "You cannot eliminate a user's private role association.  "
                status = 'error'
            in_roles = kwd.get( 'in_roles', [] )
            if in_roles:
                in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in util.listify( in_roles ) ]
            out_groups = kwd.get( 'out_groups', [] )
            if out_groups:
                out_groups = [ trans.sa_session.query( trans.app.model.Group ).get( x ) for x in util.listify( out_groups ) ]
            in_groups = kwd.get( 'in_groups', [] )
            if in_groups:
                in_groups = [ trans.sa_session.query( trans.app.model.Group ).get( x ) for x in util.listify( in_groups ) ]
            if in_roles:
                trans.app.security_agent.set_entity_user_associations( users=[ user ], roles=in_roles, groups=in_groups )
                trans.sa_session.refresh( user )
                message += "User '%s' has been updated with %d associated roles and %d associated groups (private roles are not displayed)" % \
                    ( user.email, len( in_roles ), len( in_groups ) )
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='users',
                                                           message=util.sanitize_text( message ),
                                                           status='done' ) )
        in_roles = []
        out_roles = []
        in_groups = []
        out_groups = []
        for role in trans.sa_session.query( trans.app.model.Role ).filter( trans.app.model.Role.table.c.deleted == false() ) \
                                                                  .order_by( trans.app.model.Role.table.c.name ):
            if role in [ x.role for x in user.roles ]:
                in_roles.append( ( role.id, role.name ) )
            elif role.type != trans.app.model.Role.types.PRIVATE:
                # There is a 1 to 1 mapping between a user and a PRIVATE role, so private roles should
                # not be listed in the roles form fields, except for the currently selected user's private
                # role, which should always be in in_roles.  The check above is added as an additional
                # precaution, since for a period of time we were including private roles in the form fields.
                out_roles.append( ( role.id, role.name ) )
        for group in trans.sa_session.query( trans.app.model.Group ).filter( trans.app.model.Group.table.c.deleted == false() ) \
                                                                    .order_by( trans.app.model.Group.table.c.name ):
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
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def jobs( self, trans, stop=[], stop_msg=None, cutoff=180, job_lock=None, ajl_submit=None, **kwd ):
        deleted = []
        msg = None
        status = None
        job_ids = util.listify( stop )
        if job_ids and stop_msg in [ None, '' ]:
            msg = 'Please enter an error message to display to the user describing why the job was terminated'
            status = 'error'
        elif job_ids:
            if stop_msg[-1] not in PUNCTUATION:
                stop_msg += '.'
            for job_id in job_ids:
                error_msg = "This job was stopped by an administrator: %s  <a href='%s' target='_blank'>Contact support</a> for additional help." \
                    % ( stop_msg, self.app.config.get("support_url", "https://wiki.galaxyproject.org/Support" ) )
                if trans.app.config.track_jobs_in_database:
                    job = trans.sa_session.query( trans.app.model.Job ).get( job_id )
                    job.stderr = error_msg
                    job.set_state( trans.app.model.Job.states.DELETED_NEW )
                    trans.sa_session.add( job )
                else:
                    trans.app.job_manager.job_stop_queue.put( job_id, error_msg=error_msg )
                deleted.append( str( job_id ) )
        if deleted:
            msg = 'Queued job'
            if len( deleted ) > 1:
                msg += 's'
            msg += ' for deletion: '
            msg += ', '.join( deleted )
            status = 'done'
            trans.sa_session.flush()
        if ajl_submit:
            if job_lock == 'on':
                galaxy.queue_worker.send_control_task(trans.app, 'admin_job_lock',
                                                      kwargs={'job_lock': True } )
                job_lock = True
            else:
                galaxy.queue_worker.send_control_task(trans.app, 'admin_job_lock',
                                                      kwargs={'job_lock': False } )
                job_lock = False
        else:
            job_lock = trans.app.job_manager.job_lock
        cutoff_time = datetime.utcnow() - timedelta( seconds=int( cutoff ) )
        jobs = trans.sa_session.query( trans.app.model.Job ) \
                               .filter( and_( trans.app.model.Job.table.c.update_time < cutoff_time,
                                              or_( trans.app.model.Job.state == trans.app.model.Job.states.NEW,
                                                   trans.app.model.Job.state == trans.app.model.Job.states.QUEUED,
                                                   trans.app.model.Job.state == trans.app.model.Job.states.RUNNING,
                                                   trans.app.model.Job.state == trans.app.model.Job.states.UPLOAD ) ) ) \
                               .order_by( trans.app.model.Job.table.c.update_time.desc() ).all()
        recent_jobs = trans.sa_session.query( trans.app.model.Job ) \
            .filter( and_( trans.app.model.Job.table.c.update_time > cutoff_time,
                           or_( trans.app.model.Job.state == trans.app.model.Job.states.ERROR,
                                trans.app.model.Job.state == trans.app.model.Job.states.OK) ) ) \
            .order_by( trans.app.model.Job.table.c.update_time.desc() ).all()
        last_updated = {}
        for job in jobs:
            delta = datetime.utcnow() - job.update_time
            if delta.days > 0:
                last_updated[job.id] = '%s hours' % ( delta.days * 24 + int( delta.seconds / 60 / 60 ) )
            elif delta > timedelta( minutes=59 ):
                last_updated[job.id] = '%s hours' % int( delta.seconds / 60 / 60 )
            else:
                last_updated[job.id] = '%s minutes' % int( delta.seconds / 60 )
        finished = {}
        for job in recent_jobs:
            delta = datetime.utcnow() - job.update_time
            if delta.days > 0:
                finished[job.id] = '%s hours' % ( delta.days * 24 + int( delta.seconds / 60 / 60 ) )
            elif delta > timedelta( minutes=59 ):
                finished[job.id] = '%s hours' % int( delta.seconds / 60 / 60 )
            else:
                finished[job.id] = '%s minutes' % int( delta.seconds / 60 )
        return trans.fill_template( '/admin/jobs.mako',
                                    jobs=jobs,
                                    recent_jobs=recent_jobs,
                                    last_updated=last_updated,
                                    finished=finished,
                                    cutoff=cutoff,
                                    msg=msg,
                                    status=status,
                                    job_lock=job_lock)

    @web.expose
    @web.require_admin
    def job_info( self, trans, jobid=None ):
        job = None
        if jobid is not None:
            job = trans.sa_session.query( trans.app.model.Job ).get(jobid)
        return trans.fill_template( '/webapps/reports/job_info.mako',
                                    job=job,
                                    message="<a href='jobs'>Back</a>" )

    @web.expose
    @web.require_admin
    def manage_tool_dependencies( self,
                                  trans,
                                  install_dependencies=False,
                                  uninstall_dependencies=False,
                                  remove_unused_dependencies=False,
                                  selected_tool_ids=None,
                                  selected_environments_to_uninstall=None,
                                  viewkey='View tool-centric dependencies'):
        if not selected_tool_ids:
            selected_tool_ids = []
        if not selected_environments_to_uninstall:
            selected_environments_to_uninstall = []
        tools_by_id = trans.app.toolbox.tools_by_id
        view = six.next(six.itervalues(trans.app.toolbox.tools_by_id))._view
        if selected_tool_ids:
            # install the dependencies for the tools in the selected_tool_ids list
            if not isinstance(selected_tool_ids, list):
                selected_tool_ids = [selected_tool_ids]
            requirements = set([tools_by_id[tid].tool_requirements for tid in selected_tool_ids])
            if install_dependencies:
                [view.install_dependencies(r) for r in requirements]
            elif uninstall_dependencies:
                [view.uninstall_dependencies(index=None, requirements=r) for r in requirements]
        if selected_environments_to_uninstall and remove_unused_dependencies:
            if not isinstance(selected_environments_to_uninstall, list):
                selected_environments_to_uninstall = [selected_environments_to_uninstall]
            view.remove_unused_dependency_paths(selected_environments_to_uninstall)
        return trans.fill_template( '/webapps/galaxy/admin/manage_dependencies.mako',
                                    tools=tools_by_id,
                                    requirements_status=view.toolbox_requirements_status,
                                    tool_ids_by_requirements=view.tool_ids_by_requirements,
                                    unused_environments=view.unused_dependency_paths,
                                    viewkey=viewkey )

    @web.expose
    @web.require_admin
    def sanitize_whitelist( self, trans, submit_whitelist=False, tools_to_whitelist=[]):
        if submit_whitelist:
            # write the configured sanitize_whitelist_file with new whitelist
            # and update in-memory list.
            with open(trans.app.config.sanitize_whitelist_file, 'wt') as f:
                if isinstance(tools_to_whitelist, six.string_types):
                    tools_to_whitelist = [tools_to_whitelist]
                new_whitelist = sorted([tid for tid in tools_to_whitelist if tid in trans.app.toolbox.tools_by_id])
                f.write("\n".join(new_whitelist))
            trans.app.config.sanitize_whitelist = new_whitelist
            galaxy.queue_worker.send_control_task(trans.app, 'reload_sanitize_whitelist', noop_self=True)
            # dispatch a message to reload list for other processes
        return trans.fill_template( '/webapps/galaxy/admin/sanitize_whitelist.mako',
                                    sanitize_all=trans.app.config.sanitize_all_html,
                                    tools=trans.app.toolbox.tools_by_id )


# ---- Utility methods -------------------------------------------------------


def get_user( trans, user_id ):
    """Get a User from the database by id."""
    user = trans.sa_session.query( trans.model.User ).get( trans.security.decode_id( user_id ) )
    if not user:
        return trans.show_error_message( "User not found for id (%s)" % str( user_id ) )
    return user


def get_user_by_username( trans, username ):
    """Get a user from the database by username"""
    # TODO: Add exception handling here.
    return trans.sa_session.query( trans.model.User ) \
                           .filter( trans.model.User.table.c.username == username ) \
                           .one()


def get_role( trans, id ):
    """Get a Role from the database by id."""
    # Load user from database
    id = trans.security.decode_id( id )
    role = trans.sa_session.query( trans.model.Role ).get( id )
    if not role:
        return trans.show_error_message( "Role not found for id (%s)" % str( id ) )
    return role


def get_group( trans, id ):
    """Get a Group from the database by id."""
    # Load user from database
    id = trans.security.decode_id( id )
    group = trans.sa_session.query( trans.model.Group ).get( id )
    if not group:
        return trans.show_error_message( "Group not found for id (%s)" % str( id ) )
    return group


def get_quota( trans, id ):
    """Get a Quota from the database by id."""
    # Load user from database
    id = trans.security.decode_id( id )
    quota = trans.sa_session.query( trans.model.Quota ).get( id )
    return quota
