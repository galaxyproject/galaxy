from galaxy.web.base.controller import *
from galaxy.webapps.community import model
from galaxy.model.orm import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.util import inflector
from galaxy.util.shed_util import get_configured_ui
from common import *
from repository import RepositoryListGrid, CategoryListGrid

from galaxy import eggs
eggs.require('mercurial')
from mercurial import hg

import logging

log = logging.getLogger( __name__ )

class UserListGrid( grids.Grid ):
    # TODO: move this to an admin_common controller since it is virtually the same
    # in the galaxy webapp.
    class UserLoginColumn( grids.TextColumn ):
        def get_value( self, trans, grid, user ):
            return user.email
    class UserNameColumn( grids.TextColumn ):
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
    class StatusColumn( grids.GridColumn ):
        def get_value( self, trans, grid, user ):
            if user.purged:
                return "purged"
            elif user.deleted:
                return "deleted"
            return ""
    class EmailColumn( grids.GridColumn ):
        def filter( self, trans, user, query, column_filter ):
            if column_filter == 'All':
                return query
            return query.filter( and_( model.Tool.table.c.user_id == model.User.table.c.id,
                                       model.User.table.c.email == column_filter ) )
    # Grid definition
    webapp = "community"
    title = "Users"
    model_class = model.User
    template='/admin/user/grid.mako'
    default_sort_key = "email"
    columns = [
        UserLoginColumn( "Email",
                     key="email",
                     link=( lambda item: dict( operation="information", id=item.id, webapp="community" ) ),
                     attach_popup=True,
                     filterable="advanced" ),
        UserNameColumn( "User Name",
                        key="username",
                        attach_popup=False,
                        filterable="advanced" ),
        GroupsColumn( "Groups", attach_popup=False ),
        RolesColumn( "Roles", attach_popup=False ),
        ExternalColumn( "External", attach_popup=False ),
        LastLoginColumn( "Last Login", format=time_ago ),
        StatusColumn( "Status", attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        EmailColumn( "Email",
                     key="email",
                     visible=False )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    global_actions = [
        grids.GridAction( "Create new user",
                          dict( controller='admin', action='users', operation='create', webapp="community" ) )
    ]
    operations = [
        grids.GridOperation( "Manage Roles and Groups",
                             condition=( lambda item: not item.deleted ),
                             allow_multiple=False,
                             url_args=dict( webapp="community", action="manage_roles_and_groups_for_user" ) ),
        grids.GridOperation( "Reset Password",
                             condition=( lambda item: not item.deleted ),
                             allow_multiple=True,
                             allow_popup=False,
                             url_args=dict( webapp="community", action="reset_user_password" ) )
    ]
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True, purged=False ) ),
        grids.GridColumnFilter( "Purged", args=dict( purged=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def get_current_item( self, trans, **kwargs ):
        return trans.user

class RoleListGrid( grids.Grid ):
    # TODO: move this to an admin_common controller since it is virtually the same
    # in the galaxy webapp.
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, role ):
            return role.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, role ):
            if role.description:
                return role.description
            return ''
    class TypeColumn( grids.TextColumn ):
        def get_value( self, trans, grid, role ):
            return role.type
    class StatusColumn( grids.GridColumn ):
        def get_value( self, trans, grid, role ):
            if role.deleted:
                return "deleted"
            return ""
    class GroupsColumn( grids.GridColumn ):
        def get_value( self, trans, grid, role ):
            if role.groups:
                return len( role.groups )
            return 0
    class UsersColumn( grids.GridColumn ):
        def get_value( self, trans, grid, role ):
            if role.users:
                return len( role.users )
            return 0

    # Grid definition
    webapp = "community"
    title = "Roles"
    model_class = model.Role
    template='/admin/dataset_security/role/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    link=( lambda item: dict( operation="Manage users and groups", id=item.id, webapp="community" ) ),
                    attach_popup=True,
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                           key='description',
                           attach_popup=False,
                           filterable="advanced" ),
        TypeColumn( "Type",
                    key='type',
                    attach_popup=False,
                    filterable="advanced" ),
        GroupsColumn( "Groups", attach_popup=False ),
        UsersColumn( "Users", attach_popup=False ),
        StatusColumn( "Status", attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted",
                             key="deleted",
                             visible=False,
                             filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1], columns[2] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    global_actions = [
        grids.GridAction( "Add new role",
                          dict( controller='admin', action='roles', operation='create', webapp="community" ) )
    ]
    operations = [ grids.GridOperation( "Rename",
                                        condition=( lambda item: not item.deleted ),
                                        allow_multiple=False,
                                        url_args=dict( webapp="community", action="rename_role" ) ),
                   grids.GridOperation( "Delete",
                                        condition=( lambda item: not item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="community", action="mark_role_deleted" ) ),
                   grids.GridOperation( "Undelete",
                                        condition=( lambda item: item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="community", action="undelete_role" ) ),
                   grids.GridOperation( "Purge",
                                        condition=( lambda item: item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="community", action="purge_role" ) ) ]
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def apply_query_filter( self, trans, query, **kwd ):
        return query.filter( model.Role.type != model.Role.types.PRIVATE )

