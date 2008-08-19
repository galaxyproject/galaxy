
import shutil, StringIO, operator
from galaxy import util
from galaxy.web.base.controller import *
from galaxy.datatypes import sniff
from galaxy.security import RBACAgent
import galaxy.model
from xml.sax.saxutils import escape, unescape
import pkg_resources
pkg_resources.require( "sqlalchemy>=0.3" )
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
    @web.expose
    def dataset_security( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        return trans.fill_template( '/admin/dataset_security/index.mako', msg=msg )
    
    # Galaxy Group Stuff
    @web.expose
    def groups( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        # This query retrieves groups that are not deleted and members of each group
        q = sa.select( ( ( galaxy.model.Group.table.c.id ).label( 'group_id' ),
                         ( galaxy.model.Group.table.c.name ).label( 'group_name' ),
                         ( galaxy.model.Group.table.c.priority ).label( 'group_priority' ),
                         sa.func.count( galaxy.model.User.table.c.id ).label( 'total_members' ) ),
                       whereclause = galaxy.model.Group.table.c.deleted == False,
                       from_obj = [ sa.outerjoin( galaxy.model.Group.table, 
                                                  galaxy.model.UserGroupAssociation.table
                                                ).outerjoin( galaxy.model.User.table ) ],
                       group_by = [ galaxy.model.Group.table.c.id,
                                    galaxy.model.Group.table.c.name,
                                    galaxy.model.Group.table.c.priority ],
                       order_by = [ galaxy.model.Group.table.c.name ] )
        groups = []
        for row in q.execute():
            # This 2nd query retrieves the number of datasets and dataset permitted_actions associated with each group
            q2 = sa.select( ( ( galaxy.model.Group.table.c.id ).label( 'group_id' ),
                              ( galaxy.model.GroupDatasetAssociation.table.c.permitted_actions ).label( 'permitted_actions' ),
                              sa.func.count( galaxy.model.Dataset.table.c.id ).label( 'total_datasets' ) ),
                            whereclause = galaxy.model.Group.table.c.id == row.group_id,
                            from_obj = [ sa.outerjoin( galaxy.model.Group.table,
                                                       galaxy.model.GroupDatasetAssociation.table
                                                     ).outerjoin( galaxy.model.Dataset.table ) ],
                            group_by = [ galaxy.model.Group.table.c.id,
                                         galaxy.model.GroupDatasetAssociation.table.c.permitted_actions ] )
            for row2 in q2.execute():
                total_datasets = row2.total_datasets
                permitted_actions = []
                # There may not yet be any GroupDatasetAssociations, in which case no
                # actions will be found
                if row2.permitted_actions:
                    for action in row2.permitted_actions:
                        permitted_actions.append( action.encode( 'ascii' ) )
                    permitted_actions.sort()
            groups.append( ( row.group_id,
                             escape( row.group_name, entities ),
                             row.group_priority,
                             row.total_members,
                             total_datasets,
                             permitted_actions ) )
        return trans.fill_template( '/admin/dataset_security/groups.mako', 
                                    groups=groups, 
                                    msg=msg )
    @web.expose
    def create_group( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        q = sa.select( ( ( galaxy.model.User.table.c.id ).label( 'user_id' ),
                         ( galaxy.model.User.table.c.email ).label( 'user_email') ),
                       from_obj = [ galaxy.model.User.table ],
                       order_by = [ galaxy.model.User.table.c.email ] )
        users = []
        for row in q.execute():
            users.append( ( row.user_id,
                            escape( row.user_email, entities ) ) )
        return trans.fill_template( '/admin/dataset_security/group_create.mako', users=users, msg=msg )
    @web.expose
    def new_group( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        name = unescape( params.name, unentities )
        if not name:
            msg = "Please enter a name"
            trans.response.send_redirect( '/admin/create_group?msg=%s' % msg )
        else:
            try:
                priority = int( params.priority )
            except:
                priority = 0
            # Create the group
            group = galaxy.model.Group( name, priority )
            group.flush()
            # Add the members
            members = params.members
            for user_id in members:
                user = galaxy.model.User.get( user_id )
                # Create the UserGroupAssociation
                user_group_association = galaxy.model.UserGroupAssociation( user, group )
                user_group_association.flush()
            msg = "The new group has been created with priority %s and %s members" % ( str( priority ), str( len( members ) ) )
            trans.response.send_redirect( '/admin/groups?msg=%s' % msg )
    @web.expose
    def group_members( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        group_id = params.group_id
        group_name = unescape( params.group_name, unentities )
        # This query retrieves all members of the group
        q = sa.select( ( ( galaxy.model.User.table.c.id ).label( 'user_id' ),
                         ( galaxy.model.User.table.c.email ).label( 'user_email' ) ),
                       whereclause = galaxy.model.UserGroupAssociation.table.c.group_id == group_id,
                       from_obj = [ sa.outerjoin( galaxy.model.UserGroupAssociation.table, 
                                                  galaxy.model.User.table ) ],
                       order_by = [ 'user_email' ] )
        members = []
        for row in q.execute():
            members.append( ( row.user_id,
                              escape( row.user_email, entities ) ) )
        return trans.fill_template( '/admin/dataset_security/group_members.mako', 
                                    group_id=group_id, 
                                    group_name=escape( group_name, entities ),
                                    members=members,
                                    msg=msg )
    @web.expose
    def group_members_edit( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        group_id = params.group_id
        group_name = unescape( params.group_name, unentities )
        members = params.members
        # First get all users
        q = sa.select( ( ( galaxy.model.User.table.c.id ).label( 'user_id' ),
                         ( galaxy.model.User.table.c.email ).label( 'user_email' ) ),
                       order_by = [ 'user_email' ] )
        users = []
        for row in q.execute():
            users.append( ( row.user_id,
                            escape( row.user_email, entities ) ) )
        # Then get members of the group
        q = sa.select( ( ( galaxy.model.User.table.c.id ).label( 'user_id' ),
                         ( galaxy.model.User.table.c.email ).label( 'user_email' ) ),
                       whereclause = galaxy.model.UserGroupAssociation.table.c.group_id == group_id,
                       from_obj = [ sa.outerjoin( galaxy.model.UserGroupAssociation.table, 
                                                  galaxy.model.User.table ) ],
                       order_by = [ 'user_email' ] )
        members = []
        for row in q.execute():
            members.append( ( row.user_id,
                              escape( row.user_email, entities ) ) )
        return trans.fill_template( '/admin/dataset_security/group_members_edit.mako', 
                                    group_id=group_id, 
                                    group_name=escape( group_name, entities ),
                                    users=users,
                                    members=members, 
                                    msg=msg )
    @web.expose
    def update_group_members( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        group_id = int( params.group_id )
        members = params.members
        if members and not isinstance( members, list ):
            # mako passes singleton lists as strings for some reason
            members = [ members ]
        # Handle case where admin removed all members from group
        elif members is None:
            members = []
        group = galaxy.model.Group.get( group_id )
        # This is tricky since we have default association tables with
        # records referring to members of this group.  Because of this,
        # we'll need to handle changes to the member list rather than the
        # simpler approach of deleting all existing members and creating 
        # new records for user_ids in the received members param.
        # First remove existing members that are not in the received members param
        for user_group_assoc in group.users:
            if user_group_assoc.user_id not in members:
                user = galaxy.model.User.get( user_group_assoc.user_id )
                # Delete DefaultUserGroupAssociations
                for default_user_group_association in user.default_groups:
                    if default_user_group_association.group_id == group_id:
                        default_user_group_association.delete()
                        default_user_group_association.flush()
                        break # Should only be 1 record
                # Delete DefaultHistoryGroupAssociations
                for history in user.histories:
                    for default_history_group_association in history.default_groups:
                        if default_history_group_association.group_id == group_id:
                            default_history_group_association.delete()
                            default_history_group_association.flush()
                # Delete the UserGroupAssociation
                user_group_assoc.delete()
                user_group_assoc.flush()
        # Then add all new members to the group
        for user_id in members:
            user = galaxy.model.User.get( user_id )
            if user not in group.users:
                user_group_association = galaxy.model.UserGroupAssociation( user, group )
                user_group_association.flush()
        msg = "Group membership has been updated with a total of %s members" % len( members )
        trans.response.send_redirect( '/admin/group_members?group_id=%s&group_name=%s&msg=%s' % ( str( group_id ), params.group_name, msg ) )
    @web.expose
    def group_dataset_permitted_actions( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        group_id = int( params.group_id )
        group_name = unescape( params.group_name, unentities )
        # Need to get all actions to send to the form
        dataset_actions = []
        dpas = RBACAgent.permitted_actions
        for dpa in dpas.items():
            if dpa[0].startswith( 'DATASET' ):
                dataset_actions.append( dpa[1] )
            dataset_actions.sort()
        q = sa.select( ( ( galaxy.model.Group.table.c.priority ).label( 'group_priority' ),
                         ( galaxy.model.GroupDatasetAssociation.table.c.permitted_actions ).label( 'permitted_actions' ) ),
                        whereclause = galaxy.model.GroupDatasetAssociation.table.c.id == group_id,
                        from_obj = [ sa.outerjoin( galaxy.model.Group.table,
                                                   galaxy.model.GroupDatasetAssociation.table ) ] )
        gdas = []
        for row in q.execute():
            permitted_actions = []
            # Although there may be GroupDatasetAssociations, there may not be any permitted_actions on them
            if row.permitted_actions:
                for action in row.permitted_actions:
                    permitted_actions.append( action.encode( 'ascii' ) )
                permitted_actions.sort()
            gdas.append( ( row.group_priority,
                           permitted_actions ) )
            break # Just need 1 row
        return trans.fill_template( '/admin/dataset_security/group_dataset_permitted_actions_edit.mako', 
                                    group_id=group_id,
                                    group_name=escape( group_name, entities ),
                                    gdas=gdas,
                                    dataset_actions=dataset_actions,
                                    msg=msg )
    @web.expose
    def group_dataset_permitted_actions_edit( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        group_id = int( params.group_id )
        actions = params.actions
        if actions and not isinstance( actions, list ):
            actions = [ actions ]
        # Update the permitted_actions for every GroupDatasetAssociation of the Group
        q = sa.update( galaxy.model.GroupDatasetAssociation.table,
                       whereclause = galaxy.model.GroupDatasetAssociation.table.c.group_id == group_id,
                       values = { galaxy.model.GroupDatasetAssociation.table.c.permitted_actions : actions } )
        result = q.execute()
        msg = "The dataset permitted actions for the group have been updated, affecting %d rows in the group_dataset_association table" % result.rowcount
        trans.response.send_redirect( '/admin/groups?msg=%s' % msg )
    @web.expose
    def mark_group_deleted( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        group_id = params.group_id
        group = galaxy.model.Group.get( group_id )
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
        # This query retrieves groups that are not deleted and members of each group
        q = sa.select( ( ( galaxy.model.Group.table.c.id ).label( 'group_id' ),
                         ( galaxy.model.Group.table.c.name ).label( 'group_name' ),
                         ( galaxy.model.Group.table.c.priority ).label( 'group_priority' ),
                         sa.func.count( galaxy.model.User.table.c.id ).label( 'total_members' ) ),
                       whereclause = galaxy.model.Group.table.c.deleted == True,
                       from_obj = [ sa.outerjoin( galaxy.model.Group.table, 
                                                  galaxy.model.UserGroupAssociation.table
                                                ).outerjoin( galaxy.model.User.table ) ],
                       group_by = [ galaxy.model.Group.table.c.id,
                                    galaxy.model.Group.table.c.name,
                                    galaxy.model.Group.table.c.priority ],
                       order_by = [ galaxy.model.Group.table.c.name ] )
        groups = []
        for row in q.execute():
            # This 2nd query retrieves the number of datasets and dataset permitted_actions associated with each group
            q2 = sa.select( ( ( galaxy.model.Group.table.c.id ).label( 'group_id' ),
                              ( galaxy.model.GroupDatasetAssociation.table.c.permitted_actions ).label( 'permitted_actions' ),
                              sa.func.count( galaxy.model.Dataset.table.c.id ).label( 'total_datasets' ) ),
                            whereclause = galaxy.model.Group.table.c.id == row.group_id,
                            from_obj = [ sa.outerjoin( galaxy.model.Group.table,
                                                       galaxy.model.GroupDatasetAssociation.table
                                                     ).outerjoin( galaxy.model.Dataset.table ) ],
                            group_by = [ galaxy.model.Group.table.c.id,
                                         galaxy.model.GroupDatasetAssociation.table.c.permitted_actions ] )
            for row2 in q2.execute():
                total_datasets = row2.total_datasets
                permitted_actions = []
                # There may not yet be any GroupDatasetAssociations, in which case no
                # actions will be found
                if row2.permitted_actions:
                    for action in row2.permitted_actions:
                        permitted_actions.append( action.encode( 'ascii' ) )
                    permitted_actions.sort()
            groups.append( ( row.group_id,
                             escape( row.group_name, entities ),
                             row.group_priority,
                             row.total_members,
                             total_datasets,
                             permitted_actions ) )
        return trans.fill_template( '/admin/dataset_security/deleted_groups.mako', 
                                    groups=groups, 
                                    msg=msg )
    @web.expose
    def undelete_group( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        group_id = params.group_id
        group = galaxy.model.Group.get( group_id )
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
        group_id = params.group_id
        group = galaxy.model.Group.get( group_id )
        # Remove members and all associations
        for user_group_assoc in group.users:
            user = galaxy.model.User.get( user_group_assoc.user_id )
            # Delete DefaultUserGroupAssociations
            for default_user_group_association in user.default_groups:
                if default_user_group_association.group_id == group_id:
                    default_user_group_association.delete()
                    default_user_group_association.flush()
                    break # Should only be 1 record
            # Delete DefaultHistoryGroupAssociations
            for history in user.histories:
                for default_history_group_association in history.default_groups:
                    if default_history_group_association.group_id == group_id:
                        default_history_group_association.delete()
                        default_history_group_association.flush()
            # Delete the UserGroupAssociation
            user_group_assoc.delete()
            user_group_assoc.flush()
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
        q = sa.select( ( ( galaxy.model.User.table.c.id ).label( 'user_id' ),
                         ( galaxy.model.User.table.c.email ).label( 'user_email') ),
                       from_obj = [ galaxy.model.User.table ],
                       order_by = [ galaxy.model.User.table.c.email ] )
        users = []
        for row in q.execute():
            users.append( ( row.user_id,
                            escape( row.user_email, entities ) ) )
        return trans.fill_template( '/admin/dataset_security/users.mako',
                                    users=users,
                                    msg=msg )
    @web.expose
    def specified_users_groups( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        user_id = int( params.user_id )
        user_email = unescape( params.user_email, unentities )
        # Get the groups to which the user belongs
        q = sa.select( ( ( galaxy.model.Group.table.c.id ).label( 'group_id' ),
                         ( galaxy.model.Group.table.c.name ).label( 'group_name' ),
                         ( galaxy.model.Group.table.c.priority ).label( 'group_priority' ) ),
                       whereclause = galaxy.model.User.table.c.id == user_id,
                       from_obj = [ sa.outerjoin( galaxy.model.User.table, 
                                                  galaxy.model.UserGroupAssociation.table ).outerjoin( galaxy.model.Group.table ) ],
                       order_by = [ 'group_name' ] )
        groups = []
        for row in q.execute():
            # Perform a 2nd query to get datasets associated with each group
            q2 = sa.select( ( ( galaxy.model.Group.table.c.id ).label( 'group_id' ),
                              ( galaxy.model.GroupDatasetAssociation.table.c.permitted_actions ).label( 'permitted_actions' ),
                              sa.func.count( galaxy.model.Dataset.table.c.id ).label( 'total_datasets' ) ),
                            whereclause = galaxy.model.Group.table.c.id == row.group_id,
                            from_obj = [ sa.outerjoin( galaxy.model.Group.table,
                                                       galaxy.model.GroupDatasetAssociation.table
                                                     ).outerjoin( galaxy.model.Dataset.table ) ],
                            group_by = [ galaxy.model.Group.table.c.id,
                                         galaxy.model.GroupDatasetAssociation.table.c.permitted_actions ] )
            for row2 in q2.execute():
                total_datasets = row2.total_datasets
                libraries = []
                permitted_actions = []
                # There may not yet be any GroupDatasetAssociations, in which case no
                # actions will be found
                if row2.permitted_actions:
                    for action in row2.permitted_actions:
                        permitted_actions.append( action.encode( 'ascii' ) )
                    permitted_actions.sort()
                    # If we have permitted actions, then we have at least 1 GroupDatasetAssociation, in
                    # which case, we can see if we have any Libraries that the user can access
                    libs = trans.app.model.Library.select()
                    for library in libs:
                        folder = library.root_folder
                        components = list( folder.folders ) + list( folder.datasets )
                        for component in components:
                            if self.renderable( trans, component, row2.group_id ):
                                libraries.append( library.id )
                                break
            groups.append( ( row.group_id,
                             escape( row.group_name, entities ),
                             row.group_priority,
                             row2.total_datasets,
                             permitted_actions, 
                             libraries ) )
        return trans.fill_template( '/admin/dataset_security/specified_users_groups.mako', 
                                    user_id=user_id, 
                                    user_email=escape( user_email, entities ),
                                    groups=groups,
                                    msg=msg )
    @web.expose
    def specified_users_group_libraries( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        params = util.Params( kwd )
        msg = params.msg
        library_ids = params.library_ids.split( ',' )
        libraries = []
        for id in library_ids:
            library = trans.app.model.Library.get( id )
            libraries.append( library )
        return trans.fill_template( '/admin/library/specified_users_group_libraries.mako', 
                                    user_email=params.user_email, 
                                    group_name=params.group_name, 
                                    libraries=libraries )

    # Galaxy Library Stuff
    @web.expose
    def libraries( self, trans, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        return trans.fill_template( '/admin/library/libraries.mako', libraries=trans.app.model.Library.select() )
    @web.expose
    def library( self, trans, id=None, name="Unnamed", description=None, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        if 'create_library' in kwd:
            library = trans.app.model.Library( name=name, description=description )
            root_folder = trans.app.model.LibraryFolder( name=name, description=description )
            root_folder.flush()
            library.root_folder = root_folder
            library.flush()
            trans.response.send_redirect( web.url_for( action='folder', id = root_folder.id ) )
        elif id is None:
            return trans.show_form( 
                web.FormBuilder( action = web.url_for(), title = "Create a new Library", name = "create_library", submit_text = "Submit" )
                    .add_text( name = "name", label = "Name", value = "Unnamed", error = None, help = None )
                    .add_text( name = "description", label = "Description", value = None, error = None, help = None )
                    .add_input( 'hidden', "Create Library", 'create_library', use_label = False  ) )
        library = trans.app.model.Library.get( id )
        if library:
            return trans.fill_template( '/admin/library/library.mako', library = library )
        else:
            return trans.show_error_message( "Invalid library specified" )
    @web.expose
    def folder( self, trans, id=None, name="Unnamed", description=None, parent_id = None, **kwd ):
        if not self.user_is_admin( trans ):
            return trans.show_error_message( no_privilege_msg )
        if 'create_folder' in kwd:
            folder = trans.app.model.LibraryFolder( name = name, description = description )
            # We are associating the last used genome_build with folders, so we will always
            # initialize a new folder with the first dbkey in util.dbnames which is currently
            # ?    unspecified (?)
            folder.genome_build = util.dbnames.default_value
            if parent_id:
                parent_folder = trans.app.model.LibraryFolder.get( parent_id )
                parent_folder.add_folder( folder )
            folder.flush()
            trans.response.send_redirect( web.url_for( action='folder', id = folder.id ) )
        elif id is None:
            return trans.show_form( 
                web.FormBuilder( action = web.url_for(), title = "Create a new Folder", name = "create_folder", submit_text = "Submit" )
                    .add_text( name = "name", label = "Name", value = "Unnamed", error = None, help = None )
                    .add_text( name = "description", label = "Description", value = None, error = None, help = None )
                    .add_input( 'hidden', None, 'parent_id', value = parent_id, use_label = False  )
                    .add_input( 'hidden', "Create Folder", 'create_folder', use_label = False  ) )
        folder = trans.app.model.LibraryFolder.get( id )
        if folder:
            msg = ''
            if 'rename_folder' in kwd:
                folder.name = name
                folder.description = description
                folder.flush()
                msg = 'Folder has been renamed.'
            return trans.fill_template( '/admin/library/folder.mako', folder=folder, msg=msg )
        else:
            return trans.show_error_message( "Invalid folder specified" )
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

        # add_file method
        def add_file( file_obj, name, extension, dbkey, last_used_build, groups, info='no info', space_to_tab=False ):
            data_type = None
            temp_name = sniff.stream_to_file( file_obj )
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
            # GroupDatasetAssociations will enable security on the dataset based on the permitted_actions
            # associated with the GroupDatasetAssociation.  The default permitted_actions at this point
            # will be DATASET_ACCESS, but the user can change this after the file is uploaded.
            permitted_actions = [ RBACAgent.permitted_actions.DATASET_ACCESS ]
            for group_id in groups:
                group = galaxy.model.Group.get( group_id )
                group_dataset_assoc = galaxy.model.GroupDatasetAssociation( group, dataset.dataset, permitted_actions )
                group_dataset_assoc.flush()
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

        if 'create_dataset' in kwd:
            # Copied from upload tool action
            last_dataset_created = None
            data_file = kwd['file_data']
            url_paste = kwd['url_paste']
            space_to_tab = False 
            if 'space_to_tab' in kwd:
                if kwd['space_to_tab'] not in ["None", None]:
                    space_to_tab = True
            groups = kwd['groups']
            if groups and not isinstance( groups, list ):
                # mako sends singleton lists as a string
                groups = [ groups ]
            if groups is None:
                groups = []
            temp_name = ""
            data_list = []

            if 'filename' in dir( data_file ):
                file_name = data_file.filename
                file_name = file_name.split( '\\' )[-1]
                file_name = file_name.split( '/' )[-1]
                last_dataset_created = add_file( data_file.file,
                                                 file_name,
                                                 extension,
                                                 dbkey,
                                                 last_used_build,
                                                 groups,
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
                                                             groups,
                                                             info="uploaded url",
                                                             space_to_tab=space_to_tab )
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
                                                         groups,
                                                         info="pasted entry",
                                                         space_to_tab=space_to_tab )
            trans.response.send_redirect( web.url_for( action='dataset', id=last_dataset_created.id ) )
        elif id is None:
            # Send list of data formats to the form so the "extension" select list can be populated dynamically
            file_formats = trans.app.datatypes_registry.upload_file_formats
            # Send list of genome builds to the form so the "dbkey" select list can be populated dynamically
            def get_dbkey_options( last_used_build ):
                for dbkey, build_name in util.dbnames:
                    yield build_name, dbkey, ( dbkey==last_used_build )
            dbkeys = get_dbkey_options( last_used_build )
            # Send list of groups to the form so the dataset can be associated with 1 or more of them.
            groups = []
            q = sa.select( ( ( galaxy.model.Group.table.c.id ).label( 'group_id' ),
                             ( galaxy.model.Group.table.c.name ).label( 'group_name' ) ),
                            order_by = [ galaxy.model.Group.table.c.name ] )
            for row in q.execute():
                groups.append( ( row.group_id, row.group_name ) )
            groups = sorted( groups, key=operator.itemgetter(1) )
            return trans.fill_template( '/admin/library/new_dataset.mako', 
                                        folder_id=folder_id,
                                        file_formats=file_formats,
                                        dbkeys=dbkeys,
                                        last_used_build=last_used_build,
                                        groups=groups )
        dataset = trans.app.model.LibraryFolderDatasetAssociation.get( id )
        if dataset:
            # Copied from edit attributes for 'regular' datasets with some additions
            p = util.Params(kwd, safe=False)
            if p.change_permitted_actions:
                # The user clicked the Save button on the 'Group Associations' form
                actions = p.actions
                if actions and not isinstance( actions, list ):
                    actions = [ actions ]
                if actions is None:
                    actions = []
                # actions is a list of comma-separated strings consisting of group_id and permitted_action,
                # something like: ['6,dataset_access', '6,dataset_edit_metadata'].  We'll parse them and
                # create a dict whose keys are groups_id and values are permitted_actions
                gdpa_dict = {}
                for action in actions:
                    group_id, dpa = action.split( ',' )
                    group_id = int( group_id )
                    if group_id in gdpa_dict.keys():
                        gdpa_dict[ group_id ].append( dpa )
                    else:
                        gdpa_dict[ group_id ] = [ dpa ]
                # Refresh the Dataset to ensure we have a valid set of DatasetGroupAssociations
                dataset.dataset.refresh()
                # Check to see if we need to delete any GroupDatasetAssociations.  This occurs if
                # the user unchecked all boxes for a group
                for group_dataset_assoc in dataset.dataset.groups:
                    if group_dataset_assoc.group_id not in gdpa_dict.keys():
                        group_dataset_assoc.delete()
                        group_dataset_assoc.flush()
                # Use the dict to update the permitted actions for each GroupDatasetAssociaton
                for group_id in gdpa_dict:
                    actions = gdpa_dict[ group_id ]
                    # Update the permitted_actions for every GroupDatasetAssociation of the Group
                    q = sa.update( galaxy.model.GroupDatasetAssociation.table,
                                   whereclause = galaxy.model.GroupDatasetAssociation.table.c.group_id == group_id,
                                   values = { galaxy.model.GroupDatasetAssociation.table.c.permitted_actions : actions } )
                    result = q.execute()
            elif p.change:
                # The user clicked the Save button on the 'Change data type' form
                trans.app.datatypes_registry.change_datatype( dataset, p.datatype )
                trans.app.model.flush()
            elif p.save:
                # The user clicked the Save button on the 'Edit Attributes' form
                dataset.name  = name
                dataset.info  = info
                # The following for loop will save all metadata_spec items
                for name, spec in dataset.datatype.metadata_spec.items():
                    if spec.get("readonly"):
                        continue
                    optional = p.get("is_"+name, None)
                    if optional and optional == 'true':
                        # optional element... == 'true' actually means it is NOT checked (and therefore ommitted)
                        setattr(dataset.metadata,name,None)
                    else:
                        setattr(dataset.metadata,name,spec.unwrap(p.get(name, None), p))

                dataset.datatype.after_edit( dataset )
                trans.app.model.flush()
                return trans.show_ok_message( "Attributes updated" )
            elif p.detect:
                # The user clicked the Auto-detect button on the 'Edit Attributes' form
                for name, spec in dataset.datatype.metadata_spec.items():
                    # We need to be careful about the attributes we are resetting
                    if name != 'name' and name != 'info' and name != 'dbkey':
                        if spec.get( 'default' ):
                            setattr( dataset.metadata,name,spec.unwrap( spec.get( 'default' ), spec ))
                dataset.datatype.set_meta( dataset )
                dataset.datatype.after_edit( dataset )
                trans.app.model.flush()
                return trans.show_ok_message( "Attributes updated" )
            
            dataset.datatype.before_edit( dataset )
            # Get all actions to send to the form
            dataset_actions = []
            dpas = RBACAgent.permitted_actions
            for dpa in dpas.items():
                if dpa[0].startswith( 'DATASET' ):
                    dataset_actions.append( dpa[1] )
                dataset_actions.sort()
            # Get the permitted_actions of each GroupDatasetAssociation to send to the form
            gdas = []
            # Refresh the Dataset to ensure we have a valid set of GroupDatasetAssociations
            dataset.dataset.refresh()
            for group_dataset_assoc in dataset.dataset.groups:
                # Refresh the GroupDatasetAssociation to ensure we have a valid set of permitted_actions
                group_dataset_assoc.refresh()
                group = galaxy.model.Group.get( group_dataset_assoc.group_id )
                gdas.append( ( group.id, group.name, group_dataset_assoc.permitted_actions ) )
            if "dbkey" in dataset.datatype.metadata_spec and not dataset.metadata.dbkey:
                # Copy dbkey into metadata, for backwards compatability
                # This looks like it does nothing, but getting the dbkey
                # returns the metadata dbkey unless it is None, in which
                # case it resorts to the old dbkey.  Setting the dbkey
                # sets it properly in the metadata
                dataset.metadata.dbkey = dataset.dbkey
            metadata = list()
            # a list of MetadataParemeters
            for name, spec in dataset.datatype.metadata_spec.items():
                if spec.visible:
                    metadata.append( spec.wrap( dataset.metadata.get(name), dataset ) )
            # let's not overwrite the imported datatypes module with the variable datatypes?
            ldatatypes = [x for x in trans.app.datatypes_registry.datatypes_by_extension.iterkeys()]
            ldatatypes.sort()
            return trans.fill_template( "/admin/library/dataset.mako", 
                                        dataset=dataset, 
                                        metadata=metadata,
                                        datatypes=ldatatypes,
                                        dataset_actions=dataset_actions,
                                        gdas=gdas,
                                        err=None )
        else:
            return trans.show_error_message( "Invalid dataset specified" )
    def renderable( self, trans, component, group_id ):
        render = False
        if isinstance( component, trans.app.model.LibraryFolder ):
            # Check the folder's datasets to see what can be rendered
            for library_folder_dataset_assoc in component.datasets:
                if render:
                    break
                dataset = trans.app.model.Dataset.get( library_folder_dataset_assoc.dataset_id )
                for group_dataset_assoc in dataset.groups:
                    if group_dataset_assoc.group_id == group_id:
                        render = True
                        break
            # Check the folder's sub-folders to see what can be rendered
            if not render:
                for library_folder in component.folders:
                    self.renderable( trans, library_folder, group_id )
        elif isinstance( component, trans.app.model.LibraryFolderDatasetAssociation ):
            render = False
            dataset = trans.app.model.Dataset.get( component.dataset_id )
            for group_dataset_assoc in dataset.groups:
                if group_dataset_assoc.group_id == group_id:
                    render = True
                    break
        return render

