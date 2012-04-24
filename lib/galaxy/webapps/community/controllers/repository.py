import os, logging, tempfile, shutil
from time import strftime
from datetime import date, datetime
from galaxy import util
from galaxy.datatypes.checkers import *
from galaxy.web.base.controller import *
from galaxy.web.form_builder import CheckboxField
from galaxy.webapps.community import model
from galaxy.webapps.community.model import directory_hash_id
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.util.json import from_json_string, to_json_string
from galaxy.model.orm import *
from galaxy.util.shed_util import get_configured_ui
from common import *

from galaxy import eggs
eggs.require('mercurial')
from mercurial import hg, ui, patch, commands

log = logging.getLogger( __name__ )

MAX_CONTENT_SIZE = 32768
VALID_REPOSITORYNAME_RE = re.compile( "^[a-z0-9\_]+$" )
    
class CategoryListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            return category.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            return category.description
    class RepositoriesColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            if category.repositories:
                viewable_repositories = 0
                for rca in category.repositories:
                    viewable_repositories += 1
                return viewable_repositories
            return 0

    # Grid definition
    webapp = "community"
    title = "Categories"
    model_class = model.Category
    template='/webapps/community/category/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="Category.name",
                    link=( lambda item: dict( operation="repositories_by_category", id=item.id, webapp="community" ) ),
                    attach_popup=False ),
        DescriptionColumn( "Description",
                           key="Category.description",
                           attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        RepositoriesColumn( "Repositories",
                            model_class=model.Repository,
                            attach_popup=False )
    ]
    # Override these
    default_filter = {}
    global_actions = []
    operations = []
    standard_filters = []
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True

class RepositoryListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository ):
            return repository.name
    class RevisionColumn( grids.GridColumn ):
        def __init__( self, col_name ):
            grids.GridColumn.__init__( self, col_name )
        def get_value( self, trans, grid, repository ):
            """
            Display a SelectField whose options are the changeset_revision
            strings of all downloadable_revisions of this repository.
            """
            select_field = build_changeset_revision_select_field( trans, repository )
            if len( select_field.options ) > 1:
                return select_field.get_html()
            return repository.revision
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository ):
            return repository.description
    class CategoryColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository ):
            rval = '<ul>'
            if repository.categories:
                for rca in repository.categories:
                    rval += '<li><a href="browse_repositories?operation=repositories_by_category&id=%s&webapp=community">%s</a></li>' \
                        % ( trans.security.encode_id( rca.category.id ), rca.category.name )
            else:
                rval += '<li>not set</li>'
            rval += '</ul>'
            return rval
    class RepositoryCategoryColumn( grids.GridColumn ):
        def filter( self, trans, user, query, column_filter ):
            """Modify query to filter by category."""
            if column_filter == "All":
                return query
            return query.filter( model.Category.name == column_filter )
    class UserColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository ):
            if repository.user:
                return repository.user.username
            return 'no user'
    class EmailColumn( grids.TextColumn ):
        def filter( self, trans, user, query, column_filter ):
            if column_filter == 'All':
                return query
            return query.filter( and_( model.Repository.table.c.user_id == model.User.table.c.id,
                                       model.User.table.c.email == column_filter ) )
    class EmailAlertsColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository ):
            if trans.user and repository.email_alerts and trans.user.email in from_json_string( repository.email_alerts ):
                return 'yes'
            return ''
    # Grid definition
    title = "Repositories"
    model_class = model.Repository
    template='/webapps/community/repository/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    link=( lambda item: dict( operation="view_or_manage_repository",
                                              id=item.id,
                                              webapp="community" ) ),
                    attach_popup=True ),
        DescriptionColumn( "Synopsis",
                           key="description",
                           attach_popup=False ),
        RevisionColumn( "Revision" ),
        CategoryColumn( "Category",
                        model_class=model.Category,
                        key="Category.name",
                        attach_popup=False ),
        UserColumn( "Owner",
                     model_class=model.User,
                     link=( lambda item: dict( operation="repositories_by_user", id=item.id, webapp="community" ) ),
                     attach_popup=False,
                     key="User.username" ),
        grids.CommunityRatingColumn( "Average Rating", key="rating" ),
        EmailAlertsColumn( "Alert", attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        EmailColumn( "Email",
                     model_class=model.User,
                     key="email",
                     visible=False ),
        RepositoryCategoryColumn( "Category",
                                  model_class=model.Category,
                                  key="Category.name",
                                  visible=False ),
        grids.DeletedColumn( "Deleted",
                             key="deleted",
                             visible=False,
                             filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name, description", 
                                                cols_to_filter=[ columns[0], columns[1] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [ grids.GridOperation( "Receive email alerts",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted ),
                                        async_compatible=False ) ]
    standard_filters = []
    default_filter = dict( deleted="False" )
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( self.model_class ) \
                               .join( model.User.table ) \
                               .outerjoin( model.RepositoryCategoryAssociation.table ) \
                               .outerjoin( model.Category.table )

class EmailAlertsRepositoryListGrid( RepositoryListGrid ):
    columns = [
        RepositoryListGrid.NameColumn( "Name",
                                       key="name",
                                       link=( lambda item: dict( operation="view_or_manage_repository",
                                                                 id=item.id,
                                                                 webapp="community" ) ),
                                       attach_popup=False ),
        RepositoryListGrid.DescriptionColumn( "Synopsis",
                                              key="description",
                                              attach_popup=False ),
        RepositoryListGrid.UserColumn( "Owner",
                                       model_class=model.User,
                                       link=( lambda item: dict( operation="repositories_by_user", id=item.id, webapp="community" ) ),
                                       attach_popup=False,
                                       key="User.username" ),
        RepositoryListGrid.EmailAlertsColumn( "Alert", attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted",
                             key="deleted",
                             visible=False,
                             filterable="advanced" )
    ]
    operations = [ grids.GridOperation( "Receive email alerts",
                                        allow_multiple=True,
                                        condition=( lambda item: not item.deleted ),
                                        async_compatible=False ) ]
    global_actions = [
            grids.GridAction( "User preferences", dict( controller='user', action='index', cntrller='repository', webapp='community' ) )
        ]

class ValidRepositoryListGrid( RepositoryListGrid ):
    class RevisionColumn( grids.GridColumn ):
        def __init__( self, col_name ):
            grids.GridColumn.__init__( self, col_name )
        def get_value( self, trans, grid, repository ):
            """
            Display a SelectField whose options are the changeset_revision
            strings of all download-able revisions of this repository.
            """
            select_field = build_changeset_revision_select_field( trans, repository )
            if len( select_field.options ) > 1:
                return select_field.get_html()
            return repository.revision
    title = "Valid repositories"
    columns = [
        RepositoryListGrid.NameColumn( "Name",
                                       key="name",
                                       attach_popup=True ),
        RepositoryListGrid.DescriptionColumn( "Synopsis",
                                              key="description",
                                              attach_popup=False ),
        RevisionColumn( "Revision" ),
        RepositoryListGrid.UserColumn( "Owner",
                                       model_class=model.User,
                                       attach_popup=False,
                                       key="User.username" )
    ]
    operations = []
    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( self.model_class ) \
                               .join( model.RepositoryMetadata.table ) \
                               .join( model.User.table )

class MatchedRepositoryListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            return repository_metadata.repository.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            return repository_metadata.repository.description
    class RevisionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            return repository_metadata.changeset_revision
    class UserColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            if repository_metadata.repository.user:
                return repository_metadata.repository.user.username
            return 'no user'
    # Grid definition
    title = "Matching repositories"
    model_class = model.RepositoryMetadata
    template='/webapps/community/repository/grid.mako'
    default_sort_key = "Repository.name"
    columns = [
        NameColumn( "Repository name",
                    link=( lambda item: dict( operation="view_or_manage_repository",
                                              id=item.id,
                                              webapp="community" ) ),
                    attach_popup=True ),
        DescriptionColumn( "Synopsis",
                           attach_popup=False ),
        RevisionColumn( "Revision" ),
        UserColumn( "Owner",
                     model_class=model.User,
                     attach_popup=False )
    ]
    operations = []
    standard_filters = []
    default_filter = {}
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, trans, **kwd ):
        match_tuples = kwd.get( 'match_tuples', [] )
        clause_list = []
        if match_tuples:
            for match_tuple in match_tuples:
                repository_id, changeset_revision = match_tuple
                clause_list.append( "%s=%d and %s='%s'" % ( self.model_class.table.c.repository_id,
                                                            int( repository_id ),
                                                            self.model_class.table.c.changeset_revision,
                                                            changeset_revision ) )
            return trans.sa_session.query( self.model_class ) \
                                   .join( model.Repository ) \
                                   .join( model.User.table ) \
                                   .filter( or_( *clause_list ) ) \
                                   .order_by( model.Repository.name )
        # Return an empty query
        return trans.sa_session.query( self.model_class ) \
                               .join( model.Repository ) \
                               .join( model.User.table ) \
                               .filter( self.model_class.table.c.repository_id == 0 )

class InstallMatchedRepositoryListGrid( MatchedRepositoryListGrid ):
    columns = [ col for col in MatchedRepositoryListGrid.columns ]
    # Override the NameColumn
    columns[ 0 ] = MatchedRepositoryListGrid.NameColumn( "Name",
                                                         link=( lambda item: dict( operation="view_or_manage_repository",
                                                                                   id=item.id,
                                                                                   webapp="galaxy" ) ),
                                                         attach_popup=False )

class RepositoryController( BaseUIController, ItemRatings ):

    install_matched_repository_list_grid = InstallMatchedRepositoryListGrid()
    matched_repository_list_grid = MatchedRepositoryListGrid()
    valid_repository_list_grid = ValidRepositoryListGrid()
    repository_list_grid = RepositoryListGrid()
    email_alerts_repository_list_grid = EmailAlertsRepositoryListGrid()
    category_list_grid = CategoryListGrid()

    @web.expose
    def index( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        # See if there are any RepositoryMetadata records since menu items require them.
        repository_metadata = trans.sa_session.query( model.RepositoryMetadata ).first()
        return trans.fill_template( '/webapps/community/index.mako',
                                    repository_metadata=repository_metadata,
                                    message=message,
                                    status=status )
    @web.expose
    def browse_categories( self, trans, **kwd ):
        if 'f-free-text-search' in kwd:
            # Trick to enable searching repository name, description from the CategoryListGrid.
            # What we've done is rendered the search box for the RepositoryListGrid on the grid.mako
            # template for the CategoryListGrid.  See ~/templates/webapps/community/category/grid.mako.
            # Since we are searching repositories and not categories, redirect to browse_repositories().
            if 'id' in kwd and 'f-free-text-search' in kwd and kwd[ 'id' ] == kwd[ 'f-free-text-search' ]:
                # The value of 'id' has been set to the search string, which is a repository name.
                # We'll try to get the desired encoded repository id to pass on.
                try:
                    repository = get_repository_by_name( trans, kwd[ 'id' ] )
                    kwd[ 'id' ] = trans.security.encode_id( repository.id )
                except:
                    pass
            return self.browse_repositories( trans, **kwd )
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation in [ "repositories_by_category", "repositories_by_user" ]:
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='browse_repositories',
                                                                  **kwd ) )
        # Render the list view
        return self.category_list_grid( trans, **kwd )
    @web.expose
    def browse_valid_repositories( self, trans, **kwd ):
        webapp = kwd.get( 'webapp', 'community' )
        galaxy_url = kwd.get( 'galaxy_url', None )
        if galaxy_url:
            trans.set_cookie( galaxy_url, name='toolshedgalaxyurl' )
        repository_id = kwd.get( 'id', None )
        if 'operation' in kwd:
            operation = kwd[ 'operation' ].lower()
            if operation == "preview_tools_in_changeset":
                repository = get_repository( trans, repository_id )
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='preview_tools_in_changeset',
                                                                  webapp=webapp,
                                                                  repository_id=repository_id,
                                                                  changeset_revision=repository.tip ) )
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
                                                                      action='preview_tools_in_changeset',
                                                                      webapp=webapp,
                                                                      repository_id=trans.security.encode_id( repository.id ),
                                                                      changeset_revision=v ) )
        url_args = dict( action='browse_valid_repositories',
                         operation='preview_tools_in_changeset',
                         webapp=webapp,
                         repository_id=repository_id )
        self.valid_repository_list_grid.operations = [ grids.GridOperation( "Preview and install",
                                                                            url_args=url_args,
                                                                            allow_multiple=False,
                                                                            async_compatible=False ) ]
        # Render the list view
        return self.valid_repository_list_grid( trans, **kwd )
    @web.expose
    def browse_invalid_tools( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        webapp = params.get( 'webapp', 'community' )
        cntrller = params.get( 'cntrller', 'repository' )
        is_admin = trans.user_is_admin()
        invalid_tools_dict = odict()
        if is_admin and cntrller == 'admin':
            for repository in trans.sa_session.query( trans.model.Repository ) \
                                              .filter( trans.model.Repository.table.c.deleted == False ) \
                                              .order_by( trans.model.Repository.table.c.name ):
                for downloadable_revision in repository.downloadable_revisions:
                    metadata = downloadable_revision.metadata
                    invalid_tools = metadata.get( 'invalid_tools', [] )
                    for invalid_tool_config in invalid_tools:
                        invalid_tools_dict[ invalid_tool_config ] = ( repository.id, repository.name, downloadable_revision.changeset_revision )
        else:
            for repository in trans.sa_session.query( trans.model.Repository ) \
                                              .filter( and_( trans.model.Repository.table.c.deleted == False,
                                                             trans.model.Repository.table.c.user_id == trans.user.id ) ) \
                                              .order_by( trans.model.Repository.table.c.name ):
                for downloadable_revision in repository.downloadable_revisions:
                    metadata = downloadable_revision.metadata
                    invalid_tools = metadata.get( 'invalid_tools', [] )
                    for invalid_tool_config in invalid_tools:
                        invalid_tools_dict[ invalid_tool_config ] = ( repository.id, repository.name, downloadable_revision.changeset_revision )
        return trans.fill_template( '/webapps/community/repository/browse_invalid_tools.mako',
                                    cntrller=cntrller,
                                    invalid_tools_dict=invalid_tools_dict,
                                    webapp=webapp,
                                    message=message,
                                    status=status )     
    @web.expose
    def find_workflows( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', '' ) )
        status = params.get( 'status', 'done' )
        webapp = params.get( 'webapp', 'community' )
        galaxy_url = kwd.get( 'galaxy_url', None )
        if galaxy_url:
            trans.set_cookie( galaxy_url, name='toolshedgalaxyurl' )
        if 'operation' in kwd:
            item_id = kwd.get( 'id', '' )
            if item_id:
                operation = kwd[ 'operation' ].lower()
                is_admin = trans.user_is_admin()
                if operation == "view_or_manage_repository":
                    # The received id is a RepositoryMetadata id, so we have to get the repository id.
                    repository_metadata = get_repository_metadata_by_id( trans, item_id )
                    repository_id = trans.security.encode_id( repository_metadata.repository.id )
                    repository = get_repository( trans, repository_id )
                    kwd[ 'id' ] = repository_id
                    kwd[ 'changeset_revision' ] = repository_metadata.changeset_revision
                    if webapp == 'community' and ( is_admin or repository.user == trans.user ):
                        a = 'manage_repository'
                    else:
                        a = 'view_repository'
                    return trans.response.send_redirect( web.url_for( controller='repository',
                                                                      action=a,
                                                                      **kwd ) )
                if operation == "install":
                    galaxy_url = trans.get_cookie( name='toolshedgalaxyurl' )
                    encoded_repo_info_dict, includes_tools = self.__encode_repo_info_dict( trans, webapp, util.listify( item_id ) )
                    url = '%sadmin_toolshed/install_repository?tool_shed_url=%s&webapp=%s&repo_info_dict=%s&includes_tools=%s' % \
                        ( galaxy_url, url_for( '/', qualified=True ), webapp, encoded_repo_info_dict, str( includes_tools ) )
                    return trans.response.send_redirect( url )
            else:
                # This can only occur when there is a multi-select grid with check boxes and an operation,
                # and the user clicked the operation button without checking any of the check boxes.
                return trans.show_error_message( "No items were selected." )
        if 'find_workflows_button' in kwd:
            workflow_names = [ item.lower() for item in util.listify( kwd.get( 'workflow_name', '' ) ) ]
            exact_matches = params.get( 'exact_matches', '' )
            exact_matches_checked = CheckboxField.is_checked( exact_matches )
            match_tuples = []
            ok = True
            if workflow_names:
                ok, match_tuples = self.__search_repository_metadata( trans, exact_matches_checked, workflow_names=workflow_names )
            else:
                ok, match_tuples = self.__search_repository_metadata( trans, exact_matches_checked, workflow_names=[], all_workflows=True )
            if ok:
                kwd[ 'match_tuples' ] = match_tuples
                # Render the list view
                if webapp == 'galaxy':
                    # Our initial request originated from a Galaxy instance.
                    global_actions = [ grids.GridAction( "Browse valid repositories",
                                                         dict( controller='repository', action='browse_valid_repositories', webapp=webapp ) ),
                                       grids.GridAction( "Search for valid tools",
                                                         dict( controller='repository', action='find_tools', webapp=webapp ) ),
                                       grids.GridAction( "Search for workflows",
                                                         dict( controller='repository', action='find_workflows', webapp=webapp ) ) ]
                    self.install_matched_repository_list_grid.global_actions = global_actions
                    install_url_args = dict( controller='repository', action='find_workflows', webapp=webapp )
                    operations = [ grids.GridOperation( "Install", url_args=install_url_args, allow_multiple=True, async_compatible=False ) ]
                    self.install_matched_repository_list_grid.operations = operations
                    return self.install_matched_repository_list_grid( trans, **kwd )
                else:
                    kwd[ 'message' ] = "workflow name: <b>%s</b><br/>exact matches only: <b>%s</b>" % \
                        ( self.__stringify( workflow_names ), str( exact_matches_checked ) )
                    self.matched_repository_list_grid.title = "Repositories with matching workflows"
                    return self.matched_repository_list_grid( trans, **kwd )
            else:
                message = "No search performed - each field must contain the same number of comma-separated items."
                status = "error"
        else:
            exact_matches_checked = False
            workflow_names = []
        exact_matches_check_box = CheckboxField( 'exact_matches', checked=exact_matches_checked )
        return trans.fill_template( '/webapps/community/repository/find_workflows.mako',
                                    webapp=webapp,
                                    workflow_name=self.__stringify( workflow_names ),
                                    exact_matches_check_box=exact_matches_check_box,
                                    message=message,
                                    status=status )
    @web.expose
    def find_tools( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', '' ) )
        status = params.get( 'status', 'done' )
        webapp = params.get( 'webapp', 'community' )
        galaxy_url = kwd.get( 'galaxy_url', None )
        if galaxy_url:
            trans.set_cookie( galaxy_url, name='toolshedgalaxyurl' )
        if 'operation' in kwd:
            item_id = kwd.get( 'id', '' )
            if item_id:
                operation = kwd[ 'operation' ].lower()
                is_admin = trans.user_is_admin()
                if operation == "view_or_manage_repository":
                    # The received id is a RepositoryMetadata id, so we have to get the repository id.
                    repository_metadata = get_repository_metadata_by_id( trans, item_id )
                    repository_id = trans.security.encode_id( repository_metadata.repository.id )
                    repository = get_repository( trans, repository_id )
                    kwd[ 'id' ] = repository_id
                    kwd[ 'changeset_revision' ] = repository_metadata.changeset_revision
                    if webapp == 'community' and ( is_admin or repository.user == trans.user ):
                        a = 'manage_repository'
                    else:
                        a = 'view_repository'
                    return trans.response.send_redirect( web.url_for( controller='repository',
                                                                      action=a,
                                                                      **kwd ) )
                if operation == "install":
                    galaxy_url = trans.get_cookie( name='toolshedgalaxyurl' )
                    encoded_repo_info_dict, includes_tools = self.__encode_repo_info_dict( trans, webapp, util.listify( item_id ) )
                    url = '%sadmin_toolshed/install_repository?tool_shed_url=%s&webapp=%s&repo_info_dict=%s&includes_tools=%s' % \
                        ( galaxy_url, url_for( '/', qualified=True ), webapp, encoded_repo_info_dict, str( includes_tools ) )
                    return trans.response.send_redirect( url )
            else:
                # This can only occur when there is a multi-select grid with check boxes and an operation,
                # and the user clicked the operation button without checking any of the check boxes.
                return trans.show_error_message( "No items were selected." )
        tool_ids = [ item.lower() for item in util.listify( kwd.get( 'tool_id', '' ) ) ]
        tool_names = [ item.lower() for item in util.listify( kwd.get( 'tool_name', '' ) ) ]
        tool_versions = [ item.lower() for item in util.listify( kwd.get( 'tool_version', '' ) ) ]
        exact_matches = params.get( 'exact_matches', '' )
        exact_matches_checked = CheckboxField.is_checked( exact_matches )
        match_tuples = []
        ok = True
        if tool_ids or tool_names or tool_versions:
            ok, match_tuples = self.__search_repository_metadata( trans, exact_matches_checked, tool_ids=tool_ids, tool_names=tool_names, tool_versions=tool_versions )
            if ok:
                kwd[ 'match_tuples' ] = match_tuples
                # Render the list view
                if webapp == 'galaxy':
                    # Our initial request originated from a Galaxy instance.
                    global_actions = [ grids.GridAction( "Browse valid repositories",
                                                         dict( controller='repository', action='browse_valid_repositories', webapp=webapp ) ),
                                       grids.GridAction( "Search for valid tools",
                                                         dict( controller='repository', action='find_tools', webapp=webapp ) ),
                                       grids.GridAction( "Search for workflows",
                                                         dict( controller='repository', action='find_workflows', webapp=webapp ) ) ]
                    self.install_matched_repository_list_grid.global_actions = global_actions
                    install_url_args = dict( controller='repository', action='find_tools', webapp=webapp )
                    operations = [ grids.GridOperation( "Install", url_args=install_url_args, allow_multiple=True, async_compatible=False ) ]
                    self.install_matched_repository_list_grid.operations = operations
                    return self.install_matched_repository_list_grid( trans, **kwd )
                else:
                    kwd[ 'message' ] = "tool id: <b>%s</b><br/>tool name: <b>%s</b><br/>tool version: <b>%s</b><br/>exact matches only: <b>%s</b>" % \
                        ( self.__stringify( tool_ids ), self.__stringify( tool_names ), self.__stringify( tool_versions ), str( exact_matches_checked ) )
                    self.matched_repository_list_grid.title = "Repositories with matching tools"
                    return self.matched_repository_list_grid( trans, **kwd )
            else:
                message = "No search performed - each field must contain the same number of comma-separated items."
                status = "error"
        exact_matches_check_box = CheckboxField( 'exact_matches', checked=exact_matches_checked )
        return trans.fill_template( '/webapps/community/repository/find_tools.mako',
                                    webapp=webapp,
                                    tool_id=self.__stringify( tool_ids ),
                                    tool_name=self.__stringify( tool_names ),
                                    tool_version=self.__stringify( tool_versions ),
                                    exact_matches_check_box=exact_matches_check_box,
                                    message=message,
                                    status=status )
    def __search_repository_metadata( self, trans, exact_matches_checked, tool_ids='', tool_names='', tool_versions='', workflow_names='', all_workflows=False ):
        match_tuples = []
        ok = True
        for repository_metadata in trans.sa_session.query( model.RepositoryMetadata ):
            metadata = repository_metadata.metadata
            if tool_ids or tool_names or tool_versions:
                if 'tools' in metadata:
                    tools = metadata[ 'tools' ]
                else:
                    tools = []
                for tool_dict in tools:
                    if tool_ids and not tool_names and not tool_versions:
                        for tool_id in tool_ids:
                            if self.__in_tool_dict( tool_dict, exact_matches_checked, tool_id=tool_id ):
                                match_tuples.append( ( repository_metadata.repository_id, repository_metadata.changeset_revision ) )
                    elif tool_names and not tool_ids and not tool_versions:
                        for tool_name in tool_names:
                            if self.__in_tool_dict( tool_dict, exact_matches_checked, tool_name=tool_name ):
                                match_tuples.append( ( repository_metadata.repository_id, repository_metadata.changeset_revision ) )
                    elif tool_versions and not tool_ids and not tool_names:
                        for tool_version in tool_versions:
                            if self.__in_tool_dict( tool_dict, exact_matches_checked, tool_version=tool_version ):
                                match_tuples.append( ( repository_metadata.repository_id, repository_metadata.changeset_revision ) )
                    elif tool_ids and tool_names and not tool_versions:
                        if len( tool_ids ) == len( tool_names ):
                            match_tuples = self.__search_ids_names( tool_dict, exact_matches_checked, match_tuples, repository_metadata, tool_ids, tool_names )
                        elif len( tool_ids ) == 1 or len( tool_names ) == 1:
                            tool_ids, tool_names = self.__make_same_length( tool_ids, tool_names )
                            match_tuples = self.__search_ids_names( tool_dict, exact_matches_checked, match_tuples, repository_metadata, tool_ids, tool_names )
                        else:
                            ok = False
                    elif tool_ids and tool_versions and not tool_names:
                        if len( tool_ids )  == len( tool_versions ):
                            match_tuples = self.__search_ids_versions( tool_dict, exact_matches_checked, match_tuples, repository_metadata, tool_ids, tool_versions )
                        elif len( tool_ids ) == 1 or len( tool_versions ) == 1:
                            tool_ids, tool_versions = self.__make_same_length( tool_ids, tool_versions )
                            match_tuples = self.__search_ids_versions( tool_dict, exact_matches_checked, match_tuples, repository_metadata, tool_ids, tool_versions )
                        else:
                            ok = False
                    elif tool_versions and tool_names and not tool_ids:
                        if len( tool_versions ) == len( tool_names ):
                            match_tuples = self.__search_names_versions( tool_dict, exact_matches_checked, match_tuples, repository_metadata, tool_names, tool_versions )
                        elif len( tool_versions ) == 1 or len( tool_names ) == 1:
                            tool_versions, tool_names = self.__make_same_length( tool_versions, tool_names )
                            match_tuples = self.__search_names_versions( tool_dict, exact_matches_checked, match_tuples, repository_metadata, tool_names, tool_versions )
                        else:
                            ok = False
                    elif tool_versions and tool_names and tool_ids:
                        if len( tool_versions ) == len( tool_names ) and len( tool_names ) == len( tool_ids ):
                            for i, tool_version in enumerate( tool_versions ):
                                tool_name = tool_names[ i ]
                                tool_id = tool_ids[ i ]
                                if self.__in_tool_dict( tool_dict, exact_matches_checked, tool_id=tool_id, tool_name=tool_name, tool_version=tool_version ):
                                    match_tuples.append( ( repository_metadata.repository_id, repository_metadata.changeset_revision ) )
                        else:
                            ok = False
            elif workflow_names:
                if 'workflows' in metadata:
                    # metadata[ 'workflows' ] is a list of tuples where each contained tuple is
                    # [ <relative path to the .ga file in the repository>, <exported workflow dict> ]
                    workflow_tups = metadata[ 'workflows' ]
                    workflows = [ workflow_tup[1] for workflow_tup in workflow_tups ]
                else:
                    workflows = []
                for workflow_dict in workflows:
                    for workflow_name in workflow_names:
                        if self.__in_workflow_dict( workflow_dict, exact_matches_checked, workflow_name ):
                            match_tuples.append( ( repository_metadata.repository_id, repository_metadata.changeset_revision ) )
            elif all_workflows and 'workflows' in metadata:
                match_tuples.append( ( repository_metadata.repository_id, repository_metadata.changeset_revision ) )
        return ok, match_tuples
    def __in_workflow_dict( self, workflow_dict, exact_matches_checked, workflow_name ):
        workflow_dict_workflow_name = workflow_dict[ 'name' ].lower()
        return ( workflow_name == workflow_dict_workflow_name ) or \
               ( not exact_matches_checked and workflow_dict_workflow_name.find( workflow_name ) >= 0 )
    def __in_tool_dict( self, tool_dict, exact_matches_checked, tool_id=None, tool_name=None, tool_version=None ):
        found = False
        if tool_id and not tool_name and not tool_version:
            tool_dict_tool_id = tool_dict[ 'id' ].lower()
            found = ( tool_id == tool_dict_tool_id ) or \
                    ( not exact_matches_checked and tool_dict_tool_id.find( tool_id ) >= 0 )
        elif tool_name and not tool_id and not tool_version:
            tool_dict_tool_name = tool_dict[ 'name' ].lower()
            found = ( tool_name == tool_dict_tool_name ) or \
                    ( not exact_matches_checked and tool_dict_tool_name.find( tool_name ) >= 0 )
        elif tool_version and not tool_id and not tool_name:
            tool_dict_tool_version = tool_dict[ 'version' ].lower()
            found = ( tool_version == tool_dict_tool_version ) or \
                    ( not exact_matches_checked and tool_dict_tool_version.find( tool_version ) >= 0 )
        elif tool_id and tool_name and not tool_version:
            tool_dict_tool_id = tool_dict[ 'id' ].lower()
            tool_dict_tool_name = tool_dict[ 'name' ].lower()
            found = ( tool_id == tool_dict_tool_id and tool_name == tool_dict_tool_name ) or \
                    ( not exact_matches_checked and tool_dict_tool_id.find( tool_id ) >= 0 and tool_dict_tool_name.find( tool_name ) >= 0 )
        elif tool_id and tool_version and not tool_name:
            tool_dict_tool_id = tool_dict[ 'id' ].lower()
            tool_dict_tool_version = tool_dict[ 'version' ].lower()
            found = ( tool_id == tool_dict_tool_id and tool_version == tool_dict_tool_version ) or \
                    ( not exact_matches_checked and tool_dict_tool_id.find( tool_id ) >= 0 and tool_dict_tool_version.find( tool_version ) >= 0 )
        elif tool_version and tool_name and not tool_id:
            tool_dict_tool_version = tool_dict[ 'version' ].lower()
            tool_dict_tool_name = tool_dict[ 'name' ].lower()
            found = ( tool_version == tool_dict_tool_version and tool_name == tool_dict_tool_name ) or \
                    ( not exact_matches_checked and tool_dict_tool_version.find( tool_version ) >= 0 and tool_dict_tool_name.find( tool_name ) >= 0 )
        elif tool_version and tool_name and tool_id:
            tool_dict_tool_version = tool_dict[ 'version' ].lower()
            tool_dict_tool_name = tool_dict[ 'name' ].lower()
            tool_dict_tool_id = tool_dict[ 'id' ].lower()
            found = ( tool_version == tool_dict_tool_version and \
                      tool_name == tool_dict_tool_name and \
                      tool_id == tool_dict_tool_id ) or \
                    ( not exact_matches_checked and \
                      tool_dict_tool_version.find( tool_version ) >= 0 and \
                      tool_dict_tool_name.find( tool_name ) >= 0 and \
                      tool_dict_tool_id.find( tool_id ) >= 0 )
        return found
    def __stringify( self, list ):
        if list:
            return ','.join( list )
        return ''
    def __make_same_length( self, list1, list2 ):
        # If either list is 1 item, we'll append to it until its 
        # length is the same as the other.
        if len( list1 ) == 1:
            for i in range( 1, len( list2 ) ):
                list1.append( list1[ 0 ] )
        elif len( list2 ) == 1:
            for i in range( 1, len( list1 ) ):
                list2.append( list2[ 0 ] )
        return list1, list2
    def __search_ids_names( self, tool_dict, exact_matches_checked, match_tuples, repository_metadata, tool_ids, tool_names ):
        for i, tool_id in enumerate( tool_ids ):
            tool_name = tool_names[ i ]
            if self.__in_tool_dict( tool_dict, exact_matches_checked, tool_id=tool_id, tool_name=tool_name ):
                match_tuples.append( ( repository_metadata.repository_id, repository_metadata.changeset_revision ) )
        return match_tuples
    def __search_ids_versions( self, tool_dict, exact_matches_checked, match_tuples, repository_metadata, tool_ids, tool_versions ):
        for i, tool_id in enumerate( tool_ids ):
            tool_version = tool_versions[ i ]
            if self.__in_tool_dict( tool_dict, exact_matches_checked, tool_id=tool_id, tool_version=tool_version ):
                match_tuples.append( ( repository_metadata.repository_id, repository_metadata.changeset_revision ) )
        return match_tuples
    def __search_names_versions( self, tool_dict, exact_matches_checked, match_tuples, repository_metadata, tool_names, tool_versions ):
        for i, tool_name in enumerate( tool_names ):
            tool_version = tool_versions[ i ]
            if self.__in_tool_dict( tool_dict, exact_matches_checked, tool_name=tool_name, tool_version=tool_version ):
                match_tuples.append( ( repository_metadata.repository_id, repository_metadata.changeset_revision ) )
        return match_tuples
    def __encode_repo_info_dict( self, trans, webapp, repository_metadata_ids ):
        repo_info_dict = {}
        includes_tools = False
        for repository_metadata_id in repository_metadata_ids:
            repository_metadata = get_repository_metadata_by_id( trans, repository_metadata_id )
            if not includes_tools and 'tools' in repository_metadata.metadata:
                includes_tools = True
            repository = get_repository( trans, trans.security.encode_id( repository_metadata.repository_id ) )
            # Get the changelog rev for this changeset_revision.
            repo_dir = repository.repo_path
            repo = hg.repository( get_configured_ui(), repo_dir )
            changeset_revision = repository_metadata.changeset_revision
            ctx = get_changectx_for_changeset( repo, changeset_revision )
            repository_id = trans.security.encode_id( repository.id )
            repository_clone_url = generate_clone_url( trans, repository_id )
            repo_info_dict[ repository.name ] = ( repository.description, repository_clone_url, changeset_revision, str( ctx.rev() ) )
        return encode( repo_info_dict ), includes_tools
    @web.expose
    def preview_tools_in_changeset( self, trans, repository_id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', '' ) )
        status = params.get( 'status', 'done' )
        webapp = params.get( 'webapp', 'community' )
        repository = get_repository( trans, repository_id )
        changeset_revision = util.restore_text( params.get( 'changeset_revision', repository.tip ) )
        repository_metadata = get_repository_metadata_by_changeset_revision( trans, repository_id, changeset_revision )
        if repository_metadata:
            repository_metadata_id = trans.security.encode_id( repository_metadata.id ),
            metadata = repository_metadata.metadata
        else:
            repository_metadata_id = None
            metadata = None
        revision_label = get_revision_label( trans, repository, changeset_revision )
        changeset_revision_select_field = build_changeset_revision_select_field( trans,
                                                                                 repository,
                                                                                 selected_value=changeset_revision,
                                                                                 add_id_to_name=False )
        return trans.fill_template( '/webapps/community/repository/preview_tools_in_changeset.mako',
                                    repository=repository,
                                    repository_metadata_id=repository_metadata_id,
                                    changeset_revision=changeset_revision,
                                    revision_label=revision_label,
                                    changeset_revision_select_field=changeset_revision_select_field,
                                    metadata=metadata,
                                    webapp=webapp,
                                    message=message,
                                    status=status )
    @web.expose
    def install_repository_revision( self, trans, repository_id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        webapp = params.get( 'webapp', 'community' )
        galaxy_url = trans.get_cookie( name='toolshedgalaxyurl' )
        repository_clone_url = generate_clone_url( trans, repository_id )        
        repository = get_repository( trans, repository_id )
        changeset_revision = util.restore_text( params.get( 'changeset_revision', repository.tip ) )
        repository_metadata = get_repository_metadata_by_changeset_revision( trans, repository_id, changeset_revision )
        # Tell the caller if the repository includes Galaxy tools so the page
        # enabling selection of the tool panel section can be displayed.
        includes_tools = 'tools' in repository_metadata.metadata
        # Get the changelog rev for this changeset_revision.
        repo_dir = repository.repo_path
        repo = hg.repository( get_configured_ui(), repo_dir )
        ctx = get_changectx_for_changeset( repo, changeset_revision )
        repo_info_dict = {}
        repo_info_dict[ repository.name ] = ( repository.description, repository_clone_url, changeset_revision, str( ctx.rev() ) )
        encoded_repo_info_dict = encode( repo_info_dict )
        # Redirect back to local Galaxy to perform install.
        url = '%sadmin_toolshed/install_repository?tool_shed_url=%s&repo_info_dict=%s&includes_tools=%s' % \
            ( galaxy_url, url_for( '/', qualified=True ), encoded_repo_info_dict, str( includes_tools ) )
        return trans.response.send_redirect( url )
    @web.expose
    def get_ctx_rev( self, trans, **kwd ):
        """Given a repository and changeset_revision, return the correct ctx.rev() value."""
        repository_name = kwd[ 'name' ]
        repository_owner = kwd[ 'owner' ]
        changeset_revision = kwd[ 'changeset_revision' ]
        repository = get_repository_by_name_and_owner( trans, repository_name, repository_owner )
        repo_dir = repository.repo_path
        repo = hg.repository( get_configured_ui(), repo_dir )
        ctx = get_changectx_for_changeset( repo, changeset_revision )
        if ctx:
            return str( ctx.rev() )
        return ''
    @web.expose
    def get_readme( self, trans, **kwd ):
        """If the received changeset_revision includes a file named readme (case ignored), return it's contents."""
        repository_name = kwd[ 'name' ]
        repository_owner = kwd[ 'owner' ]
        changeset_revision = kwd[ 'changeset_revision' ]
        repository = get_repository_by_name_and_owner( trans, repository_name, repository_owner )
        repo_dir = repository.repo_path
        for root, dirs, files in os.walk( repo_dir ):
            for name in files:
                if name.lower() in [ 'readme', 'readme.txt', 'read_me', 'read_me.txt', '%s.txt' % repository_name ]:
                    f = open( os.path.join( root, name ), 'r' )
                    text = f.read()
                    f.close()
                    return str( text )
        return ''
    @web.expose
    def get_tool_versions( self, trans, **kwd ):
        """
        For each valid /downloadable change set (up to the received changeset_revision) in the
        repository's change log, append the change set's tool_versions dictionary to the list
        that will be returned.
        """
        name = kwd[ 'name' ]
        owner = kwd[ 'owner' ]
        changeset_revision = kwd[ 'changeset_revision' ]
        repository = get_repository_by_name_and_owner( trans, name, owner )
        repo_dir = repository.repo_path
        repo = hg.repository( get_configured_ui(), repo_dir )
        tool_version_dicts = []
        for changeset in repo.changelog:
            current_changeset_revision = str( repo.changectx( changeset ) )
            repository_metadata = get_repository_metadata_by_changeset_revision( trans, trans.security.encode_id( repository.id ), current_changeset_revision )
            if repository_metadata and repository_metadata.tool_versions:
                tool_version_dicts.append( repository_metadata.tool_versions )
                if current_changeset_revision == changeset_revision:
                    break
        if tool_version_dicts:
            return to_json_string( tool_version_dicts )
        return ''
    @web.expose
    def check_for_updates( self, trans, **kwd ):
        # Handle a request from a local Galaxy instance.  If the request originated with the
        # Galaxy instances' UpdateManager, the value of 'webapp' will be 'update_manager'.
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        # If the request originated with the UpdateManager, it will not include a galaxy_url.
        galaxy_url = kwd.get( 'galaxy_url', '' )
        name = params.get( 'name', None )
        owner = params.get( 'owner', None )
        changeset_revision = params.get( 'changeset_revision', None )
        webapp = params.get( 'webapp', 'community' )
        repository = get_repository_by_name_and_owner( trans, name, owner )
        repo_dir = repository.repo_path
        repo = hg.repository( get_configured_ui(), repo_dir )
        latest_ctx = get_changectx_for_changeset( repo, changeset_revision )
        from_update_manager = webapp == 'update_manager'
        if from_update_manager:
            update = 'true'
            no_update = 'false'
        else:
            # Start building up the url to redirect back to the calling Galaxy instance.
            url = '%sadmin_toolshed/update_to_changeset_revision?tool_shed_url=%s' % ( galaxy_url, url_for( '/', qualified=True ) )
            url += '&name=%s&owner=%s&changeset_revision=%s&latest_changeset_revision=' % \
                ( repository.name, repository.user.username, changeset_revision )
        if changeset_revision == repository.tip:
            # If changeset_revision is the repository tip, we know there are no additional updates for the tools.
            if from_update_manager:
                return no_update
            # Return the same value for changeset_revision and latest_changeset_revision.
            url += repository.tip
        else:
            repository_metadata = get_repository_metadata_by_changeset_revision( trans, 
                                                                                 trans.security.encode_id( repository.id ),
                                                                                 changeset_revision )
            if repository_metadata:
                # If changeset_revision is in the repository_metadata table for this
                # repository, then we know there are no additional updates for the tools.
                if from_update_manager:
                    return no_update
                else:
                    # Return the same value for changeset_revision and latest_changeset_revision.
                    url += changeset_revision
            else:
                # The changeset_revision column in the repository_metadata table has been
                # updated with a new changeset_revision value since the repository was cloned.
                # Load each tool in the repository's changeset_revision to generate a list of
                # tool guids, since guids differentiate tools by id and version.
                ctx = get_changectx_for_changeset( repo, changeset_revision )
                if ctx is not None:        
                    tool_guids = []
                    for filename in ctx:
                        # Find all tool configs in this repository changeset_revision.
                        if filename != 'datatypes_conf.xml' and filename.endswith( '.xml' ):
                            fctx = ctx[ filename ]
                            # Write the contents of the old tool config to a temporary file.
                            fh = tempfile.NamedTemporaryFile( 'w' )
                            tmp_filename = fh.name
                            fh.close()
                            fh = open( tmp_filename, 'w' )
                            fh.write( fctx.data() )
                            fh.close()
                            if not ( check_binary( tmp_filename ) or check_image( tmp_filename ) or check_gzip( tmp_filename )[ 0 ]
                                     or check_bz2( tmp_filename )[ 0 ] or check_zip( tmp_filename ) ):
                                try:
                                    # Make sure we're looking at a tool config and not a display application config or something else.
                                    element_tree = util.parse_xml( tmp_filename )
                                    element_tree_root = element_tree.getroot()
                                    is_tool = element_tree_root.tag == 'tool'
                                except Exception, e:
                                    log.debug( "Error parsing %s, exception: %s" % ( tmp_filename, str( e ) ) )
                                    is_tool = False
                                if is_tool:
                                    try:
                                        tool = load_tool( trans, tmp_filename )
                                        valid = True
                                    except:
                                        valid = False
                                    if valid and tool is not None:
                                        tool_guids.append( generate_tool_guid( trans, repository, tool ) )
                            try:
                                os.unlink( tmp_filename )
                            except:
                                pass
                    tool_guids.sort()
                    if tool_guids:
                        # Compare our list of tool guids against those in each repository_metadata record
                        # for the repository to find the repository_metadata record with the changeset_revision
                        # value we want to pass back to the caller.
                        found = False
                        for repository_metadata in get_repository_metadata_by_repository_id( trans, trans.security.encode_id( repository.id ) ):
                            metadata = repository_metadata.metadata
                            metadata_tool_guids = []
                            for tool_dict in metadata[ 'tools' ]:
                                metadata_tool_guids.append( tool_dict[ 'guid' ] )
                            metadata_tool_guids.sort()
                            if tool_guids == metadata_tool_guids:
                                # We've found the repository_metadata record whose changeset_revision value has been updated.
                                if from_update_manager:
                                    return update
                                url += repository_metadata.changeset_revision
                                # Get the ctx_rev for the discovered changeset_revision.
                                latest_ctx = get_changectx_for_changeset( repo, repository_metadata.changeset_revision )
                                found = True
                                break
                        if not found:
                            # There must be a problem in the data, so we'll just send back the received changeset_revision.
                            log.debug( "Possible data corruption - updated repository_metadata cannot be found for repository id %d." % repository.id )
                            if from_update_manager:
                                return no_update
                            url += changeset_revision
                    else:
                        # There are no tools in the changeset_revision, so no tool updates are possible.
                        if from_update_manager:
                            return no_update
                        url += changeset_revision
        url += '&latest_ctx_rev=%s' % str( latest_ctx.rev() )
        return trans.response.send_redirect( url )
    @web.expose
    def browse_repositories( self, trans, **kwd ):
        # We add params to the keyword dict in this method in order to rename the param
        # with an "f-" prefix, simulating filtering by clicking a search link.  We have
        # to take this approach because the "-" character is illegal in HTTP requests.
        if 'webapp' not in kwd:
            kwd[ 'webapp' ] = 'community'
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "view_or_manage_repository":
                repository_id = kwd[ 'id' ]
                repository = get_repository( trans, repository_id )
                is_admin = trans.user_is_admin()
                if is_admin or repository.user == trans.user:
                    return trans.response.send_redirect( web.url_for( controller='repository',
                                                                      action='manage_repository',
                                                                      **kwd ) )
                else:
                    return trans.response.send_redirect( web.url_for( controller='repository',
                                                                      action='view_repository',
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
            elif operation == "my_repositories":
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                kwd[ 'f-email' ] = trans.user.email
            elif operation == "repositories_by_category":
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                category_id = kwd.get( 'id', None )
                category = get_category( trans, category_id )
                kwd[ 'f-Category.name' ] = category.name
            elif operation == "receive email alerts":
                if trans.user:
                    if kwd[ 'id' ]:
                        kwd[ 'caller' ] = 'browse_repositories'
                        return trans.response.send_redirect( web.url_for( controller='repository',
                                                                          action='set_email_alerts',
                                                                          **kwd ) )
                else:
                    kwd[ 'message' ] = 'You must be logged in to set email alerts.'
                    kwd[ 'status' ] = 'error'
                    del kwd[ 'operation' ]
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
    def create_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        categories = get_categories( trans )
        if not categories:
            message = 'No categories have been configured in this instance of the Galaxy Tool Shed.  ' + \
                'An administrator needs to create some via the Administrator control panel before creating repositories.',
            status = 'error'
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='browse_repositories',
                                                              message=message,
                                                              status=status ) )
        name = util.restore_text( params.get( 'name', '' ) )
        description = util.restore_text( params.get( 'description', '' ) )
        long_description = util.restore_text( params.get( 'long_description', '' ) )
        category_ids = util.listify( params.get( 'category_id', '' ) )
        selected_categories = [ trans.security.decode_id( id ) for id in category_ids ]
        if params.get( 'create_repository_button', False ):
            error = False
            message = self.__validate_repository_name( name, trans.user )
            if message:
                error = True
            if not description:
                message = 'Enter a description.'
                error = True
            if not error:
                # Add the repository record to the db
                repository = trans.app.model.Repository( name=name,
                                                         description=description,
                                                         long_description=long_description,
                                                         user_id=trans.user.id )
                # Flush to get the id
                trans.sa_session.add( repository )
                trans.sa_session.flush()
                # Determine the repository's repo_path on disk
                dir = os.path.join( trans.app.config.file_path, *directory_hash_id( repository.id ) )
                # Create directory if it does not exist
                if not os.path.exists( dir ):
                    os.makedirs( dir )
                # Define repo name inside hashed directory
                repository_path = os.path.join( dir, "repo_%d" % repository.id )
                # Create local repository directory
                if not os.path.exists( repository_path ):
                    os.makedirs( repository_path )
                # Create the local repository
                repo = hg.repository( get_configured_ui(), repository_path, create=True )
                # Add an entry in the hgweb.config file for the local repository
                # This enables calls to repository.repo_path
                self.__add_hgweb_config_entry( trans, repository, repository_path )
                # Create a .hg/hgrc file for the local repository
                self.__create_hgrc_file( repository )
                flush_needed = False
                if category_ids:
                    # Create category associations
                    for category_id in category_ids:
                        category = trans.app.model.Category.get( trans.security.decode_id( category_id ) )
                        rca = trans.app.model.RepositoryCategoryAssociation( repository, category )
                        trans.sa_session.add( rca )
                        flush_needed = True
                if flush_needed:
                    trans.sa_session.flush()
                message = "Repository '%s' has been created." % repository.name
                trans.response.send_redirect( web.url_for( controller='repository',
                                                           action='view_repository',
                                                           webapp='community',
                                                           message=message,
                                                           id=trans.security.encode_id( repository.id ) ) )
        return trans.fill_template( '/webapps/community/repository/create_repository.mako',
                                    name=name,
                                    description=description,
                                    long_description=long_description,
                                    selected_categories=selected_categories,
                                    categories=categories,
                                    message=message,
                                    status=status )
    def __validate_repository_name( self, name, user ):
        # Repository names must be unique for each user, must be at least four characters
        # in length and must contain only lower-case letters, numbers, and the '_' character.
        if name in [ 'None', None, '' ]:
            return 'Enter the required repository name.'
        for repository in user.active_repositories:
            if repository.name == name:
                return "You already have a repository named '%s', so choose a different name." % name
        if len( name ) < 4:
            return "Repository names must be at least 4 characters in length."
        if len( name ) > 80:
            return "Repository names cannot be more than 80 characters in length."
        if not( VALID_REPOSITORYNAME_RE.match( name ) ):
            return "Repository names must contain only lower-case letters, numbers and underscore '_'."
        return ''
    def __make_hgweb_config_copy( self, trans, hgweb_config ):
        # Make a backup of the hgweb.config file
        today = date.today()
        backup_date = today.strftime( "%Y_%m_%d" )
        hgweb_config_copy = '%s/hgweb.config_%s_backup' % ( trans.app.config.root, backup_date )
        shutil.copy( os.path.abspath( hgweb_config ), os.path.abspath( hgweb_config_copy ) )
    def __add_hgweb_config_entry( self, trans, repository, repository_path ):
        # Add an entry in the hgweb.config file for a new repository.  An entry looks something like:
        # repos/test/mira_assembler = database/community_files/000/repo_123.
        hgweb_config = "%s/hgweb.config" %  trans.app.config.root
        if repository_path.startswith( './' ):
            repository_path = repository_path.replace( './', '', 1 )
        entry = "repos/%s/%s = %s" % ( repository.user.username, repository.name, repository_path )
        tmp_fd, tmp_fname = tempfile.mkstemp()
        if os.path.exists( hgweb_config ):
            # Make a backup of the hgweb.config file since we're going to be changing it.
            self.__make_hgweb_config_copy( trans, hgweb_config )
            new_hgweb_config = open( tmp_fname, 'wb' )
            for i, line in enumerate( open( hgweb_config ) ):
                new_hgweb_config.write( line )
        else:
            new_hgweb_config = open( tmp_fname, 'wb' )
            new_hgweb_config.write( '[paths]\n' )
        new_hgweb_config.write( "%s\n" % entry )
        new_hgweb_config.flush()
        shutil.move( tmp_fname, os.path.abspath( hgweb_config ) )
    def __change_hgweb_config_entry( self, trans, repository, old_repository_name, new_repository_name ):
        # Change an entry in the hgweb.config file for a repository.  This only happens when
        # the owner changes the name of the repository.  An entry looks something like:
        # repos/test/mira_assembler = database/community_files/000/repo_123.
        hgweb_config = "%s/hgweb.config" % trans.app.config.root
        # Make a backup of the hgweb.config file since we're going to be changing it.
        self.__make_hgweb_config_copy( trans, hgweb_config )
        repo_dir = repository.repo_path
        old_lhs = "repos/%s/%s" % ( repository.user.username, old_repository_name )
        new_entry = "repos/%s/%s = %s\n" % ( repository.user.username, new_repository_name, repo_dir )
        tmp_fd, tmp_fname = tempfile.mkstemp()
        new_hgweb_config = open( tmp_fname, 'wb' )
        for i, line in enumerate( open( hgweb_config ) ):
            if line.startswith( old_lhs ):
                new_hgweb_config.write( new_entry )
            else:
                new_hgweb_config.write( line )
        new_hgweb_config.flush()
        shutil.move( tmp_fname, os.path.abspath( hgweb_config ) )
    def __create_hgrc_file( self, repository ):
        # At this point, an entry for the repository is required to be in the hgweb.config file so we can call repository.repo_path.
        # Since we support both http and https, we set push_ssl to False to override the default (which is True) in the mercurial api.
        # The hg purge extension purges all files and directories not being tracked by mercurial in the current repository.  It'll
        # remove unknown files and empty directories.  This is not currently used because it is not supported in the mercurial API.
        repo = hg.repository( get_configured_ui(), path=repository.repo_path )
        fp = repo.opener( 'hgrc', 'wb' )
        fp.write( '[paths]\n' )
        fp.write( 'default = .\n' )
        fp.write( 'default-push = .\n' )
        fp.write( '[web]\n' )
        fp.write( 'allow_push = %s\n' % repository.user.username )
        fp.write( 'name = %s\n' % repository.name )
        fp.write( 'push_ssl = false\n' )
        fp.write( '[extensions]\n' )
        fp.write( 'hgext.purge=' )
        fp.close()
    @web.expose
    def browse_repository( self, trans, id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        webapp = params.get( 'webapp', 'community' )
        commit_message = util.restore_text( params.get( 'commit_message', 'Deleted selected files' ) )
        repository = get_repository( trans, id )
        repo = hg.repository( get_configured_ui(), repository.repo_path )
        current_working_dir = os.getcwd()
        # Update repository files for browsing.
        update_repository( repo )
        is_malicious = change_set_is_malicious( trans, id, repository.tip )
        return trans.fill_template( '/webapps/community/repository/browse_repository.mako',
                                    repo=repo,
                                    repository=repository,
                                    commit_message=commit_message,
                                    is_malicious=is_malicious,
                                    webapp=webapp,
                                    message=message,
                                    status=status )
    @web.expose
    def contact_owner( self, trans, id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = get_repository( trans, id )
        if trans.user and trans.user.email:
            return trans.fill_template( "/webapps/community/repository/contact_owner.mako",
                                        repository=repository,
                                        message=message,
                                        status=status )
        else:
            # Do all we can to eliminate spam.
            return trans.show_error_message( "You must be logged in to contact the owner of a repository." )
    @web.expose
    def send_to_owner( self, trans, id, message='' ):
        repository = get_repository( trans, id )
        if not message:
            message = 'Enter a message'
            status = 'error'
        elif trans.user and trans.user.email:
            smtp_server = trans.app.config.smtp_server
            from_address = trans.app.config.email_from
            if smtp_server is None or from_address is None:
                return trans.show_error_message( "Mail is not configured for this Galaxy tool shed instance" )
            to_address = repository.user.email
            # Get the name of the server hosting the tool shed instance.
            host = trans.request.host
            # Build the email message
            body = string.Template( contact_owner_template ) \
                .safe_substitute( username=trans.user.username,
                                  repository_name=repository.name,
                                  email=trans.user.email,
                                  message=message,
                                  host=host )
            subject = "Regarding your tool shed repository named %s" % repository.name
            # Send it
            try:
                util.send_mail( from_address, to_address, subject, body, trans.app.config )
                message = "Your message has been sent"
                status = "done"
            except Exception, e:
                message = "An error occurred sending your message by email: %s" % str( e )
                status = "error"
        else:
            # Do all we can to eliminate spam.
            return trans.show_error_message( "You must be logged in to contact the owner of a repository." )
        return trans.response.send_redirect( web.url_for( controller='repository',
                                                          action='contact_owner',
                                                          id=id,
                                                          message=message,
                                                          status=status ) )
    @web.expose
    def select_files_to_delete( self, trans, id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', '' ) )
        status = params.get( 'status', 'done' )
        commit_message = util.restore_text( params.get( 'commit_message', 'Deleted selected files' ) )
        repository = get_repository( trans, id )
        repo_dir = repository.repo_path
        repo = hg.repository( get_configured_ui(), repo_dir )
        selected_files_to_delete = util.restore_text( params.get( 'selected_files_to_delete', '' ) )
        if params.get( 'select_files_to_delete_button', False ):
            if selected_files_to_delete:
                selected_files_to_delete = selected_files_to_delete.split( ',' )
                current_working_dir = os.getcwd()
                # Get the current repository tip.
                tip = repository.tip
                for selected_file in selected_files_to_delete:
                    try:
                        commands.remove( repo.ui, repo, selected_file, force=True )
                    except Exception, e:
                        # I never have a problem with commands.remove on a Mac, but in the test/production
                        # tool shed environment, it throws an exception whenever I delete all files from a
                        # repository.  If this happens, we'll try the following.
                        relative_selected_file = selected_file.split( 'repo_%d' % repository.id )[1].lstrip( '/' )
                        repo.dirstate.remove( relative_selected_file )
                        repo.dirstate.write()
                        absolute_selected_file = os.path.abspath( selected_file )
                        if os.path.isdir( absolute_selected_file ):
                            try:
                                os.rmdir( absolute_selected_file )
                            except OSError, e:
                                # The directory is not empty
                                pass
                        elif os.path.isfile( absolute_selected_file ):
                            os.remove( absolute_selected_file )
                            dir = os.path.split( absolute_selected_file )[0]
                            try:
                                os.rmdir( dir )
                            except OSError, e:
                                # The directory is not empty
                                pass
                # Commit the change set.
                if not commit_message:
                    commit_message = 'Deleted selected files'
                try:
                    commands.commit( repo.ui, repo, repo_dir, user=trans.user.username, message=commit_message )
                except Exception, e:
                    # I never have a problem with commands.commit on a Mac, but in the test/production
                    # tool shed environment, it occasionally throws a "TypeError: array item must be char"
                    # exception.  If this happens, we'll try the following.
                    repo.dirstate.write()
                    repo.commit( user=trans.user.username, text=commit_message )
                handle_email_alerts( trans, repository )
                # Update the repository files for browsing.
                update_repository( repo )
                # Get the new repository tip.
                repo = hg.repository( get_configured_ui(), repo_dir )
                if tip != repository.tip:
                    message = "The selected files were deleted from the repository."
                else:
                    message = 'No changes to repository.'
                # Set metadata on the repository tip.
                error_message, status = set_repository_metadata( trans, id, repository.tip, **kwd )
                if error_message:
                    # If there is an error, display it.
                    message = '%s<br/>%s' % ( message, error_message )
                    return trans.response.send_redirect( web.url_for( controller='repository',
                                                                      action='manage_repository',
                                                                      id=id,
                                                                      message=message,
                                                                      status=status ) )
                else:
                    # If no error occurred in setting metadata on the repository tip, reset metadata on all
                    # changeset revisions for the repository.  This will result in a more standardized set of
                    # valid repository revisions that can be installed.
                    reset_all_repository_metadata( trans, id, **kwd )
            else:
                message = "Select at least 1 file to delete from the repository before clicking <b>Delete selected files</b>."
                status = "error"
        is_malicious = change_set_is_malicious( trans, id, repository.tip )
        return trans.fill_template( '/webapps/community/repository/browse_repository.mako',
                                    repo=repo,
                                    repository=repository,
                                    commit_message=commit_message,
                                    is_malicious=is_malicious,
                                    message=message,
                                    status=status )
    @web.expose
    def view_repository( self, trans, id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = get_repository( trans, id )
        webapp = params.get( 'webapp', 'community' )
        repo = hg.repository( get_configured_ui(), repository.repo_path )
        avg_rating, num_ratings = self.get_ave_item_rating_data( trans.sa_session, repository, webapp_model=trans.model )
        changeset_revision = util.restore_text( params.get( 'changeset_revision', repository.tip ) )
        display_reviews = util.string_as_bool( params.get( 'display_reviews', False ) )
        alerts = params.get( 'alerts', '' )
        alerts_checked = CheckboxField.is_checked( alerts )
        if repository.email_alerts:
            email_alerts = from_json_string( repository.email_alerts )
        else:
            email_alerts = []
        user = trans.user
        if user and params.get( 'receive_email_alerts_button', False ):
            flush_needed = False
            if alerts_checked:
                if user.email not in email_alerts:
                    email_alerts.append( user.email )
                    repository.email_alerts = to_json_string( email_alerts )
                    flush_needed = True
            else:
                if user.email in email_alerts:
                    email_alerts.remove( user.email )
                    repository.email_alerts = to_json_string( email_alerts )
                    flush_needed = True
            if flush_needed:
                trans.sa_session.add( repository )
                trans.sa_session.flush()
        checked = alerts_checked or ( user and user.email in email_alerts )
        alerts_check_box = CheckboxField( 'alerts', checked=checked )
        changeset_revision_select_field = build_changeset_revision_select_field( trans,
                                                                                 repository,
                                                                                 selected_value=changeset_revision,
                                                                                 add_id_to_name=False )
        revision_label = get_revision_label( trans, repository, changeset_revision )
        repository_metadata = get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
        if repository_metadata:
            repository_metadata_id = trans.security.encode_id( repository_metadata.id ),
            metadata = repository_metadata.metadata
        else:
            repository_metadata_id = None
            metadata = None
        is_malicious = change_set_is_malicious( trans, id, repository.tip )
        if is_malicious:
            if trans.app.security_agent.can_push( trans.user, repository ):
                message += malicious_error_can_push
            else:
                message += malicious_error
            status = 'error'
        return trans.fill_template( '/webapps/community/repository/view_repository.mako',
                                    repo=repo,
                                    repository=repository,
                                    repository_metadata_id=repository_metadata_id,
                                    metadata=metadata,
                                    avg_rating=avg_rating,
                                    display_reviews=display_reviews,
                                    num_ratings=num_ratings,
                                    alerts_check_box=alerts_check_box,
                                    changeset_revision=changeset_revision,
                                    changeset_revision_select_field=changeset_revision_select_field,
                                    revision_label=revision_label,
                                    is_malicious=is_malicious,
                                    webapp=webapp,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_login( "manage repository" )
    def manage_repository( self, trans, id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = get_repository( trans, id )
        repo_dir = repository.repo_path
        repo = hg.repository( get_configured_ui(), repo_dir )
        repo_name = util.restore_text( params.get( 'repo_name', repository.name ) )
        changeset_revision = util.restore_text( params.get( 'changeset_revision', repository.tip ) )
        description = util.restore_text( params.get( 'description', repository.description ) )
        long_description = util.restore_text( params.get( 'long_description', repository.long_description ) )
        avg_rating, num_ratings = self.get_ave_item_rating_data( trans.sa_session, repository, webapp_model=trans.model )
        display_reviews = util.string_as_bool( params.get( 'display_reviews', False ) )
        alerts = params.get( 'alerts', '' )
        alerts_checked = CheckboxField.is_checked( alerts )
        category_ids = util.listify( params.get( 'category_id', '' ) )
        if repository.email_alerts:
            email_alerts = from_json_string( repository.email_alerts )
        else:
            email_alerts = []
        allow_push = params.get( 'allow_push', '' )
        error = False
        user = trans.user
        if params.get( 'edit_repository_button', False ):
            flush_needed = False
            # TODO: add a can_manage in the security agent.
            if not ( user.email == repository.user.email or trans.user_is_admin() ):
                message = "You are not the owner of this repository, so you cannot manage it."
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='view_repository',
                                                                  id=id,
                                                                  webapp='community',
                                                                  message=message,
                                                                  status='error' ) )
            if description != repository.description:
                repository.description = description
                flush_needed = True
            if long_description != repository.long_description:
                repository.long_description = long_description
                flush_needed = True
            if repo_name != repository.name:
                message = self.__validate_repository_name( repo_name, user )
                if message:
                    error = True
                else:
                    self.__change_hgweb_config_entry( trans, repository, repository.name, repo_name )
                    repository.name = repo_name
                    flush_needed = True
            if flush_needed:
                trans.sa_session.add( repository )
                trans.sa_session.flush()
            message = "The repository information has been updated."
        elif params.get( 'manage_categories_button', False ):
            flush_needed = False
            # Delete all currently existing categories.
            for rca in repository.categories:
                trans.sa_session.delete( rca )
                trans.sa_session.flush()
            if category_ids:
                # Create category associations
                for category_id in category_ids:
                    category = trans.app.model.Category.get( trans.security.decode_id( category_id ) )
                    rca = trans.app.model.RepositoryCategoryAssociation( repository, category )
                    trans.sa_session.add( rca )
                    trans.sa_session.flush()
            message = "The repository information has been updated."
        elif params.get( 'user_access_button', False ):
            if allow_push not in [ 'none' ]:
                remove_auth = params.get( 'remove_auth', '' )
                if remove_auth:
                    usernames = ''
                else:
                    user_ids = util.listify( allow_push )
                    usernames = []
                    for user_id in user_ids:
                        user = trans.sa_session.query( trans.model.User ).get( trans.security.decode_id( user_id ) )
                        usernames.append( user.username )
                    usernames = ','.join( usernames )
                repository.set_allow_push( usernames, remove_auth=remove_auth )
            message = "The repository information has been updated."
        elif params.get( 'receive_email_alerts_button', False ):
            flush_needed = False
            if alerts_checked:
                if user.email not in email_alerts:
                    email_alerts.append( user.email )
                    repository.email_alerts = to_json_string( email_alerts )
                    flush_needed = True
            else:
                if user.email in email_alerts:
                    email_alerts.remove( user.email )
                    repository.email_alerts = to_json_string( email_alerts )
                    flush_needed = True
            if flush_needed:
                trans.sa_session.add( repository )
                trans.sa_session.flush()
            message = "The repository information has been updated."
        if error:
            status = 'error'
        if repository.allow_push:
            current_allow_push_list = repository.allow_push.split( ',' )
        else:
            current_allow_push_list = []
        allow_push_select_field = self.__build_allow_push_select_field( trans, current_allow_push_list )
        checked = alerts_checked or user.email in email_alerts
        alerts_check_box = CheckboxField( 'alerts', checked=checked )
        changeset_revision_select_field = build_changeset_revision_select_field( trans,
                                                                                 repository,
                                                                                 selected_value=changeset_revision,
                                                                                 add_id_to_name=False )
        revision_label = get_revision_label( trans, repository, changeset_revision )
        repository_metadata = get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
        if repository_metadata:
            repository_metadata_id = trans.security.encode_id( repository_metadata.id )
            metadata = repository_metadata.metadata
            is_malicious = repository_metadata.malicious
        else:
            repository_metadata_id = None
            metadata = None
            is_malicious = False
        if is_malicious:
            if trans.app.security_agent.can_push( trans.user, repository ):
                message += malicious_error_can_push
            else:
                message += malicious_error
            status = 'error'
        malicious_check_box = CheckboxField( 'malicious', checked=is_malicious )
        categories = get_categories( trans )
        selected_categories = [ rca.category_id for rca in repository.categories ]
        return trans.fill_template( '/webapps/community/repository/manage_repository.mako',
                                    repo_name=repo_name,
                                    description=description,
                                    long_description=long_description,
                                    current_allow_push_list=current_allow_push_list,
                                    allow_push_select_field=allow_push_select_field,
                                    repo=repo,
                                    repository=repository,
                                    repository_metadata_id=repository_metadata_id,
                                    changeset_revision=changeset_revision,
                                    changeset_revision_select_field=changeset_revision_select_field,
                                    revision_label=revision_label,
                                    selected_categories=selected_categories,
                                    categories=categories,
                                    metadata=metadata,
                                    avg_rating=avg_rating,
                                    display_reviews=display_reviews,
                                    num_ratings=num_ratings,
                                    alerts_check_box=alerts_check_box,
                                    malicious_check_box=malicious_check_box,
                                    is_malicious=is_malicious,
                                    message=message,
                                    status=status )
    @web.expose
    def view_changelog( self, trans, id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = get_repository( trans, id )
        repo = hg.repository( get_configured_ui(), repository.repo_path )
        changesets = []
        for changeset in repo.changelog:
            ctx = repo.changectx( changeset )
            if get_repository_metadata_by_changeset_revision( trans, id, str( ctx ) ):
                has_metadata = True
            else:
                has_metadata = False
            t, tz = ctx.date()
            date = datetime( *time.gmtime( float( t ) - tz )[:6] )
            display_date = date.strftime( "%Y-%m-%d" )
            change_dict = { 'ctx' : ctx,
                            'rev' : str( ctx.rev() ),
                            'date' : date,
                            'display_date' : display_date,
                            'description' : ctx.description(),
                            'files' : ctx.files(),
                            'user' : ctx.user(),
                            'parent' : ctx.parents()[0],
                            'has_metadata' : has_metadata }
            # Make sure we'll view latest changeset first.
            changesets.insert( 0, change_dict )
        is_malicious = change_set_is_malicious( trans, id, repository.tip )
        return trans.fill_template( '/webapps/community/repository/view_changelog.mako', 
                                    repository=repository,
                                    changesets=changesets,
                                    is_malicious=is_malicious,
                                    message=message,
                                    status=status )
    @web.expose
    def view_changeset( self, trans, id, ctx_str, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = get_repository( trans, id )
        repo = hg.repository( get_configured_ui(), repository.repo_path )
        ctx = get_changectx_for_changeset( repo, ctx_str )
        if ctx is None:
            message = "Repository does not include changeset revision '%s'." % str( ctx_str )
            status = 'error'
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='view_changelog',
                                                              id=id,
                                                              message=message,
                                                              status=status ) )
        ctx_parent = ctx.parents()[0]
        modified, added, removed, deleted, unknown, ignored, clean = repo.status( node1=ctx_parent.node(), node2=ctx.node() )
        anchors = modified + added + removed + deleted + unknown + ignored + clean
        diffs = []
        for diff in patch.diff( repo, node1=ctx_parent.node(), node2=ctx.node() ):
            diffs.append( to_html_escaped( diff ) )
        is_malicious = change_set_is_malicious( trans, id, repository.tip )
        return trans.fill_template( '/webapps/community/repository/view_changeset.mako', 
                                    repository=repository,
                                    ctx=ctx,
                                    anchors=anchors,
                                    modified=modified,
                                    added=added,
                                    removed=removed,
                                    deleted=deleted,
                                    unknown=unknown,
                                    ignored=ignored,
                                    clean=clean,
                                    diffs=diffs,
                                    is_malicious=is_malicious,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_login( "rate repositories" )
    def rate_repository( self, trans, **kwd ):
        """ Rate a repository and return updated rating data. """
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        id = params.get( 'id', None )
        if not id:
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='browse_repositories',
                                                              message='Select a repository to rate',
                                                              status='error' ) )
        repository = get_repository( trans, id )
        repo = hg.repository( get_configured_ui(), repository.repo_path )
        if repository.user == trans.user:
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='browse_repositories',
                                                              message="You are not allowed to rate your own repository",
                                                              status='error' ) )
        if params.get( 'rate_button', False ):
            rating = int( params.get( 'rating', '0' ) )
            comment = util.restore_text( params.get( 'comment', '' ) )
            rating = self.rate_item( trans, trans.user, repository, rating, comment )
        avg_rating, num_ratings = self.get_ave_item_rating_data( trans.sa_session, repository, webapp_model=trans.model )
        display_reviews = util.string_as_bool( params.get( 'display_reviews', False ) )
        rra = self.get_user_item_rating( trans.sa_session, trans.user, repository, webapp_model=trans.model )
        is_malicious = change_set_is_malicious( trans, id, repository.tip )
        return trans.fill_template( '/webapps/community/repository/rate_repository.mako', 
                                    repository=repository,
                                    avg_rating=avg_rating,
                                    display_reviews=display_reviews,
                                    num_ratings=num_ratings,
                                    rra=rra,
                                    is_malicious=is_malicious,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_login( "set email alerts" )
    def set_email_alerts( self, trans, **kwd ):
        # Set email alerts for selected repositories
        # This method is called from multiple grids, so
        # the caller must be passed.
        caller = kwd[ 'caller' ]
        user = trans.user
        if user:
            repository_ids = util.listify( kwd.get( 'id', '' ) )
            total_alerts_added = 0
            total_alerts_removed = 0
            flush_needed = False
            for repository_id in repository_ids:
                repository = get_repository( trans, repository_id )
                if repository.email_alerts:
                    email_alerts = from_json_string( repository.email_alerts )
                else:
                    email_alerts = []
                if user.email in email_alerts:
                    email_alerts.remove( user.email )
                    repository.email_alerts = to_json_string( email_alerts )
                    trans.sa_session.add( repository )
                    flush_needed = True
                    total_alerts_removed += 1
                else:
                    email_alerts.append( user.email )
                    repository.email_alerts = to_json_string( email_alerts )
                    trans.sa_session.add( repository )
                    flush_needed = True
                    total_alerts_added += 1
            if flush_needed:
                trans.sa_session.flush()
            message = 'Total alerts added: %d, total alerts removed: %d' % ( total_alerts_added, total_alerts_removed )
            kwd[ 'message' ] = message
            kwd[ 'status' ] = 'done'
        del kwd[ 'operation' ]
        return trans.response.send_redirect( web.url_for( controller='repository',
                                                          action=caller,
                                                          **kwd ) )
    @web.expose
    @web.require_login( "manage email alerts" )
    def manage_email_alerts( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        new_repo_alert = params.get( 'new_repo_alert', '' )
        new_repo_alert_checked = CheckboxField.is_checked( new_repo_alert )
        user = trans.user
        if params.get( 'new_repo_alert_button', False ):
            user.new_repo_alert = new_repo_alert_checked
            trans.sa_session.add( user )
            trans.sa_session.flush()
            if new_repo_alert_checked:
                message = 'You will receive email alerts for all new valid tool shed repositories.'
            else:
                message = 'You will not receive any email alerts for new valid tool shed repositories.'
        checked = new_repo_alert_checked or ( user and user.new_repo_alert )
        new_repo_alert_check_box = CheckboxField( 'new_repo_alert', checked=checked )
        email_alert_repositories = []
        for repository in trans.sa_session.query( trans.model.Repository ) \
                                          .filter( and_( trans.model.Repository.table.c.deleted == False,
                                                         trans.model.Repository.table.c.email_alerts != None ) ) \
                                          .order_by( trans.model.Repository.table.c.name ):
            if user.email in repository.email_alerts:
                email_alert_repositories.append( repository )
        return trans.fill_template( "/webapps/community/user/manage_email_alerts.mako",
                                    webapp='community',
                                    new_repo_alert_check_box=new_repo_alert_check_box,
                                    email_alert_repositories=email_alert_repositories,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_login( "manage email alerts" )
    def multi_select_email_alerts( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if 'webapp' not in kwd:
            kwd[ 'webapp' ] = 'community'
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "receive email alerts":
                if trans.user:
                    if kwd[ 'id' ]:
                        kwd[ 'caller' ] = 'multi_select_email_alerts'
                        return trans.response.send_redirect( web.url_for( controller='repository',
                                                                          action='set_email_alerts',
                                                                          **kwd ) )
                else:
                    kwd[ 'message' ] = 'You must be logged in to set email alerts.'
                    kwd[ 'status' ] = 'error'
                    del kwd[ 'operation' ]
        return self.email_alerts_repository_list_grid( trans, **kwd )
    @web.expose
    @web.require_login( "set repository metadata" )
    def set_metadata( self, trans, id, ctx_str, **kwd ):
        malicious = kwd.get( 'malicious', '' )
        if kwd.get( 'malicious_button', False ):
            repository_metadata = get_repository_metadata_by_changeset_revision( trans, id, ctx_str )
            malicious_checked = CheckboxField.is_checked( malicious )
            repository_metadata.malicious = malicious_checked
            trans.sa_session.add( repository_metadata )
            trans.sa_session.flush()
            if malicious_checked:
                message = "The repository tip has been defined as malicious."
            else:
                message = "The repository tip has been defined as <b>not</b> malicious."
            status = 'done'
        else:
            # The set_metadata_button was clicked
            message, status = set_repository_metadata( trans, id, ctx_str, **kwd )
            if not message:
                message = "Metadata for change set revision '%s' has been reset." % str( ctx_str )
        return trans.response.send_redirect( web.url_for( controller='repository',
                                                          action='manage_repository',
                                                          id=id,
                                                          changeset_revision=ctx_str,
                                                          malicious=malicious,
                                                          message=message,
                                                          status=status ) )
    @web.expose
    def reset_all_metadata( self, trans, id, **kwd ):
        reset_all_repository_metadata( trans, id, **kwd )
        message = "All repository metadata has been reset."
        status = 'done'
        return trans.response.send_redirect( web.url_for( controller='repository',
                                                          action='manage_repository',
                                                          id=id,
                                                          message=message,
                                                          status=status ) )
    @web.expose
    def display_tool( self, trans, repository_id, tool_config, changeset_revision, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        webapp = params.get( 'webapp', 'community' )
        repository = get_repository( trans, repository_id )
        tool, message = load_tool_from_changeset_revision( trans, repository_id, changeset_revision, tool_config )
        tool_state = self.__new_state( trans )
        is_malicious = change_set_is_malicious( trans, repository_id, repository.tip )
        try:
            return trans.fill_template( "/webapps/community/repository/tool_form.mako",
                                        repository=repository,
                                        changeset_revision=changeset_revision,
                                        tool=tool,
                                        tool_state=tool_state,
                                        is_malicious=is_malicious,
                                        webapp=webapp,
                                        message=message,
                                        status=status )
        except Exception, e:
            message = "Error displaying tool, probably due to a problem in the tool config.  The exception is: %s." % str( e )
        if webapp == 'galaxy':
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='preview_tools_in_changeset',
                                                              repository_id=repository_id,
                                                              changeset_revision=changeset_revision,
                                                              message=message,
                                                              status='error' ) )
        return trans.response.send_redirect( web.url_for( controller='repository',
                                                          action='browse_repositories',
                                                          operation='view_or_manage_repository',
                                                          id=repository_id,
                                                          changeset_revision=changeset_revision,
                                                          message=message,
                                                          status='error' ) )
    @web.expose
    def load_invalid_tool( self, trans, repository_id, tool_config, changeset_revision, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'error' )
        webapp = params.get( 'webapp', 'community' )
        repository = get_repository( trans, repository_id )
        repo_dir = repository.repo_path
        repo = hg.repository( get_configured_ui(), repo_dir )
        ctx = get_changectx_for_changeset( repo, changeset_revision )
        invalid_message = ''
        if changeset_revision == repository.tip:
            for root, dirs, files in os.walk( repo_dir ):
                found = False
                for name in files:
                    if name == tool_config:
                        tool_config_path = os.path.join( root, name )
                        found = True
                        break
                if found:
                    break
            metadata_dict, invalid_files = generate_metadata_for_repository_tip( trans, repository_id, ctx, changeset_revision, repo, repo_dir )
        else:
            for filename in ctx:
                if filename == tool_config:
                    fctx = ctx[ filename ]
                    # Write the contents of datatypes_config.xml to a temporary file.
                    fh = tempfile.NamedTemporaryFile( 'w' )
                    tool_config_path = fh.name
                    fh.close()
                    fh = open( tool_config_path, 'w' )
                    fh.write( fctx.data() )
                    fh.close()
                    break
            metadata_dict, invalid_files = generate_metadata_for_changeset_revision( trans, repository_id, ctx, changeset_revision, repo_dir )
        for invalid_file_tup in invalid_files:
            invalid_tool_config, invalid_msg = invalid_file_tup
            if tool_config == invalid_tool_config:
                invalid_message = invalid_msg
                break 
        tool, message = load_tool_from_changeset_revision( trans, repository_id, changeset_revision, tool_config_path )
        tool_state = self.__new_state( trans )
        is_malicious = change_set_is_malicious( trans, repository_id, repository.tip )
        if changeset_revision != repository.tip:
            try:
                os.unlink( tool_config_path )
            except:
                pass
        try:
            if invalid_message:
                message = invalid_message
            return trans.fill_template( "/webapps/community/repository/tool_form.mako",
                                        repository=repository,
                                        changeset_revision=changeset_revision,
                                        tool=tool,
                                        tool_state=tool_state,
                                        is_malicious=is_malicious,
                                        webapp=webapp,
                                        message=message,
                                        status='error' )
        except Exception, e:
            message = "This tool is invalid because: %s." % str( e )
        if webapp == 'galaxy':
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='preview_tools_in_changeset',
                                                              repository_id=repository_id,
                                                              changeset_revision=changeset_revision,
                                                              message=message,
                                                              status='error' ) )
        return trans.response.send_redirect( web.url_for( controller='repository',
                                                          action='browse_repositories',
                                                          operation='view_or_manage_repository',
                                                          id=repository_id,
                                                          changeset_revision=changeset_revision,
                                                          message=message,
                                                          status='error' ) )
    def __new_state( self, trans, all_pages=False ):
        """
        Create a new `DefaultToolState` for this tool. It will not be initialized
        with default values for inputs. 
        
        Only inputs on the first page will be initialized unless `all_pages` is
        True, in which case all inputs regardless of page are initialized.
        """
        state = DefaultToolState()
        state.inputs = {}
        return state
    @web.expose
    def view_tool_metadata( self, trans, repository_id, changeset_revision, tool_id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        webapp = params.get( 'webapp', 'community' )
        repository = get_repository( trans, repository_id )
        metadata = {}
        tool = None
        revision_label = get_revision_label( trans, repository, changeset_revision )
        repository_metadata = get_repository_metadata_by_changeset_revision( trans, repository_id, changeset_revision ).metadata
        if 'tools' in repository_metadata:
            for tool_metadata_dict in repository_metadata[ 'tools' ]:
                if tool_metadata_dict[ 'id' ] == tool_id:
                    metadata = tool_metadata_dict
                    try:
                        # We may be attempting to load a tool that no longer exists in the repository tip.
                        tool = load_tool( trans, os.path.abspath( metadata[ 'tool_config' ] ) )
                    except:
                        tool = None
                    break
        is_malicious = change_set_is_malicious( trans, repository_id, repository.tip )
        changeset_revision_select_field = build_changeset_revision_select_field( trans,
                                                                                 repository,
                                                                                 selected_value=changeset_revision,
                                                                                 add_id_to_name=False )
        return trans.fill_template( "/webapps/community/repository/view_tool_metadata.mako",
                                    repository=repository,
                                    tool=tool,
                                    metadata=metadata,
                                    changeset_revision=changeset_revision,
                                    revision_label=revision_label,
                                    changeset_revision_select_field=changeset_revision_select_field,
                                    is_malicious=is_malicious,
                                    webapp=webapp,
                                    message=message,
                                    status=status )
    @web.expose
    def download( self, trans, repository_id, changeset_revision, file_type, **kwd ):
        # Download an archive of the repository files compressed as zip, gz or bz2.
        params = util.Params( kwd )
        repository = get_repository( trans, repository_id )
        # Allow hgweb to handle the download.  This requires the tool shed
        # server account's .hgrc file to include the following setting:
        # [web]
        # allow_archive = bz2, gz, zip
        if file_type == 'zip':
            file_type_str = '%s.zip' % changeset_revision
        elif file_type == 'bz2':
            file_type_str = '%s.tar.bz2' % changeset_revision
        elif file_type == 'gz':
            file_type_str = '%s.tar.gz' % changeset_revision
        repository.times_downloaded += 1
        trans.sa_session.add( repository )
        trans.sa_session.flush()
        download_url = '/repos/%s/%s/archive/%s' % ( repository.user.username, repository.name, file_type_str )
        return trans.response.send_redirect( download_url )
    @web.json
    def open_folder( self, trans, repository_id, key ):
        # The tool shed includes a repository source file browser, which currently depends upon
        # copies of the hg repository file store in the repo_path for browsing.
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        repository = trans.sa_session.query( trans.model.Repository ).get( trans.security.decode_id( repository_id ) )
        folder_path = key
        try:
            files_list = self.__get_files( trans, folder_path )
        except OSError, e:
            if str( e ).find( 'No such file or directory' ) >= 0:
                # We have a repository with no contents.
                return []
        folder_contents = []
        for filename in files_list:
            is_folder = False
            if filename and filename[-1] == os.sep:
                is_folder = True
            if filename:
                full_path = os.path.join( folder_path, filename )
                node = { "title": filename,
                         "isFolder": is_folder,
                         "isLazy": is_folder,
                         "tooltip": full_path,
                         "key": full_path }
                folder_contents.append( node )
        return folder_contents
    def __get_files( self, trans, folder_path ):
        contents = []
        for item in os.listdir( folder_path ):
            # Skip .hg directories
            if str( item ).startswith( '.hg' ):
                continue
            if os.path.isdir( os.path.join( folder_path, item ) ):
                # Append a '/' character so that our jquery dynatree will
                # function properly.
                item = '%s/' % item
            contents.append( item )
        if contents:
            contents.sort()
        return contents
    @web.json
    def get_file_contents( self, trans, file_path ):
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        if is_gzip( file_path ):
            to_html = to_html_str( '\ngzip compressed file\n' )
        elif is_bz2( file_path ):
            to_html = to_html_str( '\nbz2 compressed file\n' )
        elif check_zip( file_path ):
            to_html = to_html_str( '\nzip compressed file\n' )
        elif check_binary( file_path ):
            to_html = to_html_str( '\nBinary file\n' )
        else:
            to_html = ''
            for i, line in enumerate( open( file_path ) ):
                to_html = '%s%s' % ( to_html, to_html_str( line ) )
                if len( to_html ) > MAX_CONTENT_SIZE:
                    large_str = '\nFile contents truncated because file size is larger than maximum viewing size of %s\n' % util.nice_size( MAX_CONTENT_SIZE )
                    to_html = '%s%s' % ( to_html, to_html_str( large_str ) )
                    break
        return to_html
    @web.expose
    def help( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        return trans.fill_template( '/webapps/community/repository/help.mako', message=message, status=status, **kwd )
    def __build_allow_push_select_field( self, trans, current_push_list, selected_value='none' ):
        options = []
        for user in trans.sa_session.query( trans.model.User ):
            if user.username not in current_push_list:
                options.append( user )
        return build_select_field( trans,
                                   objs=options,
                                   label_attr='username',
                                   select_field_name='allow_push',
                                   selected_value=selected_value,
                                   refresh_on_change=False,
                                   multiple=True )