class GroupListGrid( grids.Grid ):
    # TODO: move this to an admin_common controller since it is virtually the same
    # in the galaxy webapp.
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, group ):
            return group.name
    class StatusColumn( grids.GridColumn ):
        def get_value( self, trans, grid, group ):
            if group.deleted:
                return "deleted"
            return ""
    class RolesColumn( grids.GridColumn ):
        def get_value( self, trans, grid, group ):
            if group.roles:
                return len( group.roles )
            return 0
    class UsersColumn( grids.GridColumn ):
        def get_value( self, trans, grid, group ):
            if group.members:
                return len( group.members )
            return 0

    # Grid definition
    webapp = "community"
    title = "Groups"
    model_class = model.Group
    template='/admin/dataset_security/group/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    #key="name",
                    link=( lambda item: dict( operation="Manage users and roles", id=item.id, webapp="community" ) ),
                    attach_popup=True
                    #filterable="advanced"
                    ),
        UsersColumn( "Users", attach_popup=False ),
        RolesColumn( "Roles", attach_popup=False ),
        StatusColumn( "Status", attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted",
                             key="deleted",
                             visible=False,
                             filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[1], columns[2] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    global_actions = [
        grids.GridAction( "Add new group",
                          dict( controller='admin', action='groups', operation='create', webapp="community" ) )
    ]
    operations = [ grids.GridOperation( "Rename",
                                        condition=( lambda item: not item.deleted ),
                                        allow_multiple=False,
                                        url_args=dict( webapp="community", action="rename_group" ) ),
                   grids.GridOperation( "Delete",
                                        condition=( lambda item: not item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="community", action="mark_group_deleted" ) ),
                   grids.GridOperation( "Undelete",
                                        condition=( lambda item: item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="community", action="undelete_group" ) ),
                   grids.GridOperation( "Purge",
                                        condition=( lambda item: item.deleted ),
                                        allow_multiple=True,
                                        url_args=dict( webapp="community", action="purge_group" ) ) ]
    standard_filters = [
        grids.GridColumnFilter( "Active", args=dict( deleted=False ) ),
        grids.GridColumnFilter( "Deleted", args=dict( deleted=True ) ),
        grids.GridColumnFilter( "All", args=dict( deleted='All' ) )
    ]
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True

class ManageCategoryListGrid( CategoryListGrid ):
    columns = [ col for col in CategoryListGrid.columns ]
    # Override the NameColumn to include an Edit link
    columns[ 0 ] = CategoryListGrid.NameColumn( "Name",
                                                key="Category.name",
                                                link=( lambda item: dict( operation="Edit", id=item.id, webapp="community" ) ),
                                                model_class=model.Category,
                                                attach_popup=False )
    global_actions = [
        grids.GridAction( "Add new category",
                          dict( controller='admin', action='manage_categories', operation='create', webapp="community" ) )
    ]

class AdminRepositoryListGrid( RepositoryListGrid ):
    operations = [ operation for operation in RepositoryListGrid.operations ]
    operations.append( grids.GridOperation( "Delete",
                                            allow_multiple=False,
                                            condition=( lambda item: not item.deleted ),
                                            async_compatible=False ) )
    operations.append( grids.GridOperation( "Undelete",
                                            allow_multiple=False,
                                            condition=( lambda item: item.deleted ),
                                            async_compatible=False ) )
    standard_filters = []

class RepositoryMetadataListGrid( grids.Grid ):
    class IdColumn( grids.IntegerColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            return repository_metadata.id
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            return repository_metadata.repository.name
    class RevisionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            repository = repository_metadata.repository
            repo = hg.repository( get_configured_ui(), repository.repo_path )
            ctx = get_changectx_for_changeset( repo, repository_metadata.changeset_revision )
            return "%s:%s" % ( str( ctx.rev() ), repository_metadata.changeset_revision )
    class ToolsColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            tools_str = ''
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    if 'tools' in metadata:
                        for tool_metadata_dict in metadata[ 'tools' ]:
                            tools_str += '%s <b>%s</b><br/>' % ( tool_metadata_dict[ 'id' ], tool_metadata_dict[ 'version' ] )
            return tools_str
    class DatatypesColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            datatypes_str = ''
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    if 'datatypes' in metadata:
                        for datatype_metadata_dict in metadata[ 'datatypes' ]:
                            datatypes_str += '%s<br/>' % datatype_metadata_dict[ 'extension' ]
            return datatypes_str
    class WorkflowsColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            workflows_str = ''
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    if 'workflows' in metadata:
                        workflows_str += '<b>Workflows:</b><br/>'
                        # metadata[ 'workflows' ] is a list of tuples where each contained tuple is
                        # [ <relative path to the .ga file in the repository>, <exported workflow dict> ]
                        workflow_tups = metadata[ 'workflows' ]
                        workflow_metadata_dicts = [ workflow_tup[1] for workflow_tup in workflow_tups ]
                        for workflow_metadata_dict in workflow_metadata_dicts:
                            workflows_str += '%s<br/>' % workflow_metadata_dict[ 'name' ]
            return workflows_str
    class MaliciousColumn( grids.BooleanColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            return repository_metadata.malicious
    # Grid definition
    title = "Repository Metadata"
    model_class = model.RepositoryMetadata
    template='/webapps/community/repository/grid.mako'
    default_sort_key = "name"
    columns = [
        IdColumn( "Id",
                  visible=False,
                  attach_popup=False ),
        NameColumn( "Name",
                    key="name",
                    model_class=model.Repository,
                    link=( lambda item: dict( operation="view_or_manage_repository_revision",
                                              id=item.id,
                                              webapp="community" ) ),
                    attach_popup=True ),
        RevisionColumn( "Revision",
                        attach_popup=False ),
        ToolsColumn( "Tools",
                     attach_popup=False ),
        DatatypesColumn( "Datatypes",
                         attach_popup=False ),
        WorkflowsColumn( "Workflows",
                         attach_popup=False ),
        MaliciousColumn( "Malicious",
                         attach_popup=False )
    ]
    operations = [ grids.GridOperation( "Delete",
                                        allow_multiple=False,
                                        allow_popup=True,
                                        async_compatible=False,
                                        confirm="Repository metadata records cannot be recovered after they are deleted. Click OK to delete the selected items." ) ]
    standard_filters = []
    default_filter = {}
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( self.model_class ) \
                               .join( model.Repository.table )

class AdminController( BaseUIController, Admin ):
    
    user_list_grid = UserListGrid()
    role_list_grid = RoleListGrid()
    group_list_grid = GroupListGrid()
    manage_category_list_grid = ManageCategoryListGrid()
    repository_list_grid = AdminRepositoryListGrid()
    repository_metadata_list_grid = RepositoryMetadataListGrid()

    @web.expose
    @web.require_admin
    def browse_repository_metadata( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd[ 'operation' ].lower()
            if operation == "delete":
                return self.delete_repository_metadata( trans, **kwd )
            if operation == "view_or_manage_repository_revision":
                # The received id is a RepositoryMetadata object id, so we need to get the
                # associated Repository and redirect to view_or_manage_repository with the
                # changeset_revision.
                repository_metadata = get_repository_metadata_by_id( trans, kwd[ 'id' ] )
                repository = repository_metadata.repository
                kwd[ 'id' ] = trans.security.encode_id( repository.id )
                kwd[ 'changeset_revision' ] = repository_metadata.changeset_revision
                kwd[ 'operation' ] = 'view_or_manage_repository'
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='browse_repositories',
                                                                  **kwd ) )
        return self.repository_metadata_list_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def delete_repository_metadata( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = kwd.get( 'id', None )
        if id:
            ids = util.listify( id )
            count = 0
            for repository_metadata_id in ids:
                repository_metadata = get_repository_metadata_by_id( trans, repository_metadata_id )
                trans.sa_session.delete( repository_metadata )
                trans.sa_session.flush()
                count += 1
            if count:
                message = "Deleted %d repository metadata %s" % ( count, inflector.cond_plural( len( ids ), "record" ) )
        else:
            message = "No repository metadata ids received for deleting."
            status = 'error'
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='browse_repository_metadata',
                                                   message=util.sanitize_text( message ),
                                                   status=status ) )
    @web.expose
    @web.require_admin
    def reset_all_repository_metadata( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if 'reset_all_repository_metadata_button' in kwd:
            count = 0
            for repository in trans.sa_session.query( trans.model.Repository ) \
                                              .filter( trans.model.Repository.table.c.deleted == False ):
                try:
                    reset_all_repository_metadata( trans, trans.security.encode_id( repository.id ) )
                    log.debug( "Reset metadata on repository %s" % repository.name )
                    count += 1
                except Exception, e:
                    log.debug( "Error attempting to reset metadata on repository %s: %s" % ( repository.name, str( e ) ) )
            message = "Reset metadata on %d repositories" % count
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='browse_repository_metadata',
                                                       webapp='community',
                                                       message=util.sanitize_text( message ),
                                                       status=status ) )
        return trans.fill_template( '/webapps/community/admin/reset_all_repository_metadata.mako',
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def browse_repositories( self, trans, **kwd ):
        # We add params to the keyword dict in this method in order to rename the param
        # with an "f-" prefix, simulating filtering by clicking a search link.  We have
        # to take this approach because the "-" character is illegal in HTTP requests.
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "view_or_manage_repository":
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='browse_repositories',
                                                                  **kwd ) )
            elif operation == "edit_repository":
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='edit_repository',
                                                                  **kwd ) )
            elif operation == "repositories_by_user":
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                if 'user_id' in kwd:
                    user = get_user( trans, kwd[ 'user_id' ] )
                    kwd[ 'f-email' ] = user.email
                    del kwd[ 'user_id' ]
                else:
                    # The received id is the repository id, so we need to get the id of the user
                    # that uploaded the repository.
                    repository_id = kwd.get( 'id', None )
                    repository = get_repository( trans, repository_id )
                    kwd[ 'f-email' ] = repository.user.email
            elif operation == "repositories_by_category":
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                category_id = kwd.get( 'id', None )
                category = get_category( trans, category_id )
                kwd[ 'f-Category.name' ] = category.name
            elif operation == "receive email alerts":
                if kwd[ 'id' ]:
                    kwd[ 'caller' ] = 'browse_repositories'
                    return trans.response.send_redirect( web.url_for( controller='repository',
                                                                      action='set_email_alerts',
                                                                      **kwd ) )
                else:
                    del kwd[ 'operation' ]
            elif operation == 'delete':
                return self.delete_repository( trans, **kwd )
            elif operation == "undelete":
                return self.undelete_repository( trans, **kwd )
        # The changeset_revision_select_field in the RepositoryListGrid performs a refresh_on_change
        # which sends in request parameters like changeset_revison_1, changeset_revision_2, etc.  One
        # of the many select fields on the grid performed the refresh_on_change, so we loop through 
        # all of the received values to see which value is not the repository tip.  If we find it, we
        # know the refresh_on_change occurred, and we have the necessary repository id and change set
        # revision to pass on.
        for k, v in kwd.items():
            changset_revision_str = 'changeset_revision_'
            if k.startswith( changset_revision_str ):
                repository_id = trans.security.encode_id( int( k.lstrip( changset_revision_str ) ) )
                repository = get_repository( trans, repository_id )
                if repository.tip != v:
                    return trans.response.send_redirect( web.url_for( controller='repository',
                                                                      action='browse_repositories',
                                                                      operation='view_or_manage_repository',
                                                                      id=trans.security.encode_id( repository.id ),
                                                                      changeset_revision=v ) )
        # Render the list view
        return self.repository_list_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def regenerate_statistics( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if 'regenerate_statistics_button' in kwd:
            trans.app.shed_counter.generate_statistics()
            message = "Successfully regenerated statistics"
        return trans.fill_template( '/webapps/community/admin/statistics.mako',
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def delete_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = kwd.get( 'id', None )
        if id:
            # Deleting multiple items is currently not allowed (allow_multiple=False), so there will only be 1 id. 
            ids = util.listify( id )
            count = 0
            deleted_repositories = ""
            for repository_id in ids:
                repository = get_repository( trans, repository_id )
                if not repository.deleted:
                    repository.deleted = True
                    trans.sa_session.add( repository )
                    trans.sa_session.flush()
                    count += 1
                    deleted_repositories += " %s " % repository.name
            if count:
                message = "Deleted %d %s: %s" % ( count, inflector.cond_plural( len( ids ), "repository" ), deleted_repositories )
            else:
                message = "All selected repositories were already marked deleted."
        else:
            message = "No repository ids received for deleting."
            status = 'error'
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='browse_repositories',
                                                   message=util.sanitize_text( message ),
                                                   status=status ) )
    @web.expose
    @web.require_admin
    def undelete_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = kwd.get( 'id', None )
        if id:
            # Undeleting multiple items is currently not allowed (allow_multiple=False), so there will only be 1 id.
            ids = util.listify( id )
            count = 0
            undeleted_repositories = ""
            for repository_id in ids:
                repository = get_repository( trans, repository_id )
                if repository.deleted:
                    repository.deleted = False
                    trans.sa_session.add( repository )
                    trans.sa_session.flush()
                    count += 1
                    undeleted_repositories += " %s" % repository.name
            if count:
                message = "Undeleted %d %s: %s" % ( count, inflector.cond_plural( count, "repository" ), undeleted_repositories )
            else:
                message = "No selected repositories were marked deleted, so they could not be undeleted."
        else:
            message = "No repository ids received for undeleting."
            status = 'error'
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='browse_repositories',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )
    @web.expose
    @web.require_admin
    def manage_categories( self, trans, **kwd ):
        if 'f-free-text-search' in kwd:
            # Trick to enable searching repository name, description from the CategoryListGrid.
            # What we've done is rendered the search box for the RepositoryListGrid on the grid.mako
            # template for the CategoryListGrid.  See ~/templates/webapps/community/category/grid.mako.
            # Since we are searching repositories and not categories, redirect to browse_repositories().
            return self.browse_repositories( trans, **kwd )
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "create":
                return self.create_category( trans, **kwd )
            elif operation == "delete":
                return self.mark_category_deleted( trans, **kwd )
            elif operation == "undelete":
                return self.undelete_category( trans, **kwd )
            elif operation == "purge":
                return self.purge_category( trans, **kwd )
            elif operation == "edit":
                return self.edit_category( trans, **kwd )
        # Render the list view
        return self.manage_category_list_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def create_category( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if params.get( 'create_category_button', False ):
            name = util.restore_text( params.name )
            description = util.restore_text( params.description )
            error = False
            if not name or not description:
                message = 'Enter a valid name and a description'
                error = True
            elif trans.sa_session.query( trans.app.model.Category ) \
                                 .filter( trans.app.model.Category.table.c.name==name ) \
                                 .first():
                message = 'A category with that name already exists'
                error = True
            if error:
                return trans.fill_template( '/webapps/community/category/create_category.mako',
                                            name=name,
                                            description=description,
                                            message=message,
                                            status='error' )
            else:
                # Create the category
                category = trans.app.model.Category( name=name, description=description )
                trans.sa_session.add( category )
                message = "Category '%s' has been created" % category.name
                trans.sa_session.flush()
                trans.response.send_redirect( web.url_for( controller='admin',
                                                           action='manage_categories',
                                                           message=util.sanitize_text( message ),
                                                           status='done' ) )
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='create_category',
                                                       message=util.sanitize_text( message ),
                                                       status='error' ) )
        else:
            name = ''
            description = ''
        return trans.fill_template( '/webapps/community/category/create_category.mako',
                                    name=name,
                                    description=description,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def edit_category( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            message = "No category ids received for editing"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='manage_categories',
                                                       message=message,
                                                       status='error' ) )
        category = get_category( trans, id )
        if params.get( 'edit_category_button', False ):
            new_name = util.restore_text( params.get( 'name', '' ) ).strip()
            new_description = util.restore_text( params.get( 'description', '' ) ).strip()
            if category.name != new_name or category.description != new_description:
                if not new_name:
                    message = 'Enter a valid name'
                    status = 'error'
                elif category.name != new_name and \
                    trans.sa_session.query( trans.app.model.Category ).filter( trans.app.model.Category.table.c.name==new_name ).first():
                    message = 'A category with that name already exists'
                    status = 'error'
                else:
                    category.name = new_name
                    category.description = new_description
                    trans.sa_session.add( category )
                    trans.sa_session.flush()
                    message = "The information has been saved for category '%s'" % ( category.name )
                    return trans.response.send_redirect( web.url_for( controller='admin',
                                                                      action='manage_categories',
                                                                      message=util.sanitize_text( message ),
                                                                      status='done' ) )
        return trans.fill_template( '/webapps/community/category/edit_category.mako',
                                    category=category,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def mark_category_deleted( self, trans, **kwd ):
        # TODO: We should probably eliminate the Category.deleted column since it really makes no
        # sense to mark a category as deleted (category names and descriptions can be changed instead).
        # If we do this, and the following 2 methods can be eliminated.
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = kwd.get( 'id', None )
        if id:
            ids = util.listify( id )
            message = "Deleted %d categories: " % len( ids )
            for category_id in ids:
                category = get_category( trans, category_id )
                category.deleted = True
                trans.sa_session.add( category )
                trans.sa_session.flush()
                message += " %s " % category.name
        else:
            message = "No category ids received for deleting."
            status = 'error'
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='manage_categories',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )
    @web.expose
    @web.require_admin
    def undelete_category( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = kwd.get( 'id', None )
        if id:
            ids = util.listify( id )
            count = 0
            undeleted_categories = ""
            for category_id in ids:
                category = get_category( trans, category_id )
                if category.deleted:
                    category.deleted = False
                    trans.sa_session.add( category )
                    trans.sa_session.flush()
                    count += 1
                    undeleted_categories += " %s" % category.name
            message = "Undeleted %d categories: %s" % ( count, undeleted_categories )
        else:
            message = "No category ids received for undeleting."
            status = 'error'
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='manage_categories',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )
    @web.expose
    @web.require_admin
    def purge_category( self, trans, **kwd ):
        # This method should only be called for a Category that has previously been deleted.
        # Purging a deleted Category deletes all of the following from the database:
        # - RepoitoryCategoryAssociations where category_id == Category.id
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = kwd.get( 'id', None )
        if id:
            ids = util.listify( id )
            count = 0
            purged_categories = ""
            message = "Purged %d categories: " % len( ids )
            for category_id in ids:
                category = get_category( trans, category_id )
                if category.deleted:
                    # Delete RepositoryCategoryAssociations
                    for rca in category.repositories:
                        trans.sa_session.delete( rca )
                    trans.sa_session.flush()
                    purged_categories += " %s " % category.name
            message = "Purged %d categories: %s" % ( count, purged_categories )
        else:
            message = "No category ids received for purging."
            status = 'error'
        trans.response.send_redirect( web.url_for( controller='admin',
                                                   action='manage_categories',
                                                   message=util.sanitize_text( message ),
                                                   status='done' ) )
