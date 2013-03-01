import os, logging, re, tempfile, shutil, ConfigParser, string
from time import gmtime, strftime
from datetime import date, datetime
from galaxy import util, web
from galaxy.util.odict import odict
from galaxy.web.base.controller import BaseUIController
from galaxy.web.form_builder import CheckboxField, SelectField, build_select_field
from galaxy.webapps.tool_shed import model
from galaxy.webapps.tool_shed.model import directory_hash_id
from galaxy.web.framework.helpers import grids
from galaxy.util import json
from galaxy.model.orm import and_, or_
import tool_shed.util.shed_util_common as suc
from tool_shed.util import encoding_util
from galaxy.webapps.tool_shed.util import workflow_util
from galaxy.webapps.tool_shed.util import common_util
import galaxy.tools

from galaxy import eggs
eggs.require('mercurial')
from mercurial import hg, ui, patch, commands
eggs.require('markupsafe')
from markupsafe import escape as escape_html

log = logging.getLogger( __name__ )

VALID_REPOSITORYNAME_RE = re.compile( "^[a-z0-9\_]+$" )
malicious_error = "  This changeset cannot be downloaded because it potentially produces malicious behavior or contains inappropriate content."
malicious_error_can_push = "  Correct this changeset as soon as possible, it potentially produces malicious behavior or contains inappropriate content."


class CategoryGrid( grids.Grid ):


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
                    if not rca.repository.deleted and not rca.repository.deprecated:
                        viewable_repositories += 1
                return viewable_repositories
            return 0

    title = "Categories"
    model_class = model.Category
    template='/webapps/tool_shed/category/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="Category.name",
                    link=( lambda item: dict( operation="repositories_by_category", id=item.id ) ),
                    attach_popup=False ),
        DescriptionColumn( "Description",
                           key="Category.description",
                           attach_popup=False ),
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


class ValidCategoryGrid( CategoryGrid ):


    class RepositoriesColumn( grids.TextColumn ):
        def get_value( self, trans, grid, category ):
            if category.repositories:
                viewable_repositories = 0
                for rca in category.repositories:
                    repository = rca.repository
                    if not repository.deleted and not repository.deprecated and repository.downloadable_revisions:
                        viewable_repositories += 1
                return viewable_repositories
            return 0

    title = "Categories of valid repositories"
    model_class = model.Category
    template='/webapps/tool_shed/category/valid_grid.mako'
    default_sort_key = "name"
    columns = [
        CategoryGrid.NameColumn( "Name",
                                 key="Category.name",
                                 link=( lambda item: dict( operation="valid_repositories_by_category", id=item.id ) ),
                                 attach_popup=False ),
        CategoryGrid.DescriptionColumn( "Description",
                                        key="Category.description",
                                        attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        RepositoriesColumn( "Valid repositories",
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


class RepositoryGrid( grids.Grid ):


    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository ):
            return escape_html( repository.name )


    class MetadataRevisionColumn( grids.GridColumn ):

        def __init__( self, col_name ):
            grids.GridColumn.__init__( self, col_name )

        def get_value( self, trans, grid, repository ):
            """Display a SelectField whose options are the changeset_revision strings of all metadata revisions of this repository."""
            # A repository's metadata revisions may not all be installable, as some may contain only invalid tools.
            select_field = build_changeset_revision_select_field( trans, repository, downloadable=False )
            if len( select_field.options ) > 1:
                return select_field.get_html()
            elif len( select_field.options ) == 1:
                return select_field.options[ 0 ][ 0 ]
            return ''


    class TipRevisionColumn( grids.GridColumn ):

        def __init__( self, col_name ):
            grids.GridColumn.__init__( self, col_name )

        def get_value( self, trans, grid, repository ):
            """Display the repository tip revision label."""
            return escape_html( repository.revision( trans.app ) )


    class DescriptionColumn( grids.TextColumn ):

        def get_value( self, trans, grid, repository ):
            return escape_html( repository.description )


    class CategoryColumn( grids.TextColumn ):

        def get_value( self, trans, grid, repository ):
            rval = '<ul>'
            if repository.categories:
                for rca in repository.categories:
                    rval += '<li><a href="browse_repositories?operation=repositories_by_category&id=%s">%s</a></li>' \
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
                return escape_html( repository.user.username )
            return 'no user'


    class EmailColumn( grids.TextColumn ):

        def filter( self, trans, user, query, column_filter ):
            if column_filter == 'All':
                return query
            return query.filter( and_( model.Repository.table.c.user_id == model.User.table.c.id,
                                       model.User.table.c.email == column_filter ) )


    class EmailAlertsColumn( grids.TextColumn ):

        def get_value( self, trans, grid, repository ):
            if trans.user and repository.email_alerts and trans.user.email in json.from_json_string( repository.email_alerts ):
                return 'yes'
            return ''


    class DeprecatedColumn( grids.TextColumn ):

        def get_value( self, trans, grid, repository ):
            if repository.deprecated:
                return 'yes'
            return ''

    title = "Repositories"
    model_class = model.Repository
    template='/webapps/tool_shed/repository/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                    attach_popup=True ),
        DescriptionColumn( "Synopsis",
                           key="description",
                           attach_popup=False ),
        MetadataRevisionColumn( "Metadata Revisions" ),
        TipRevisionColumn( "Tip Revision" ),
        CategoryColumn( "Category",
                        model_class=model.Category,
                        key="Category.name",
                        attach_popup=False ),
        UserColumn( "Owner",
                     model_class=model.User,
                     link=( lambda item: dict( operation="repositories_by_user", id=item.id ) ),
                     attach_popup=False,
                     key="User.username" ),
        # Columns that are valid for filtering but are not visible.
        EmailColumn( "Email",
                     model_class=model.User,
                     key="email",
                     visible=False ),
        RepositoryCategoryColumn( "Category",
                                  model_class=model.Category,
                                  key="Category.name",
                                  visible=False )
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
        return trans.sa_session.query( model.Repository ) \
                               .filter( and_( model.Repository.table.c.deleted == False,
                                              model.Repository.table.c.deprecated == False ) ) \
                               .join( model.User.table ) \
                               .outerjoin( model.RepositoryCategoryAssociation.table ) \
                               .outerjoin( model.Category.table )


class RepositoriesByUserGrid( RepositoryGrid ):
    title = "Repositories by user"
    columns = [
        RepositoryGrid.NameColumn( "Name",
                                   key="name",
                                   link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                   attach_popup=False ),
        RepositoryGrid.MetadataRevisionColumn( "Metadata Revisions" ),
        RepositoryGrid.TipRevisionColumn( "Tip Revision" ),
        RepositoryGrid.DescriptionColumn( "Synopsis",
                                          key="description",
                                          attach_popup=False ),
        RepositoryGrid.CategoryColumn( "Category",
                                       model_class=model.Category,
                                       key="Category.name",
                                       attach_popup=False )
    ]
    operations = []
    standard_filters = []
    default_filter = dict( deleted="False" )
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True

    def build_initial_query( self, trans, **kwd ):
        decoded_user_id = trans.security.decode_id( kwd[ 'user_id' ] )
        return trans.sa_session.query( model.Repository ) \
                               .filter( and_( model.Repository.table.c.deleted == False,
                                              model.Repository.table.c.deprecated == False,
                                              model.Repository.table.c.user_id == decoded_user_id ) ) \
                               .join( model.User.table ) \
                               .outerjoin( model.RepositoryCategoryAssociation.table ) \
                               .outerjoin( model.Category.table )


class RepositoriesIOwnGrid( RepositoryGrid ):
    title = "Repositories I own"
    columns = [
        RepositoryGrid.NameColumn( "Name",
                                   key="name",
                                   link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                   attach_popup=True ),
        RepositoryGrid.MetadataRevisionColumn( "Metadata Revisions" ),
        RepositoryGrid.TipRevisionColumn( "Tip Revision" ),
        RepositoryGrid.CategoryColumn( "Category",
                                       model_class=model.Category,
                                       key="Category.name",
                                       attach_popup=False ),
        RepositoryGrid.DeprecatedColumn( "Deprecated" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name", 
                                                cols_to_filter=[ columns[0] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [ grids.GridOperation( "Mark as deprecated",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted and not item.deprecated ),
                                        async_compatible=False,
                                        confirm="Are you sure that you want to deprecate this repository?" ),
                   grids.GridOperation( "Mark as not deprecated",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted and item.deprecated ),
                                        async_compatible=False ) ]

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( model.Repository ) \
                               .filter( and_( model.Repository.table.c.deleted == False,
                                              model.Repository.table.c.user_id == trans.user.id ) ) \
                               .join( model.User.table ) \
                               .outerjoin( model.RepositoryCategoryAssociation.table ) \
                               .outerjoin( model.Category.table )


class DeprecatedRepositoriesIOwnGrid( RepositoriesIOwnGrid ):
    title = "Deprecated repositories I own"
    columns = [
        RepositoriesIOwnGrid.NameColumn( "Name",
                                         key="name",
                                         link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                         attach_popup=True ),
        RepositoriesIOwnGrid.MetadataRevisionColumn( "Metadata Revisions" ),
        RepositoriesIOwnGrid.TipRevisionColumn( "Tip Revision" ),
        RepositoriesIOwnGrid.CategoryColumn( "Category",
                                             model_class=model.Category,
                                             key="Category.name",
                                             attach_popup=False ),
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name", 
                                                cols_to_filter=[ columns[0] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( model.Repository ) \
                               .filter( and_( model.Repository.table.c.deleted == False,
                                              model.Repository.table.c.user_id == trans.user.id,
                                              model.Repository.table.c.deprecated == True ) ) \
                               .join( model.User.table ) \
                               .outerjoin( model.RepositoryCategoryAssociation.table ) \
                               .outerjoin( model.Category.table )


class EmailAlertsRepositoryGrid( RepositoryGrid ):
    columns = [
        RepositoryGrid.NameColumn( "Name",
                                   key="name",
                                   link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                   attach_popup=False ),
        RepositoryGrid.DescriptionColumn( "Synopsis",
                                          key="description",
                                          attach_popup=False ),
        RepositoryGrid.UserColumn( "Owner",
                                   model_class=model.User,
                                   link=( lambda item: dict( operation="repositories_by_user", id=item.id ) ),
                                   attach_popup=False,
                                   key="User.username" ),
        RepositoryGrid.EmailAlertsColumn( "Alert", attach_popup=False ),
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
            grids.GridAction( "User preferences", dict( controller='user', action='index', cntrller='repository' ) )
        ]


class MyWritableRepositoriesGrid( RepositoryGrid ):
    # This grid filters out repositories that have been marked as either deprecated or deleted.
    columns = [
        RepositoryGrid.NameColumn( "Name",
                                   key="name",
                                   link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                   attach_popup=True ),
        RepositoryGrid.MetadataRevisionColumn( "Metadata Revisions" ),
        RepositoryGrid.TipRevisionColumn( "Tip Revision" ),
        RepositoryGrid.UserColumn( "Owner",
                                   model_class=model.User,
                                   link=( lambda item: dict( operation="repositories_by_user", id=item.id ) ),
                                   attach_popup=False,
                                   key="User.username" ),
        RepositoryGrid.EmailAlertsColumn( "Alert", attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        RepositoryGrid.EmailColumn( "Email",
                                    model_class=model.User,
                                    key="email",
                                    visible=False ),
        RepositoryGrid.RepositoryCategoryColumn( "Category",
                                                 model_class=model.Category,
                                                 key="Category.name",
                                                 visible=False )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name", 
                                                cols_to_filter=[ columns[0] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [ grids.GridOperation( "Receive email alerts",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted ),
                                        async_compatible=False ) ]

    def build_initial_query( self, trans, **kwd ):
        # TODO: improve performance by adding a db table associating users with repositories for which they have write access.
        username = trans.user.username
        clause_list = []
        for repository in trans.sa_session.query( model.Repository ) \
                                          .filter( and_( model.Repository.table.c.deprecated == False,
                                                         model.Repository.table.c.deleted == False ) ):
            allow_push = repository.allow_push( trans.app )
            if allow_push:
                allow_push_usernames = allow_push.split( ',' )
                if username in allow_push_usernames:
                    clause_list.append( model.Repository.table.c.id == repository.id )
        if clause_list:
            return trans.sa_session.query( model.Repository ) \
                                   .filter( or_( *clause_list ) ) \
                                   .join( model.User.table ) \
                                   .outerjoin( model.RepositoryCategoryAssociation.table ) \
                                   .outerjoin( model.Category.table )
        # Return an empty query.
        return trans.sa_session.query( model.Repository ) \
                               .filter( model.Repository.table.c.id < 0 )


class ValidRepositoryGrid( RepositoryGrid ):
    # This grid filters out repositories that have been marked as either deleted or deprecated.


    class CategoryColumn( grids.TextColumn ):
        def get_value( self, trans, grid, repository ):
            rval = '<ul>'
            if repository.categories:
                for rca in repository.categories:
                    rval += '<li><a href="browse_repositories?operation=valid_repositories_by_category&id=%s">%s</a></li>' \
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


    class RevisionColumn( grids.GridColumn ):

        def __init__( self, col_name ):
            grids.GridColumn.__init__( self, col_name )

        def get_value( self, trans, grid, repository ):
            """Display a SelectField whose options are the changeset_revision strings of all download-able revisions of this repository."""
            select_field = build_changeset_revision_select_field( trans, repository, downloadable=True )
            if len( select_field.options ) > 1:
                return select_field.get_html()
            elif len( select_field.options ) == 1:
                return select_field.options[ 0 ][ 0 ]
            return ''
    title = "Valid repositories"
    columns = [
        RepositoryGrid.NameColumn( "Name",
                                   key="name",
                                   attach_popup=True ),
        RepositoryGrid.DescriptionColumn( "Synopsis",
                                          key="description",
                                          attach_popup=False ),
        RevisionColumn( "Installable Revisions" ),
        RepositoryGrid.UserColumn( "Owner",
                                   model_class=model.User,
                                   attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        RepositoryCategoryColumn( "Category",
                                  model_class=model.Category,
                                  key="Category.name",
                                  visible=False )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name, description", 
                                                cols_to_filter=[ columns[0], columns[1] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = []

    def build_initial_query( self, trans, **kwd ):
        if 'id' in kwd:
            # The user is browsing categories of valid repositories, so filter the request by the received id, which is a category id.
            return trans.sa_session.query( model.Repository ) \
                                   .filter( and_( model.Repository.table.c.deleted == False,
                                                  model.Repository.table.c.deprecated == False ) ) \
                                   .join( model.RepositoryMetadata.table ) \
                                   .join( model.User.table ) \
                                   .join( model.RepositoryCategoryAssociation.table ) \
                                   .join( model.Category.table ) \
                                   .filter( and_( model.Category.table.c.id == trans.security.decode_id( kwd[ 'id' ] ),
                                                  model.RepositoryMetadata.table.c.downloadable == True ) )
        # The user performed a free text search on the ValidCategoryGrid.
        return trans.sa_session.query( model.Repository ) \
                               .filter( and_( model.Repository.table.c.deleted == False,
                                              model.Repository.table.c.deprecated == False ) ) \
                               .join( model.RepositoryMetadata.table ) \
                               .join( model.User.table ) \
                               .outerjoin( model.RepositoryCategoryAssociation.table ) \
                               .outerjoin( model.Category.table ) \
                               .filter( model.RepositoryMetadata.table.c.downloadable == True )


class MatchedRepositoryGrid( grids.Grid ):
    # This grid filters out repositories that have been marked as deprecated.


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
    template='/webapps/tool_shed/repository/grid.mako'
    default_sort_key = "Repository.name"
    columns = [
        NameColumn( "Repository name",
                    link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                    attach_popup=True ),
        DescriptionColumn( "Synopsis",
                           attach_popup=False ),
        RevisionColumn( "Revision" ),
        UserColumn( "Owner",
                     model_class=model.User,
                     attach_popup=False )
    ]
    operations = [
        grids.GridOperation( "Install to Galaxy", allow_multiple=True  )
    ]
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
                clause_list.append( "%s=%d and %s='%s'" % ( model.RepositoryMetadata.table.c.repository_id,
                                                            int( repository_id ),
                                                            model.RepositoryMetadata.table.c.changeset_revision,
                                                            changeset_revision ) )
            return trans.sa_session.query( model.RepositoryMetadata ) \
                                   .join( model.Repository ) \
                                   .filter( and_( model.Repository.table.c.deleted == False,
                                                  model.Repository.table.c.deprecated == False ) ) \
                                   .join( model.User.table ) \
                                   .filter( or_( *clause_list ) ) \
                                   .order_by( model.Repository.name )
        # Return an empty query
        return trans.sa_session.query( model.RepositoryMetadata ) \
                               .filter( model.RepositoryMetadata.id < 0 )


class InstallMatchedRepositoryGrid( MatchedRepositoryGrid ):
    columns = [ col for col in MatchedRepositoryGrid.columns ]
    # Override the NameColumn
    columns[ 0 ] = MatchedRepositoryGrid.NameColumn( "Name",
                                                     link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                                     attach_popup=False )


class RepositoryController( BaseUIController, common_util.ItemRatings ):

    install_matched_repository_grid = InstallMatchedRepositoryGrid()
    matched_repository_grid = MatchedRepositoryGrid()
    valid_repository_grid = ValidRepositoryGrid()
    repository_grid = RepositoryGrid()
    email_alerts_repository_grid = EmailAlertsRepositoryGrid()
    category_grid = CategoryGrid()
    valid_category_grid = ValidCategoryGrid()
    my_writable_repositories_grid = MyWritableRepositoriesGrid()
    repositories_i_own_grid = RepositoriesIOwnGrid()
    deprecated_repositories_i_own_grid = DeprecatedRepositoriesIOwnGrid()
    repositories_by_user_grid = RepositoriesByUserGrid()

    @web.expose
    def browse_categories( self, trans, **kwd ):
        # The request came from the tool shed.
        if 'f-free-text-search' in kwd:
            # Trick to enable searching repository name, description from the CategoryGrid.  What we've done is rendered the search box for the
            # RepositoryGrid on the grid.mako template for the CategoryGrid.  See ~/templates/webapps/tool_shed/category/grid.mako.  Since we
            # are searching repositories and not categories, redirect to browse_repositories().
            if 'id' in kwd and 'f-free-text-search' in kwd and kwd[ 'id' ] == kwd[ 'f-free-text-search' ]:
                # The value of 'id' has been set to the search string, which is a repository name.  We'll try to get the desired encoded repository
                # id to pass on.
                try:
                    repository_name = kwd[ 'id' ]
                    repository = suc.get_repository_by_name( trans.app, repository_name )
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
        return self.category_grid( trans, **kwd )

    @web.expose
    def browse_invalid_tools( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        cntrller = params.get( 'cntrller', 'repository' )
        is_admin = trans.user_is_admin()
        invalid_tools_dict = odict()
        if is_admin and cntrller == 'admin':
            for repository in trans.sa_session.query( trans.model.Repository ) \
                                              .filter( trans.model.Repository.table.c.deleted == False ) \
                                              .order_by( trans.model.Repository.table.c.name ):
                # A repository's metadata_revisions are those that ignore the value of the repository_metadata.downloadable column.
                for downloadable_revision in repository.metadata_revisions:
                    metadata = downloadable_revision.metadata
                    invalid_tools = metadata.get( 'invalid_tools', [] )
                    for invalid_tool_config in invalid_tools:
                        invalid_tools_dict[ invalid_tool_config ] = ( repository.id,
                                                                      repository.name,
                                                                      repository.user.username,
                                                                      downloadable_revision.changeset_revision )
        else:
            for repository in trans.sa_session.query( trans.model.Repository ) \
                                              .filter( and_( trans.model.Repository.table.c.deleted == False,
                                                             trans.model.Repository.table.c.user_id == trans.user.id ) ) \
                                              .order_by( trans.model.Repository.table.c.name ):
                for downloadable_revision in repository.metadata_revisions:
                    metadata = downloadable_revision.metadata
                    if metadata:
                        invalid_tools = metadata.get( 'invalid_tools', [] )
                        for invalid_tool_config in invalid_tools:
                            invalid_tools_dict[ invalid_tool_config ] = ( repository.id,
                                                                          repository.name,
                                                                          repository.user.username,
                                                                          downloadable_revision.changeset_revision )
        return trans.fill_template( '/webapps/tool_shed/repository/browse_invalid_tools.mako',
                                    cntrller=cntrller,
                                    invalid_tools_dict=invalid_tools_dict,
                                    message=message,
                                    status=status )

    @web.expose
    def browse_repositories( self, trans, **kwd ):
        # We add params to the keyword dict in this method in order to rename the param with an "f-" prefix, simulating filtering by clicking a search
        # link.  We have to take this approach because the "-" character is illegal in HTTP requests.
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "view_or_manage_repository":
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='view_or_manage_repository',
                                                                  **kwd ) )
            elif operation == "edit_repository":
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='edit_repository',
                                                                  **kwd ) )
            elif operation == "repositories_by_user":
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='browse_repositories_by_user',
                                                                  **kwd ) )
            elif operation == "repositories_i_own":
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                return self.repositories_i_own_grid( trans, **kwd )
            elif operation == "deprecated_repositories_i_own":
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                return self.deprecated_repositories_i_own_grid( trans, **kwd )
            elif operation in [ 'mark as deprecated', 'mark as not deprecated' ]:
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                kwd[ 'mark_deprecated' ] = operation == 'mark as deprecated'
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='deprecate',
                                                                  **kwd ) )
            elif operation == "reviewed_repositories_i_own":
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='reviewed_repositories_i_own' ) )
            elif operation == "my_writable_repositories":
                return self.my_writable_repositories_grid( trans, **kwd )
            elif operation == "repositories_by_category":
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                category_id = kwd.get( 'id', None )
                category = suc.get_category( trans, category_id )
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
        selected_changeset_revision, repository = self.__get_repository_from_refresh_on_change( trans, **kwd )
        if repository:
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='browse_repositories',
                                                              operation='view_or_manage_repository',
                                                              id=trans.security.encode_id( repository.id ),
                                                              changeset_revision=selected_changeset_revision ) )
        return self.repository_grid( trans, **kwd )

    @web.expose
    def browse_repositories_by_user( self, trans, **kwd ):
        """Display the list of repositories owned by a specified user."""
        # Eliminate the current filters if any exist.
        for k, v in kwd.items():
            if k.startswith( 'f-' ):
                del kwd[ k ]
        if 'operation' in kwd:
            operation = kwd[ 'operation' ].lower()
            if operation == "view_or_manage_repository":
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='view_or_manage_repository',
                                                                  **kwd ) )
        if 'user_id' not in kwd:
            # The received id is the repository id, so we need to get the id of the user that uploaded the repository.
            repository_id = kwd.get( 'id', None )
            if repository_id:
                repository = suc.get_repository_in_tool_shed( trans, repository_id )
                kwd[ 'user_id' ] = trans.security.encode_id( repository.user.id )
            else:
                # The user selected a repository revision which results in a refresh_on_change.
                selected_changeset_revision, repository = self.__get_repository_from_refresh_on_change( trans, **kwd )
                if repository:
                    return trans.response.send_redirect( web.url_for( controller='repository',
                                                                      action='view_or_manage_repository',
                                                                      id=trans.security.encode_id( repository.id ),
                                                                      changeset_revision=selected_changeset_revision ) )
        user = suc.get_user( trans, kwd[ 'user_id' ] )
        self.repositories_by_user_grid.title = "Repositories owned by %s" % user.username
        return self.repositories_by_user_grid( trans, **kwd )

    @web.expose
    def browse_repository( self, trans, id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        commit_message = util.restore_text( params.get( 'commit_message', 'Deleted selected files' ) )
        repository = suc.get_repository_in_tool_shed( trans, id )
        repo = hg.repository( suc.get_configured_ui(), repository.repo_path( trans.app ) )
        # Update repository files for browsing.
        suc.update_repository( repo )
        is_malicious = suc.changeset_is_malicious( trans, id, repository.tip( trans.app ) )
        metadata = self.get_metadata( trans, id, repository.tip( trans.app ) )
        return trans.fill_template( '/webapps/tool_shed/repository/browse_repository.mako',
                                    repository=repository,
                                    metadata=metadata,
                                    commit_message=commit_message,
                                    is_malicious=is_malicious,
                                    message=message,
                                    status=status )

    @web.expose
    def browse_valid_categories( self, trans, **kwd ):
        # The request came from Galaxy, so restrict category links to display only valid repository changeset revisions.
        galaxy_url = kwd.get( 'galaxy_url', None )
        if galaxy_url:
            trans.set_cookie( galaxy_url, name='toolshedgalaxyurl' )
        if 'f-free-text-search' in kwd:
            if kwd[ 'f-free-text-search' ] == 'All':
                # The user performed a search, then clicked the "x" to eliminate the search criteria.
                new_kwd = {}
                return self.valid_category_grid( trans, **new_kwd )
            # Since we are searching valid repositories and not categories, redirect to browse_valid_repositories().
            if 'id' in kwd and 'f-free-text-search' in kwd and kwd[ 'id' ] == kwd[ 'f-free-text-search' ]:
                # The value of 'id' has been set to the search string, which is a repository name.
                # We'll try to get the desired encoded repository id to pass on.
                try:
                    name = kwd[ 'id' ]
                    repository = suc.get_repository_by_name( trans.app, name )
                    kwd[ 'id' ] = trans.security.encode_id( repository.id )
                except:
                    pass
            return self.browse_valid_repositories( trans, **kwd )
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation in [ "valid_repositories_by_category", "valid_repositories_by_user" ]:
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='browse_valid_repositories',
                                                                  **kwd ) )
        return self.valid_category_grid( trans, **kwd )

    @web.expose
    def browse_valid_repositories( self, trans, **kwd ):
        galaxy_url = kwd.get( 'galaxy_url', None )
        repository_id = kwd.get( 'id', None )
        if 'f-free-text-search' in kwd:
            if 'f-Category.name' in kwd:
                # The user browsed to a category and then entered a search string, so get the category associated with it's value.
                category_name = kwd[ 'f-Category.name' ]
                category = suc.get_category_by_name( trans, category_name )
                # Set the id value in kwd since it is required by the ValidRepositoryGrid.build_initial_query method.
                kwd[ 'id' ] = trans.security.encode_id( category.id )
        if galaxy_url:
            trans.set_cookie( galaxy_url, name='toolshedgalaxyurl' )
        if 'operation' in kwd:
            operation = kwd[ 'operation' ].lower()
            if operation == "preview_tools_in_changeset":
                repository = suc.get_repository_in_tool_shed( trans, repository_id )
                repository_metadata = suc.get_latest_repository_metadata( trans, repository.id )
                latest_installable_changeset_revision = repository_metadata.changeset_revision
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='preview_tools_in_changeset',
                                                                  repository_id=repository_id,
                                                                  changeset_revision=latest_installable_changeset_revision ) )
            elif operation == "valid_repositories_by_category":
                # Eliminate the current filters if any exist.
                for k, v in kwd.items():
                    if k.startswith( 'f-' ):
                        del kwd[ k ]
                category_id = kwd.get( 'id', None )
                category = suc.get_category( trans, category_id )
                kwd[ 'f-Category.name' ] = category.name
        selected_changeset_revision, repository = self.__get_repository_from_refresh_on_change( trans, **kwd )
        if repository:
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='preview_tools_in_changeset',
                                                              repository_id=trans.security.encode_id( repository.id ),
                                                              changeset_revision=selected_changeset_revision ) )
        url_args = dict( action='browse_valid_repositories',
                         operation='preview_tools_in_changeset',
                         repository_id=repository_id )
        self.valid_repository_grid.operations = [ grids.GridOperation( "Preview and install",
                                                                        url_args=url_args,
                                                                        allow_multiple=False,
                                                                        async_compatible=False ) ]
        return self.valid_repository_grid( trans, **kwd )

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

    def __change_repository_name_in_hgrc_file( self, hgrc_file, new_name ):
        config = ConfigParser.ConfigParser()
        config.read( hgrc_file )
        config.read( hgrc_file )
        config.set( 'web', 'name', new_name )
        new_file = open( hgrc_file, 'wb' )
        config.write( new_file )
        new_file.close()

    @web.expose
    def check_for_updates( self, trans, **kwd ):
        """Handle a request from a local Galaxy instance."""
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        # If the request originated with the UpdateManager, it will not include a galaxy_url.
        galaxy_url = kwd.get( 'galaxy_url', '' )
        name = params.get( 'name', None )
        owner = params.get( 'owner', None )
        changeset_revision = params.get( 'changeset_revision', None )
        repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
        repo_dir = repository.repo_path( trans.app )
        repo = hg.repository( suc.get_configured_ui(), repo_dir )
        # Default to the current changeset revision.
        update_to_ctx = suc.get_changectx_for_changeset( repo, changeset_revision )
        latest_changeset_revision = changeset_revision
        from_update_manager = kwd.get( 'from_update_manager', False )
        if from_update_manager:
            update = 'true'
            no_update = 'false'
        else:
            # Start building up the url to redirect back to the calling Galaxy instance.            
            url = suc.url_join( galaxy_url,
                                'admin_toolshed/update_to_changeset_revision?tool_shed_url=%s&name=%s&owner=%s&changeset_revision=%s&latest_changeset_revision=' % \
                                ( web.url_for( '/', qualified=True ), repository.name, repository.user.username, changeset_revision ) )
        if changeset_revision == repository.tip( trans.app ):
            # If changeset_revision is the repository tip, there are no additional updates.
            if from_update_manager:
                return no_update
            # Return the same value for changeset_revision and latest_changeset_revision.
            url += latest_changeset_revision
        else:
            repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, 
                                                                                     trans.security.encode_id( repository.id ),
                                                                                     changeset_revision )
            if repository_metadata:
                # If changeset_revision is in the repository_metadata table for this repository, there are no additional updates.
                if from_update_manager:
                    return no_update
                else:
                    # Return the same value for changeset_revision and latest_changeset_revision.
                    url += latest_changeset_revision
            else:
                # The changeset_revision column in the repository_metadata table has been updated with a new changeset_revision value since the
                # repository was installed.  We need to find the changeset_revision to which we need to update.
                update_to_changeset_hash = None
                for changeset in repo.changelog:
                    changeset_hash = str( repo.changectx( changeset ) )
                    ctx = suc.get_changectx_for_changeset( repo, changeset_hash )
                    if update_to_changeset_hash:
                        if changeset_hash == repository.tip( trans.app ):
                            update_to_ctx = suc.get_changectx_for_changeset( repo, changeset_hash )
                            latest_changeset_revision = changeset_hash
                            break
                        else:
                            repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans,
                                                                                                     trans.security.encode_id( repository.id ),
                                                                                                     changeset_hash )
                            if repository_metadata:
                                # We found a RepositoryMetadata record.
                                update_to_ctx = suc.get_changectx_for_changeset( repo, changeset_hash )
                                latest_changeset_revision = changeset_hash
                                break
                            else:
                                update_to_changeset_hash = changeset_hash
                    else:
                        if changeset_hash == changeset_revision:
                            # We've found the changeset in the changelog for which we need to get the next update.
                            update_to_changeset_hash = changeset_hash
                if from_update_manager:
                    if latest_changeset_revision == changeset_revision:
                        return no_update
                    return update
                url += str( latest_changeset_revision )
        url += '&latest_ctx_rev=%s' % str( update_to_ctx.rev() )
        return trans.response.send_redirect( url )

    @web.expose
    def contact_owner( self, trans, id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = suc.get_repository_in_tool_shed( trans, id )
        metadata = self.get_metadata( trans, id, repository.tip( trans.app ) )
        if trans.user and trans.user.email:
            return trans.fill_template( "/webapps/tool_shed/repository/contact_owner.mako",
                                        repository=repository,
                                        metadata=metadata,
                                        message=message,
                                        status=status )
        else:
            # Do all we can to eliminate spam.
            return trans.show_error_message( "You must be logged in to contact the owner of a repository." )

    def __create_hgrc_file( self, trans, repository ):
        # At this point, an entry for the repository is required to be in the hgweb.config file so we can call repository.repo_path( trans.app ).
        # Since we support both http and https, we set push_ssl to False to override the default (which is True) in the mercurial api.  The hg
        # purge extension purges all files and directories not being tracked by mercurial in the current repository.  It'll remove unknown files
        # and empty directories.  This is not currently used because it is not supported in the mercurial API.
        repo = hg.repository( suc.get_configured_ui(), path=repository.repo_path( trans.app ) )
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
    def create_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        categories = suc.get_categories( trans )
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
            if error:
                status = 'error'
            else:
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
                repo = hg.repository( suc.get_configured_ui(), repository_path, create=True )
                # Add an entry in the hgweb.config file for the local repository.
                lhs = "repos/%s/%s" % ( repository.user.username, repository.name )
                trans.app.hgweb_config_manager.add_entry( lhs, repository_path )
                # Create a .hg/hgrc file for the local repository
                self.__create_hgrc_file( trans, repository )
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
                                                           message=message,
                                                           id=trans.security.encode_id( repository.id ) ) )
        return trans.fill_template( '/webapps/tool_shed/repository/create_repository.mako',
                                    name=name,
                                    description=description,
                                    long_description=long_description,
                                    selected_categories=selected_categories,
                                    categories=categories,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_login( "deprecate repository" )
    def deprecate( self, trans, **kwd ):
        """Mark a repository in the tool shed as deprecated or not deprecated."""
        # Marking a repository in the tool shed as deprecated has no effect on any downloadable changeset revisions that may be associated with the 
        # repository.  Revisions are not marked as not downlaodable because those that have installed the repository must be allowed to get updates.
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository_id = params.get( 'id', None )
        repository = suc.get_repository_in_tool_shed( trans, repository_id )
        mark_deprecated = util.string_as_bool( params.get( 'mark_deprecated', False ) )
        repository.deprecated = mark_deprecated
        trans.sa_session.add( repository )
        trans.sa_session.flush()
        if mark_deprecated:
            message = 'The repository <b>%s</b> has been marked as deprecated.' % repository.name
        else:
            message = 'The repository <b>%s</b> has been marked as not deprecated.' % repository.name        
        trans.response.send_redirect( web.url_for( controller='repository',
                                                   action='browse_repositories',
                                                   operation='repositories_i_own',
                                                   message=message,
                                                   status=status ) )

    @web.expose
    def display_tool( self, trans, repository_id, tool_config, changeset_revision, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository, tool, message = suc.load_tool_from_changeset_revision( trans, repository_id, changeset_revision, tool_config )
        if message:
            status = 'error'
        tool_state = self.__new_state( trans )
        is_malicious = suc.changeset_is_malicious( trans, repository_id, repository.tip( trans.app ) )
        metadata = self.get_metadata( trans, repository_id, changeset_revision )
        try:
            return trans.fill_template( "/webapps/tool_shed/repository/tool_form.mako",
                                        repository=repository,
                                        metadata=metadata,
                                        changeset_revision=changeset_revision,
                                        tool=tool,
                                        tool_state=tool_state,
                                        is_malicious=is_malicious,
                                        message=message,
                                        status=status )
        except Exception, e:
            message = "Error displaying tool, probably due to a problem in the tool config.  The exception is: %s." % str( e )
        if trans.webapp.name == 'galaxy':
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
    def display_tool_functional_test_errors( self, trans, repository_id, repository_metadata_id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = suc.get_repository_by_id( trans.app, repository_id )
        if repository:
            repository_metadata = suc.get_repository_metadata_by_id( trans, repository_metadata_id )
            changeset_revision = repository_metadata.changeset_revision
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    return trans.fill_template( '/webapps/tool_shed/repository/display_tool_functional_test_errors.mako',
                                                repository=repository,
                                                repository_metadata=repository_metadata,
                                                message=message,
                                                status=status )
                else:
                    message = 'Missing metadata for revision <b>%s</b> of repository <b>%s</b> owned by <b>%s</b>.' % \
                        ( str( changeset_revision ), str( repository.name ), str( repository.user.username ) )
            else:
                message = 'Invalid repository_metadata_id <b>%s</b> received for displaying functional test errors for repository <b>%s</b>.' % \
                    ( str( repository_metadata_id ), str( repository.name ) )
        else:
            message = 'Invalid repository_id received for displaying functional test errors.<b>%s</b>.' % str( repository_id )
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='browse_repositories',
                                                              message=message,
                                                              status='error' ) )
        return trans.response.send_redirect( web.url_for( controller='repository',
                                                          action='browse_repository',
                                                          operation='view_or_manage_repository',
                                                          id=repository_id,
                                                          changeset_revision=changeset_revision,
                                                          message=message,
                                                          status='error' ) )

    @web.expose
    def download( self, trans, repository_id, changeset_revision, file_type, **kwd ):
        # Download an archive of the repository files compressed as zip, gz or bz2.
        params = util.Params( kwd )
        repository = suc.get_repository_in_tool_shed( trans, repository_id )
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

    @web.expose
    def find_tools( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', '' ) )
        status = params.get( 'status', 'done' )
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
                    repository_metadata = suc.get_repository_metadata_by_id( trans, item_id )
                    repository_id = trans.security.encode_id( repository_metadata.repository.id )
                    repository = suc.get_repository_in_tool_shed( trans, repository_id )
                    kwd[ 'id' ] = repository_id
                    kwd[ 'changeset_revision' ] = repository_metadata.changeset_revision
                    if trans.webapp.name == 'tool_shed' and ( is_admin or repository.user == trans.user ):
                        a = 'manage_repository'
                    else:
                        a = 'view_repository'
                    return trans.response.send_redirect( web.url_for( controller='repository',
                                                                      action=a,
                                                                      **kwd ) )
                if operation == "install to galaxy":
                    # We've received a list of RepositoryMetadata ids, so we need to build a list of associated Repository ids.
                    encoded_repository_ids = []
                    changeset_revisions = []
                    for repository_metadata_id in util.listify( item_id ):
                        repository_metadata = suc.get_repository_metadata_by_id( trans, repository_metadata_id )
                        encoded_repository_ids.append( trans.security.encode_id( repository_metadata.repository.id ) )
                        changeset_revisions.append( repository_metadata.changeset_revision )
                    new_kwd = {}
                    new_kwd[ 'repository_ids' ] = encoded_repository_ids
                    new_kwd[ 'changeset_revisions' ] = changeset_revisions
                    return trans.response.send_redirect( web.url_for( controller='repository',
                                                                      action='install_repositories_by_revision',
                                                                      **new_kwd ) )
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
                if trans.webapp.name == 'galaxy':
                    # Our initial request originated from a Galaxy instance.
                    global_actions = [ grids.GridAction( "Browse valid repositories",
                                                         dict( controller='repository', action='browse_valid_categories' ) ),
                                       grids.GridAction( "Search for valid tools",
                                                         dict( controller='repository', action='find_tools' ) ),
                                       grids.GridAction( "Search for workflows",
                                                         dict( controller='repository', action='find_workflows' ) ) ]
                    self.install_matched_repository_grid.global_actions = global_actions
                    install_url_args = dict( controller='repository', action='find_tools' )
                    operations = [ grids.GridOperation( "Install", url_args=install_url_args, allow_multiple=True, async_compatible=False ) ]
                    self.install_matched_repository_grid.operations = operations
                    return self.install_matched_repository_grid( trans, **kwd )
                else:
                    kwd[ 'message' ] = "tool id: <b>%s</b><br/>tool name: <b>%s</b><br/>tool version: <b>%s</b><br/>exact matches only: <b>%s</b>" % \
                        ( self.__stringify( tool_ids ), self.__stringify( tool_names ), self.__stringify( tool_versions ), str( exact_matches_checked ) )
                    self.matched_repository_grid.title = "Repositories with matching tools"
                    return self.matched_repository_grid( trans, **kwd )
            else:
                message = "No search performed - each field must contain the same number of comma-separated items."
                status = "error"
        exact_matches_check_box = CheckboxField( 'exact_matches', checked=exact_matches_checked )
        return trans.fill_template( '/webapps/tool_shed/repository/find_tools.mako',
                                    tool_id=self.__stringify( tool_ids ),
                                    tool_name=self.__stringify( tool_names ),
                                    tool_version=self.__stringify( tool_versions ),
                                    exact_matches_check_box=exact_matches_check_box,
                                    message=message,
                                    status=status )

    @web.expose
    def find_workflows( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', '' ) )
        status = params.get( 'status', 'done' )
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
                    repository_metadata = suc.get_repository_metadata_by_id( trans, item_id )
                    repository_id = trans.security.encode_id( repository_metadata.repository.id )
                    repository = suc.get_repository_in_tool_shed( trans, repository_id )
                    kwd[ 'id' ] = repository_id
                    kwd[ 'changeset_revision' ] = repository_metadata.changeset_revision
                    if trans.webapp.name == 'tool_shed' and ( is_admin or repository.user == trans.user ):
                        a = 'manage_repository'
                    else:
                        a = 'view_repository'
                    return trans.response.send_redirect( web.url_for( controller='repository',
                                                                      action=a,
                                                                      **kwd ) )
                if operation == "install to galaxy":
                    # We've received a list of RepositoryMetadata ids, so we need to build a list of associated Repository ids.
                    encoded_repository_ids = []
                    changeset_revisions = []
                    for repository_metadata_id in util.listify( item_id ):
                        repository_metadata = suc.get_repository_metadata_by_id( trans, item_id )
                        encoded_repository_ids.append( trans.security.encode_id( repository_metadata.repository.id ) )
                        changeset_revisions.append( repository_metadata.changeset_revision )
                    new_kwd = {}
                    new_kwd[ 'repository_ids' ] = encoded_repository_ids
                    new_kwd[ 'changeset_revisions' ] = changeset_revisions
                    return trans.response.send_redirect( web.url_for( controller='repository',
                                                                      action='install_repositories_by_revision',
                                                                      **new_kwd ) )
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
                if trans.webapp.name == 'galaxy':
                    # Our initial request originated from a Galaxy instance.
                    global_actions = [ grids.GridAction( "Browse valid repositories",
                                                         dict( controller='repository', action='browse_valid_repositories' ) ),
                                       grids.GridAction( "Search for valid tools",
                                                         dict( controller='repository', action='find_tools' ) ),
                                       grids.GridAction( "Search for workflows",
                                                         dict( controller='repository', action='find_workflows' ) ) ]
                    self.install_matched_repository_grid.global_actions = global_actions
                    install_url_args = dict( controller='repository', action='find_workflows' )
                    operations = [ grids.GridOperation( "Install", url_args=install_url_args, allow_multiple=True, async_compatible=False ) ]
                    self.install_matched_repository_grid.operations = operations
                    return self.install_matched_repository_grid( trans, **kwd )
                else:
                    kwd[ 'message' ] = "workflow name: <b>%s</b><br/>exact matches only: <b>%s</b>" % \
                        ( self.__stringify( workflow_names ), str( exact_matches_checked ) )
                    self.matched_repository_grid.title = "Repositories with matching workflows"
                    return self.matched_repository_grid( trans, **kwd )
            else:
                message = "No search performed - each field must contain the same number of comma-separated items."
                status = "error"
        else:
            exact_matches_checked = False
            workflow_names = []
        exact_matches_check_box = CheckboxField( 'exact_matches', checked=exact_matches_checked )
        return trans.fill_template( '/webapps/tool_shed/repository/find_workflows.mako',
                                    workflow_name=self.__stringify( workflow_names ),
                                    exact_matches_check_box=exact_matches_check_box,
                                    message=message,
                                    status=status )

    @web.expose
    def generate_workflow_image( self, trans, workflow_name, repository_metadata_id=None ):
        """Return an svg image representation of a workflow dictionary created when the workflow was exported."""
        return workflow_util.generate_workflow_image( trans, workflow_name, repository_metadata_id=repository_metadata_id, repository_id=None )

    @web.expose
    def get_changeset_revision_and_ctx_rev( self, trans, **kwd ):
        """Handle a request from a local Galaxy instance to retrieve the changeset revision hash to which an installed repository can be updated."""
        def has_galaxy_utilities( repository_metadata ):
            includes_data_managers = False
            includes_datatypes = False
            includes_tools = False
            has_repository_dependencies = False
            includes_tool_dependencies = False
            includes_workflows = False
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    if 'data_manager' in metadata:
                        includes_data_managers = True
                    if 'datatypes' in metadata:
                        includes_datatypes = True
                    if 'tools' in metadata:
                        includes_tools = True
                    if 'tool_dependencies' in metadata:
                        includes_tool_dependencies = True
                    if 'repository_dependencies' in metadata:
                        has_repository_dependencies = True
                    if 'workflows' in metadata:
                        includes_workflows = True
            return includes_data_managers, includes_datatypes, includes_tools, includes_tool_dependencies, has_repository_dependencies, includes_workflows
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        galaxy_url = kwd.get( 'galaxy_url', '' )
        name = params.get( 'name', None )
        owner = params.get( 'owner', None )
        changeset_revision = params.get( 'changeset_revision', None )
        repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, 
                                                                                 trans.security.encode_id( repository.id ),
                                                                                 changeset_revision )
        includes_data_managers, includes_datatypes, includes_tools, includes_tool_dependencies, has_repository_dependencies, includes_workflows = \
            has_galaxy_utilities( repository_metadata )
        repo_dir = repository.repo_path( trans.app )
        repo = hg.repository( suc.get_configured_ui(), repo_dir )
        # Default to the received changeset revision and ctx_rev.
        update_to_ctx = suc.get_changectx_for_changeset( repo, changeset_revision )
        ctx_rev = str( update_to_ctx.rev() )
        latest_changeset_revision = changeset_revision
        update_dict = dict( changeset_revision=changeset_revision,
                            ctx_rev=ctx_rev,
                            includes_data_managers=includes_data_managers,
                            includes_datatypes=includes_datatypes,
                            includes_tools=includes_tools,
                            includes_tool_dependencies=includes_tool_dependencies,
                            has_repository_dependencies=has_repository_dependencies,
                            includes_workflows=includes_workflows )
        if changeset_revision == repository.tip( trans.app ):
            # If changeset_revision is the repository tip, there are no additional updates.
            return encoding_util.tool_shed_encode( update_dict )
        else:
            if repository_metadata:
                # If changeset_revision is in the repository_metadata table for this repository, there are no additional updates.
                return encoding_util.tool_shed_encode( update_dict )
            else:
                # The changeset_revision column in the repository_metadata table has been updated with a new changeset_revision value since the
                # repository was installed.  We need to find the changeset_revision to which we need to update.
                update_to_changeset_hash = None
                for changeset in repo.changelog:
                    includes_tools = False
                    has_repository_dependencies = False
                    changeset_hash = str( repo.changectx( changeset ) )
                    ctx = suc.get_changectx_for_changeset( repo, changeset_hash )
                    if update_to_changeset_hash:
                        update_to_repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans,
                                                                                                           trans.security.encode_id( repository.id ),
                                                                                                           changeset_hash )
                        if update_to_repository_metadata:
                            includes_data_managers, includes_datatypes, includes_tools, includes_tool_dependencies, has_repository_dependencies, includes_workflows = \
                                has_galaxy_utilities( update_to_repository_metadata )
                            # We found a RepositoryMetadata record.
                            if changeset_hash == repository.tip( trans.app ):
                                # The current ctx is the repository tip, so use it.
                                update_to_ctx = suc.get_changectx_for_changeset( repo, changeset_hash )
                                latest_changeset_revision = changeset_hash
                            else:
                                update_to_ctx = suc.get_changectx_for_changeset( repo, update_to_changeset_hash )
                                latest_changeset_revision = update_to_changeset_hash
                            break
                    elif not update_to_changeset_hash and changeset_hash == changeset_revision:
                        # We've found the changeset in the changelog for which we need to get the next update.
                        update_to_changeset_hash = changeset_hash
                update_dict[ 'includes_data_managers' ] = includes_data_managers
                update_dict[ 'includes_datatypes' ] = includes_datatypes
                update_dict[ 'includes_tools' ] = includes_tools
                update_dict[ 'includes_tool_dependencies' ] = includes_tool_dependencies
                update_dict[ 'includes_workflows' ] = includes_workflows
                update_dict[ 'has_repository_dependencies' ] = has_repository_dependencies
                update_dict[ 'changeset_revision' ] = str( latest_changeset_revision )
        update_dict[ 'ctx_rev' ] = str( update_to_ctx.rev() )
        return encoding_util.tool_shed_encode( update_dict )

    @web.expose
    def get_ctx_rev( self, trans, **kwd ):
        """Given a repository and changeset_revision, return the correct ctx.rev() value."""
        repository_name = kwd[ 'name' ]
        repository_owner = kwd[ 'owner' ]
        changeset_revision = kwd[ 'changeset_revision' ]
        repository = suc.get_repository_by_name_and_owner( trans.app, repository_name, repository_owner )
        repo_dir = repository.repo_path( trans.app )
        repo = hg.repository( suc.get_configured_ui(), repo_dir )
        ctx = suc.get_changectx_for_changeset( repo, changeset_revision )
        if ctx:
            return str( ctx.rev() )
        return ''

    @web.json
    def get_file_contents( self, trans, file_path ):
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        return suc.get_repository_file_contents( file_path )

    def get_file_from_changeset_revision( self, repo_files_dir, changeset_revision, file_name, dir ):
        """Return file_name from the received changeset_revision of the repository manifest."""
        stripped_file_name = suc.strip_path( file_name )
        repo = hg.repository( suc.get_configured_ui(), repo_files_dir )
        ctx = suc.get_changectx_for_changeset( repo, changeset_revision )
        named_tmp_file = suc.get_named_tmpfile_from_ctx( ctx, file_name, dir )
        return named_tmp_file

    def get_metadata( self, trans, repository_id, changeset_revision ):
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, repository_id, changeset_revision )
        if repository_metadata and repository_metadata.metadata:
            return repository_metadata.metadata
        return None

    @web.json
    def get_readme_files( self, trans, **kwd ):
        """
        This method is called when installing or re-installing a single repository into a Galaxy instance.  If the received changeset_revision 
        includes one or more readme files, return them in a dictionary.
        """
        repository_name = kwd[ 'name' ]
        repository_owner = kwd[ 'owner' ]
        changeset_revision = kwd[ 'changeset_revision' ]
        repository = suc.get_repository_by_name_and_owner( trans.app, repository_name, repository_owner )
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, trans.security.encode_id( repository.id ), changeset_revision )        
        return suc.build_readme_files_dict( repository_metadata.metadata )

    @web.json
    def get_repository_dependencies( self, trans, **kwd ):
        """Return an encoded dictionary of all repositories upon which the contents of the received repository depends."""
        params = util.Params( kwd )
        name = params.get( 'name', None )
        owner = params.get( 'owner', None )
        changeset_revision = params.get( 'changeset_revision', None )
        repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
        repository_id = trans.security.encode_id( repository.id )
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, repository_id, changeset_revision )
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata:
                repository_dependencies = suc.get_repository_dependencies_for_changeset_revision( trans=trans,
                                                                                                  repository=repository,
                                                                                                  repository_metadata=repository_metadata,
                                                                                                  toolshed_base_url=str( web.url_for( '/', qualified=True ) ).rstrip( '/' ),
                                                                                                  key_rd_dicts_to_be_processed=None,
                                                                                                  all_repository_dependencies=None,
                                                                                                  handled_key_rd_dicts=None,
                                                                                                  circular_repository_dependencies=None )
                if repository_dependencies:
                    return encoding_util.tool_shed_encode( repository_dependencies )
        return ''

    def __get_repository_from_refresh_on_change( self, trans, **kwd ):
        # The changeset_revision_select_field in several grids performs a refresh_on_change which sends in request parameters like
        # changeset_revison_1, changeset_revision_2, etc.  One of the many select fields on the grid performed the refresh_on_change,
        # so we loop through all of the received values to see which value is not the repository tip.  If we find it, we know the
        # refresh_on_change occurred and we have the necessary repository id and change set revision to pass on.
        repository_id = None
        for k, v in kwd.items():
            changeset_revision_str = 'changeset_revision_'
            if k.startswith( changeset_revision_str ):
                repository_id = trans.security.encode_id( int( k.lstrip( changeset_revision_str ) ) )
                repository = suc.get_repository_in_tool_shed( trans, repository_id )
                if repository.tip( trans.app ) != v:
                    return v, repository
        # This should never be reached - raise an exception?
        return v, None

    @web.json
    def get_repository_information( self, trans, repository_ids, changeset_revisions, **kwd ):
        """
        Generate a list of dictionaries, each of which contains the information about a repository that will be necessary for installing it into
        a local Galaxy instance.
        """
        includes_tools = False
        has_repository_dependencies = False
        includes_tool_dependencies = False
        repo_info_dicts = []
        for tup in zip( util.listify( repository_ids ), util.listify( changeset_revisions ) ):
            repository_id, changeset_revision = tup
            repository = suc.get_repository_in_tool_shed( trans, repository_id )
            repository_clone_url = suc.generate_clone_url_for_repository_in_tool_shed( trans, repository )
            repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, repository_id, changeset_revision )
            metadata = repository_metadata.metadata
            if not includes_tools:
                if 'tools' in metadata:
                    includes_tools = True
            if not has_repository_dependencies:
                if 'repository_dependencies' in metadata:
                    has_repository_dependencies = True
            if not includes_tool_dependencies:
                if 'tool_dependencies' in metadata:
                    includes_tool_dependencies = True
            repo_dir = repository.repo_path( trans.app )
            repo = hg.repository( suc.get_configured_ui(), repo_dir )
            ctx = suc.get_changectx_for_changeset( repo, changeset_revision )
            repo_info_dict = suc.create_repo_info_dict( trans=trans,
                                                        repository_clone_url=repository_clone_url,
                                                        changeset_revision=changeset_revision,
                                                        ctx_rev=str( ctx.rev() ),
                                                        repository_owner=repository.user.username,
                                                        repository_name=repository.name,
                                                        repository=repository,
                                                        repository_metadata=repository_metadata,
                                                        tool_dependencies=None,
                                                        repository_dependencies=None )
            repo_info_dicts.append( encoding_util.tool_shed_encode( repo_info_dict ) )
        return dict( includes_tools=includes_tools,
                     has_repository_dependencies=has_repository_dependencies,
                     includes_tool_dependencies=includes_tool_dependencies,
                     repo_info_dicts=repo_info_dicts )

    @web.json
    def get_required_repo_info_dict( self, trans, encoded_str ):
        """
        Retrieve and return a dictionary that includes a list of dictionaries that each contain all of the information needed to install the list of
        repositories defined by the received encoded_str.
        """
        encoded_required_repository_str = encoding_util.tool_shed_decode( encoded_str )
        encoded_required_repository_tups = encoded_required_repository_str.split( encoding_util.encoding_sep2 )
        decoded_required_repository_tups = []
        for encoded_required_repository_tup in encoded_required_repository_tups:
            decoded_required_repository_tups.append( encoded_required_repository_tup.split( encoding_util.encoding_sep ) )
        encoded_repository_ids = []
        changeset_revisions = []
        for required_repository_tup in decoded_required_repository_tups:
            tool_shed, name, owner, changeset_revision = required_repository_tup
            repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
            encoded_repository_ids.append( trans.security.encode_id( repository.id ) )
            changeset_revisions.append( changeset_revision )
        if encoded_repository_ids and changeset_revisions:
            repo_info_dict = json.from_json_string( self.get_repository_information( trans, encoded_repository_ids, changeset_revisions ) )
        else:
            repo_info_dict = {}
        return repo_info_dict

    @web.expose
    def get_tool_dependencies( self, trans, **kwd ):
        """Handle a request from a Galaxy instance to get the tool_dependencies entry from the metadata for a specified changeset revision."""
        params = util.Params( kwd )
        name = params.get( 'name', None )
        owner = params.get( 'owner', None )
        changeset_revision = params.get( 'changeset_revision', None )
        repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
        for downloadable_revision in repository.downloadable_revisions:
            if downloadable_revision.changeset_revision == changeset_revision:
                break
        metadata = downloadable_revision.metadata
        tool_dependencies = metadata.get( 'tool_dependencies', '' )
        if tool_dependencies:
            return encoding_util.tool_shed_encode( tool_dependencies )
        return ''

    @web.expose
    def get_tool_dependencies_config_contents( self, trans, **kwd ):
        """Handle a request from a Galaxy instance to get the tool_dependencies.xml file contents for a specified changeset revision."""
        params = util.Params( kwd )
        name = params.get( 'name', None )
        owner = params.get( 'owner', None )
        changeset_revision = params.get( 'changeset_revision', None )
        repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
        # TODO: We're currently returning the tool_dependencies.xml file that is available on disk.  We need to enhance this process
        # to retrieve older versions of the tool-dependencies.xml file from the repository manafest.
        repo_dir = repository.repo_path( trans.app )
        # Get the tool_dependencies.xml file from disk.
        tool_dependencies_config = suc.get_config_from_disk( 'tool_dependencies.xml', repo_dir )
        # Return the encoded contents of the tool_dependencies.xml file.
        if tool_dependencies_config:
            tool_dependencies_config_file = open( tool_dependencies_config, 'rb' )
            contents = tool_dependencies_config_file.read()
            tool_dependencies_config_file.close()
            return contents
        return ''

    @web.expose
    def get_tool_versions( self, trans, **kwd ):
        """
        For each valid /downloadable change set (up to the received changeset_revision) in the repository's change log, append the change
        set's tool_versions dictionary to the list that will be returned.
        """
        name = kwd[ 'name' ]
        owner = kwd[ 'owner' ]
        changeset_revision = kwd[ 'changeset_revision' ]
        repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
        repo_dir = repository.repo_path( trans.app )
        repo = hg.repository( suc.get_configured_ui(), repo_dir )
        tool_version_dicts = []
        for changeset in repo.changelog:
            current_changeset_revision = str( repo.changectx( changeset ) )
            repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, trans.security.encode_id( repository.id ), current_changeset_revision )
            if repository_metadata and repository_metadata.tool_versions:
                tool_version_dicts.append( repository_metadata.tool_versions )
                if current_changeset_revision == changeset_revision:
                    break
        if tool_version_dicts:
            return json.to_json_string( tool_version_dicts )
        return ''

    @web.json
    def get_updated_repository_information( self, trans, name, owner, changeset_revision, **kwd ):
        """Generate a dictionary that contains the information about a repository that is necessary for installing it into a local Galaxy instance."""
        repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
        repository_id = trans.security.encode_id( repository.id )
        repository_clone_url = suc.generate_clone_url_for_repository_in_tool_shed( trans, repository )
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, repository_id, changeset_revision )
        repo_dir = repository.repo_path( trans.app )
        repo = hg.repository( suc.get_configured_ui(), repo_dir )
        ctx = suc.get_changectx_for_changeset( repo, changeset_revision )
        repo_info_dict = suc.create_repo_info_dict( trans=trans,
                                                    repository_clone_url=repository_clone_url,
                                                    changeset_revision=changeset_revision,
                                                    ctx_rev=str( ctx.rev() ),
                                                    repository_owner=repository.user.username,
                                                    repository_name=repository.name,
                                                    repository=repository,
                                                    repository_metadata=repository_metadata,
                                                    tool_dependencies=None,
                                                    repository_dependencies=None )
        includes_data_managers = False
        includes_datatypes = False
        includes_tools = False
        includes_workflows = False
        readme_files_dict = None
        metadata = repository_metadata.metadata
        if metadata:
            if 'data_manager' in metadata:
                includes_data_managers = True
            if 'datatypes' in metadata:
                includes_datatypes = True
            if 'tools' in metadata:
                includes_tools = True
            if 'workflows' in metadata:
                includes_workflows = True
            readme_files_dict = suc.build_readme_files_dict( metadata )
        # See if the repo_info_dict was populated with repository_dependencies or tool_dependencies.
        for name, repo_info_tuple in repo_info_dict.items():
            description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
                suc.get_repo_info_tuple_contents( repo_info_tuple )
            if repository_dependencies:
                has_repository_dependencies = True
            else:
                has_repository_dependencies = False
            if tool_dependencies:
                includes_tool_dependencies = True
            else:
                includes_tool_dependencies = False
        return dict( includes_data_managers=includes_data_managers,
                     includes_datatypes=includes_datatypes,
                     includes_tools=includes_tools,
                     has_repository_dependencies=has_repository_dependencies,
                     includes_tool_dependencies=includes_tool_dependencies,
                     includes_workflows=includes_workflows,
                     readme_files_dict=readme_files_dict,
                     repo_info_dict=repo_info_dict )

    def get_versions_of_tool( self, trans, repository, repository_metadata, guid ):
        """Return the tool lineage in descendant order for the received guid contained in the received repsitory_metadata.tool_versions."""
        encoded_id = trans.security.encode_id( repository.id )
        repo_dir = repository.repo_path( trans.app )
        repo = hg.repository( suc.get_configured_ui(), repo_dir )
        # Initialize the tool lineage
        tool_guid_lineage = [ guid ]
        # Get all ancestor guids of the received guid.
        current_child_guid = guid
        for changeset in suc.reversed_upper_bounded_changelog( repo, repository_metadata.changeset_revision ):
            ctx = repo.changectx( changeset )
            rm = suc.get_repository_metadata_by_changeset_revision( trans, encoded_id, str( ctx ) )
            if rm:
                parent_guid = rm.tool_versions.get( current_child_guid, None )
                if parent_guid:
                    tool_guid_lineage.append( parent_guid )
                    current_child_guid = parent_guid
        # Get all descendant guids of the received guid.
        current_parent_guid = guid
        for changeset in suc.reversed_lower_upper_bounded_changelog( repo, repository_metadata.changeset_revision, repository.tip( trans.app ) ):
            ctx = repo.changectx( changeset )
            rm = suc.get_repository_metadata_by_changeset_revision( trans, encoded_id, str( ctx ) )
            if rm:
                tool_versions = rm.tool_versions
                for child_guid, parent_guid in tool_versions.items():
                    if parent_guid == current_parent_guid:
                        tool_guid_lineage.insert( 0, child_guid )
                        current_parent_guid = child_guid
                        break
        return tool_guid_lineage

    @web.expose
    def help( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        return trans.fill_template( '/webapps/tool_shed/repository/help.mako', message=message, status=status, **kwd )

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

    def __in_workflow_dict( self, workflow_dict, exact_matches_checked, workflow_name ):
        workflow_dict_workflow_name = workflow_dict[ 'name' ].lower()
        return ( workflow_name == workflow_dict_workflow_name ) or \
               ( not exact_matches_checked and workflow_dict_workflow_name.find( workflow_name ) >= 0 )

    @web.expose
    def index( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        # See if there are any RepositoryMetadata records since menu items require them.
        repository_metadata = trans.sa_session.query( model.RepositoryMetadata ).first()
        current_user = trans.user
        has_reviewed_repositories = False
        has_deprecated_repositories = False
        if current_user:
            # See if the current user owns any repositories that have been reviewed.
            for repository in current_user.active_repositories:
                if repository.reviews:
                    has_reviewed_repositories = True
                    break
            # See if the current user has any repositories that have been marked as deprecated.
            for repository in current_user.active_repositories:
                if repository.deprecated:
                    has_deprecated_repositories = True
                    break
        # Route in may have been from a sharable URL, in whcih case we'll have a user_id and possibly a name
        # The received user_id will be the id of the repository owner.
        user_id = params.get( 'user_id', None )
        repository_id = params.get( 'repository_id', None )
        changeset_revision = params.get( 'changeset_revision', None )
        return trans.fill_template( '/webapps/tool_shed/index.mako',
                                    repository_metadata=repository_metadata,
                                    has_reviewed_repositories=has_reviewed_repositories,
                                    has_deprecated_repositories=has_deprecated_repositories,
                                    user_id=user_id,
                                    repository_id=repository_id,
                                    changeset_revision=changeset_revision,
                                    message=message,
                                    status=status )

    @web.expose
    def install_repositories_by_revision( self, trans, **kwd ):
        """
        Send the list of repository_ids and changeset_revisions to Galaxy so it can begin the installation process.  If the value of
        repository_ids is not received, then the name and owner of a single repository must be received to install a single repository.
        """
        repository_ids = kwd.get( 'repository_ids', None )
        changeset_revisions = kwd.get( 'changeset_revisions', None )
        name = kwd.get( 'name', None )
        owner = kwd.get( 'owner', None )
        galaxy_url = kwd.get( 'galaxy_url', None )
        if not repository_ids:
            repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
            repository_ids = trans.security.encode_id( repository.id )
        if not galaxy_url:
            # If galaxy_url is not in the request, it had to have been stored in a cookie by the tool shed.
            galaxy_url = trans.get_cookie( name='toolshedgalaxyurl' )
        # Redirect back to local Galaxy to perform install.
        url = suc.url_join( galaxy_url,
                            'admin_toolshed/prepare_for_install?tool_shed_url=%s&repository_ids=%s&changeset_revisions=%s' % \
                            ( web.url_for( '/', qualified=True ), ','.join( util.listify( repository_ids ) ), ','.join( util.listify( changeset_revisions ) ) ) )
        return trans.response.send_redirect( url )

    @web.expose
    def load_invalid_tool( self, trans, repository_id, tool_config, changeset_revision, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'error' )
        repository, tool, error_message = suc.load_tool_from_changeset_revision( trans, repository_id, changeset_revision, tool_config )
        tool_state = self.__new_state( trans )
        is_malicious = suc.changeset_is_malicious( trans, repository_id, repository.tip( trans.app ) )
        invalid_file_tups = []
        if tool:
            invalid_file_tups = suc.check_tool_input_params( trans.app,
                                                             repository.repo_path( trans.app ),
                                                             tool_config,
                                                             tool,
                                                             [] )
        if invalid_file_tups:
            message = suc.generate_message_for_invalid_tools( trans, invalid_file_tups, repository, {}, as_html=True, displaying_invalid_tool=True )
        elif error_message:
            message = error_message
        try:
            return trans.fill_template( "/webapps/tool_shed/repository/tool_form.mako",
                                        repository=repository,
                                        changeset_revision=changeset_revision,
                                        tool=tool,
                                        tool_state=tool_state,
                                        is_malicious=is_malicious,
                                        message=message,
                                        status='error' )
        except Exception, e:
            message = "Exception thrown attempting to display tool: %s." % str( e )
        if trans.webapp.name == 'galaxy':
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

    def __make_same_length( self, list1, list2 ):
        # If either list is 1 item, we'll append to it until its length is the same as the other.
        if len( list1 ) == 1:
            for i in range( 1, len( list2 ) ):
                list1.append( list1[ 0 ] )
        elif len( list2 ) == 1:
            for i in range( 1, len( list1 ) ):
                list2.append( list2[ 0 ] )
        return list1, list2

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
        return trans.fill_template( "/webapps/tool_shed/user/manage_email_alerts.mako",
                                    new_repo_alert_check_box=new_repo_alert_check_box,
                                    email_alert_repositories=email_alert_repositories,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_login( "manage repository" )
    def manage_repository( self, trans, id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = suc.get_repository_in_tool_shed( trans, id )
        repo_dir = repository.repo_path( trans.app )
        repo = hg.repository( suc.get_configured_ui(), repo_dir )
        repo_name = util.restore_text( params.get( 'repo_name', repository.name ) )
        changeset_revision = util.restore_text( params.get( 'changeset_revision', repository.tip( trans.app ) ) )
        description = util.restore_text( params.get( 'description', repository.description ) )
        long_description = util.restore_text( params.get( 'long_description', repository.long_description ) )
        avg_rating, num_ratings = self.get_ave_item_rating_data( trans.sa_session, repository, webapp_model=trans.model )
        display_reviews = util.string_as_bool( params.get( 'display_reviews', False ) )
        alerts = params.get( 'alerts', '' )
        alerts_checked = CheckboxField.is_checked( alerts )
        category_ids = util.listify( params.get( 'category_id', '' ) )
        if repository.email_alerts:
            email_alerts = json.from_json_string( repository.email_alerts )
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
                                                                  message=message,
                                                                  status='error' ) )
            if description != repository.description:
                repository.description = description
                flush_needed = True
            if long_description != repository.long_description:
                repository.long_description = long_description
                flush_needed = True
            if repository.times_downloaded == 0 and repo_name != repository.name:
                message = self.__validate_repository_name( repo_name, user )
                if message:
                    error = True
                else:
                    # Change the entry in the hgweb.config file for the repository.
                    old_lhs = "repos/%s/%s" % ( repository.user.username, repository.name )
                    new_lhs = "repos/%s/%s" % ( repository.user.username, repo_name )
                    trans.app.hgweb_config_manager.change_entry( old_lhs, new_lhs, repo_dir )
                    # Change the entry in the repository's hgrc file.
                    hgrc_file = os.path.join( repo_dir, '.hg', 'hgrc' )
                    self.__change_repository_name_in_hgrc_file( hgrc_file, repo_name )
                    repository.name = repo_name
                    flush_needed = True
            elif repository.times_downloaded != 0 and repo_name != repository.name:
                message = "Repository names cannot be changed if the repository has been cloned.  "
            if flush_needed:
                trans.sa_session.add( repository )
                trans.sa_session.flush()
                message += "The repository information has been updated."
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
                repository.set_allow_push( trans.app, usernames, remove_auth=remove_auth )
            message = "The repository information has been updated."
        elif params.get( 'receive_email_alerts_button', False ):
            flush_needed = False
            if alerts_checked:
                if user.email not in email_alerts:
                    email_alerts.append( user.email )
                    repository.email_alerts = json.to_json_string( email_alerts )
                    flush_needed = True
            else:
                if user.email in email_alerts:
                    email_alerts.remove( user.email )
                    repository.email_alerts = json.to_json_string( email_alerts )
                    flush_needed = True
            if flush_needed:
                trans.sa_session.add( repository )
                trans.sa_session.flush()
            message = "The repository information has been updated."
        if error:
            status = 'error'
        current_allow_push = repository.allow_push( trans.app )
        if current_allow_push:
            current_allow_push_list = current_allow_push.split( ',' )
        else:
            current_allow_push_list = []
        allow_push_select_field = self.__build_allow_push_select_field( trans, current_allow_push_list )
        checked = alerts_checked or user.email in email_alerts
        alerts_check_box = CheckboxField( 'alerts', checked=checked )
        changeset_revision_select_field = build_changeset_revision_select_field( trans,
                                                                                 repository,
                                                                                 selected_value=changeset_revision,
                                                                                 add_id_to_name=False,
                                                                                 downloadable=False )
        revision_label = suc.get_revision_label( trans, repository, repository.tip( trans.app ) )
        repository_metadata = None
        repository_metadata_id = None
        metadata = None
        is_malicious = False
        repository_dependencies = None
        if changeset_revision != suc.INITIAL_CHANGELOG_HASH:
            repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
            if repository_metadata:
                revision_label = suc.get_revision_label( trans, repository, changeset_revision )
                repository_metadata_id = trans.security.encode_id( repository_metadata.id )
                metadata = repository_metadata.metadata
                is_malicious = repository_metadata.malicious
            else:
                # There is no repository_metadata defined for the changeset_revision, so see if it was defined in a previous changeset in the changelog.
                previous_changeset_revision = suc.get_previous_downloadable_changeset_revision( repository, repo, changeset_revision )
                if previous_changeset_revision != suc.INITIAL_CHANGELOG_HASH:
                    repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, id, previous_changeset_revision )
                    if repository_metadata:
                        revision_label = suc.get_revision_label( trans, repository, previous_changeset_revision )
                        repository_metadata_id = trans.security.encode_id( repository_metadata.id )
                        metadata = repository_metadata.metadata
                        is_malicious = repository_metadata.malicious
            if repository_metadata:
                metadata = repository_metadata.metadata
                # Get a dictionary of all repositories upon which the contents of the current repository_metadata record depend.
                repository_dependencies = suc.get_repository_dependencies_for_changeset_revision( trans=trans,
                                                                                                  repository=repository,
                                                                                                  repository_metadata=repository_metadata,
                                                                                                  toolshed_base_url=str( web.url_for( '/', qualified=True ) ).rstrip( '/' ),
                                                                                                  key_rd_dicts_to_be_processed=None,
                                                                                                  all_repository_dependencies=None,
                                                                                                  handled_key_rd_dicts=None )
                # Handle messaging for orphan tool dependencies.
                orphan_message = suc.generate_message_for_orphan_tool_dependencies( metadata )
                if orphan_message:
                    message += orphan_message
                    status = 'warning'
        if is_malicious:
            if trans.app.security_agent.can_push( trans.app, trans.user, repository ):
                message += malicious_error_can_push
            else:
                message += malicious_error
            status = 'error'
        malicious_check_box = CheckboxField( 'malicious', checked=is_malicious )
        categories = suc.get_categories( trans )
        selected_categories = [ rca.category_id for rca in repository.categories ]
        # Determine if the current changeset revision has been reviewed by the current user.
        reviewed_by_user = suc.changeset_revision_reviewed_by_user( trans, trans.user, repository, changeset_revision )
        if reviewed_by_user:
            review = suc.get_review_by_repository_id_changeset_revision_user_id( trans=trans,
                                                                                 repository_id=id,
                                                                                 changeset_revision=changeset_revision,
                                                                                 user_id=trans.security.encode_id( trans.user.id ) )
            review_id = trans.security.encode_id( review.id )
        else:
            review_id = None
        can_browse_repository_reviews = suc.can_browse_repository_reviews( trans, repository )
        containers_dict = suc.build_repository_containers_for_tool_shed( trans, repository, changeset_revision, repository_dependencies, repository_metadata )
        return trans.fill_template( '/webapps/tool_shed/repository/manage_repository.mako',
                                    repo_name=repo_name,
                                    description=description,
                                    long_description=long_description,
                                    current_allow_push_list=current_allow_push_list,
                                    allow_push_select_field=allow_push_select_field,
                                    repo=repo,
                                    repository=repository,
                                    containers_dict=containers_dict,
                                    repository_metadata_id=repository_metadata_id,
                                    changeset_revision=changeset_revision,
                                    reviewed_by_user=reviewed_by_user,
                                    review_id=review_id,
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
                                    can_browse_repository_reviews=can_browse_repository_reviews,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_login( "review repository revision" )
    def manage_repository_reviews_of_revision( self, trans, **kwd ):
        return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                          action='manage_repository_reviews_of_revision',
                                                          **kwd ) )

    @web.expose
    @web.require_login( "multi select email alerts" )
    def multi_select_email_alerts( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
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
        self.email_alerts_repository_grid.title = "Set email alerts for repository changes"
        return self.email_alerts_repository_grid( trans, **kwd )

    def __new_state( self, trans, all_pages=False ):
        """
        Create a new `DefaultToolState` for this tool. It will not be initialized
        with default values for inputs. 
        
        Only inputs on the first page will be initialized unless `all_pages` is
        True, in which case all inputs regardless of page are initialized.
        """
        state = galaxy.tools.DefaultToolState()
        state.inputs = {}
        return state

    @web.json
    def open_folder( self, trans, folder_path ):
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        return suc.open_repository_files_folder( trans, folder_path )

    @web.expose
    def preview_tools_in_changeset( self, trans, repository_id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', '' ) )
        status = params.get( 'status', 'done' )
        repository = suc.get_repository_in_tool_shed( trans, repository_id )
        repo_dir = repository.repo_path( trans.app )
        repo = hg.repository( suc.get_configured_ui(), repo_dir )
        changeset_revision = util.restore_text( params.get( 'changeset_revision', repository.tip( trans.app ) ) )
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, repository_id, changeset_revision )
        if repository_metadata:
            repository_metadata_id = trans.security.encode_id( repository_metadata.id ),
            metadata = repository_metadata.metadata
            # Get a dictionary of all repositories upon which the contents of the current repository_metadata record depend.
            repository_dependencies = suc.get_repository_dependencies_for_changeset_revision( trans=trans,
                                                                                              repository=repository,
                                                                                              repository_metadata=repository_metadata,
                                                                                              toolshed_base_url=str( web.url_for( '/', qualified=True ) ).rstrip( '/' ),
                                                                                              key_rd_dicts_to_be_processed=None,
                                                                                              all_repository_dependencies=None,
                                                                                              handled_key_rd_dicts=None )
            if metadata:
                if 'repository_dependencies' in metadata and not repository_dependencies:
                    message += 'The repository dependency definitions for this repository are invalid and will be ignored.'
                    status = 'error'
        else:
            repository_metadata_id = None
            metadata = None
            repository_dependencies = None
        revision_label = suc.get_revision_label( trans, repository, changeset_revision )
        changeset_revision_select_field = build_changeset_revision_select_field( trans,
                                                                                 repository,
                                                                                 selected_value=changeset_revision,
                                                                                 add_id_to_name=False,
                                                                                 downloadable=False )
        containers_dict = suc.build_repository_containers_for_tool_shed( trans, repository, changeset_revision, repository_dependencies, repository_metadata )
        return trans.fill_template( '/webapps/tool_shed/repository/preview_tools_in_changeset.mako',
                                    repository=repository,
                                    containers_dict=containers_dict,
                                    repository_metadata_id=repository_metadata_id,
                                    changeset_revision=changeset_revision,
                                    revision_label=revision_label,
                                    changeset_revision_select_field=changeset_revision_select_field,
                                    metadata=metadata,
                                    message=message,
                                    status=status )

    @web.expose
    def previous_changeset_revisions( self, trans, **kwd ):
        """
        Handle a request from a local Galaxy instance.  This method will handle the case where the repository was previously installed using an
        older changeset_revsion, but later the repository was updated in the tool shed and the Galaxy admin is trying to install the latest
        changeset revision of the same repository instead of updating the one that was previously installed.
        """
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        # If the request originated with the UpdateManager, it will not include a galaxy_url.
        galaxy_url = kwd.get( 'galaxy_url', '' )
        name = params.get( 'name', None )
        owner = params.get( 'owner', None )
        changeset_revision = params.get( 'changeset_revision', None )
        repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
        repo_dir = repository.repo_path( trans.app )
        repo = hg.repository( suc.get_configured_ui(), repo_dir )
        # Get the lower bound changeset revision.
        lower_bound_changeset_revision = suc.get_previous_downloadable_changeset_revision( repository, repo, changeset_revision )
        # Build the list of changeset revision hashes.
        changeset_hashes = []
        for changeset in suc.reversed_lower_upper_bounded_changelog( repo, lower_bound_changeset_revision, changeset_revision ):
            changeset_hashes.append( str( repo.changectx( changeset ) ) )
        if changeset_hashes:
            changeset_hashes_str = ','.join( changeset_hashes )
            return changeset_hashes_str
        return ''

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
        repository = suc.get_repository_in_tool_shed( trans, id )
        repo = hg.repository( suc.get_configured_ui(), repository.repo_path( trans.app ) )
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
        is_malicious = suc.changeset_is_malicious( trans, id, repository.tip( trans.app ) )
        metadata = self.get_metadata( trans, id, repository.tip( trans.app ) )
        return trans.fill_template( '/webapps/tool_shed/repository/rate_repository.mako', 
                                    repository=repository,
                                    metadata=metadata,
                                    avg_rating=avg_rating,
                                    display_reviews=display_reviews,
                                    num_ratings=num_ratings,
                                    rra=rra,
                                    is_malicious=is_malicious,
                                    message=message,
                                    status=status )

    @web.expose
    def reset_all_metadata( self, trans, id, **kwd ):
        # This method is called only from the ~/templates/webapps/tool_shed/repository/manage_repository.mako template.
        # It resets all metadata on the complete changelog for a single repository in the tool shed.
        invalid_file_tups, metadata_dict = suc.reset_all_metadata_on_repository_in_tool_shed( trans, id, **kwd )
        if invalid_file_tups:
            repository = suc.get_repository_in_tool_shed( trans, id )
            message = suc.generate_message_for_invalid_tools( trans, invalid_file_tups, repository, metadata_dict )
            status = 'error'
        else:
            message = "All repository metadata has been reset.  "
            status = 'done'
        return trans.response.send_redirect( web.url_for( controller='repository',
                                                          action='manage_repository',
                                                          id=id,
                                                          message=message,
                                                          status=status ) )

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

    @web.expose
    def select_files_to_delete( self, trans, id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', '' ) )
        status = params.get( 'status', 'done' )
        commit_message = util.restore_text( params.get( 'commit_message', 'Deleted selected files' ) )
        repository = suc.get_repository_in_tool_shed( trans, id )
        repo_dir = repository.repo_path( trans.app )
        repo = hg.repository( suc.get_configured_ui(), repo_dir )
        selected_files_to_delete = util.restore_text( params.get( 'selected_files_to_delete', '' ) )
        if params.get( 'select_files_to_delete_button', False ):
            if selected_files_to_delete:
                selected_files_to_delete = selected_files_to_delete.split( ',' )
                # Get the current repository tip.
                tip = repository.tip( trans.app )
                for selected_file in selected_files_to_delete:
                    try:
                        commands.remove( repo.ui, repo, selected_file, force=True )
                    except Exception, e:
                        log.debug( "Error removing files using the mercurial API, so trying a different approach, the error was: %s" % str( e ))
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
                commands.commit( repo.ui, repo, repo_dir, user=trans.user.username, message=commit_message )
                suc.handle_email_alerts( trans, repository )
                # Update the repository files for browsing.
                suc.update_repository( repo )
                # Get the new repository tip.
                repo = hg.repository( suc.get_configured_ui(), repo_dir )
                if tip == repository.tip( trans.app ):
                    message += 'No changes to repository.  '
                    kwd[ 'message' ] = message
                    
                else:
                    message += 'The selected files were deleted from the repository.  '
                    kwd[ 'message' ] = message
                    suc.set_repository_metadata_due_to_new_tip( trans, repository, **kwd )
            else:
                message = "Select at least 1 file to delete from the repository before clicking <b>Delete selected files</b>."
                status = "error"
        is_malicious = suc.changeset_is_malicious( trans, id, repository.tip( trans.app ) )
        return trans.fill_template( '/webapps/tool_shed/repository/browse_repository.mako',
                                    repo=repo,
                                    repository=repository,
                                    commit_message=commit_message,
                                    is_malicious=is_malicious,
                                    message=message,
                                    status=status )

    @web.expose
    def send_to_owner( self, trans, id, message='' ):
        repository = suc.get_repository_in_tool_shed( trans, id )
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
            body = string.Template( suc.contact_owner_template ) \
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
                repository = suc.get_repository_in_tool_shed( trans, repository_id )
                if repository.email_alerts:
                    email_alerts = json.from_json_string( repository.email_alerts )
                else:
                    email_alerts = []
                if user.email in email_alerts:
                    email_alerts.remove( user.email )
                    repository.email_alerts = json.to_json_string( email_alerts )
                    trans.sa_session.add( repository )
                    flush_needed = True
                    total_alerts_removed += 1
                else:
                    email_alerts.append( user.email )
                    repository.email_alerts = json.to_json_string( email_alerts )
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
    @web.require_login( "set repository as malicious" )
    def set_malicious( self, trans, id, ctx_str, **kwd ):
        malicious = kwd.get( 'malicious', '' )
        if kwd.get( 'malicious_button', False ):
            repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, id, ctx_str )
            malicious_checked = CheckboxField.is_checked( malicious )
            repository_metadata.malicious = malicious_checked
            trans.sa_session.add( repository_metadata )
            trans.sa_session.flush()
            if malicious_checked:
                message = "The repository tip has been defined as malicious."
            else:
                message = "The repository tip has been defined as <b>not</b> malicious."
            status = 'done'
        return trans.response.send_redirect( web.url_for( controller='repository',
                                                          action='manage_repository',
                                                          id=id,
                                                          changeset_revision=ctx_str,
                                                          malicious=malicious,
                                                          message=message,
                                                          status=status ) )

    @web.expose
    def sharable_owner( self, trans, owner ):
        """Support for sharable URL for each repository owner's tools, e.g. http://example.org/view/owner."""
        try:
            user = suc.get_user_by_username( trans, owner )
        except:
            user = None
        if user:
            user_id = trans.security.encode_id( user.id )
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='index',
                                                              user_id=user_id ) )
        else:
            return trans.show_error_message( "The tool shed <b>%s</b> contains no repositories owned by <b>%s</b>." % \
                                             ( web.url_for( '/', qualified=True ).rstrip( '/' ), str( owner ) ) )

    @web.expose
    def sharable_repository( self, trans, owner, name ):
        """Support for sharable URL for a specified repository, e.g. http://example.org/view/owner/name."""
        try:
            repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
        except:
            repository = None
        if repository:
            repository_id = trans.security.encode_id( repository.id )
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='index',
                                                              repository_id=repository_id ) )
        else:
            # If the owner is valid, then show all of their repositories.
            try:
                user = suc.get_user_by_username( trans, owner )
            except:
                user = None
            if user:
                user_id = trans.security.encode_id( user.id )
                message = "This list of repositories owned by <b>%s</b>, does not include one named <b>%s</b>." % ( str( owner ), str( name ) )
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='index',
                                                                  user_id=user_id,
                                                                  message=message,
                                                                  status='error' ) )
            else:
                return trans.show_error_message( "The tool shed <b>%s</b> contains no repositories named <b>%s</b> with owner <b>%s</b>." % \
                                                 ( web.url_for( '/', qualified=True ).rstrip( '/' ), str( name ), str( owner ) ) )

    @web.expose
    def sharable_repository_revision( self, trans, owner, name, changeset_revision ):
        """Support for sharable URL for a specified repository revision, e.g. http://example.org/view/owner/name/changeset_revision."""
        try:
            repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
        except:
            repository = None
        if repository:
            repository_id = trans.security.encode_id( repository.id )
            repository_metadata = suc.get_repository_metadata_by_repository_id_changeset_revision( trans, repository_id, changeset_revision )
            if not repository_metadata:
                # Get updates to the received changeset_revision if any exist.
                repo_dir = repository.repo_path( trans.app )
                repo = hg.repository( suc.get_configured_ui(), repo_dir )
                upper_bound_changeset_revision = suc.get_next_downloadable_changeset_revision( repository, repo, changeset_revision )
                if upper_bound_changeset_revision:
                    changeset_revision = upper_bound_changeset_revision
                    repository_metadata = suc.get_repository_metadata_by_repository_id_changeset_revision( trans, repository_id, changeset_revision )
            if repository_metadata:
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='index',
                                                                  repository_id=repository_id,
                                                                  changeset_revision=changeset_revision ) )
            else:
                message = "The change log for the repository named <b>%s</b> owned by <b>%s</b> does not include revision <b>%s</b>." % \
                    ( str( name ), str( owner ), str( changeset_revision ) )
                return trans.response.send_redirect( web.url_for( controller='repository',
                                                                  action='index',
                                                                  repository_id=repository_id,
                                                                  message=message,
                                                                  status='error' ) )
        else:
            # See if the owner is valid.
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='sharable_owner',
                                                              owner=owner ) )

    def __stringify( self, list ):
        if list:
            return ','.join( list )
        return ''

    @web.expose
    def updated_changeset_revisions( self, trans, **kwd ):
        """
        Handle a request from a local Galaxy instance to retrieve the list of changeset revisions to which an installed repository can be updated.  This
        method will return a string of comma-separated changeset revision hashes for all available updates to the received changeset revision.  Among
        other things , this method handles the scenario where an installed tool shed repository's tool_dependency definition file defines a changeset
        revision for a complex repository dependency that is outdated.  In other words, a defined changeset revision is older than the current changeset
        revision for the required repository, making it impossible to discover the repository without knowledge of revisions to which it could have been
        updated.
        """
        params = util.Params( kwd )
        name = params.get( 'name', None )
        owner = params.get( 'owner', None )
        changeset_revision = params.get( 'changeset_revision', None )
        repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
        repo_dir = repository.repo_path( trans.app )
        repo = hg.repository( suc.get_configured_ui(), repo_dir )
        # Get the upper bound changeset revision.
        upper_bound_changeset_revision = suc.get_next_downloadable_changeset_revision( repository, repo, changeset_revision )
        # Build the list of changeset revision hashes defining each available update up to, but excluding, upper_bound_changeset_revision.
        changeset_hashes = []
        for changeset in suc.reversed_lower_upper_bounded_changelog( repo, changeset_revision, upper_bound_changeset_revision ):
            # Make sure to exclude upper_bound_changeset_revision.
            if changeset != upper_bound_changeset_revision:
                changeset_hashes.append( str( repo.changectx( changeset ) ) )
        if changeset_hashes:
            changeset_hashes_str = ','.join( changeset_hashes )
            return changeset_hashes_str
        return ''

    def __validate_repository_name( self, name, user ):
        # Repository names must be unique for each user, must be at least four characters
        # in length and must contain only lower-case letters, numbers, and the '_' character.
        if name in [ 'None', None, '' ]:
            return 'Enter the required repository name.'
        if name in [ 'repos' ]:
            return "The term <b>%s</b> is a reserved word in the tool shed, so it cannot be used as a repository name." % name
        for repository in user.active_repositories:
            if repository.name == name:
                return "You already have a repository named <b>%s</b>, so choose a different name." % name
        if len( name ) < 4:
            return "Repository names must be at least 4 characters in length."
        if len( name ) > 80:
            return "Repository names cannot be more than 80 characters in length."
        if not( VALID_REPOSITORYNAME_RE.match( name ) ):
            return "Repository names must contain only lower-case letters, numbers and underscore <b>_</b>."
        return ''

    @web.expose
    def view_changelog( self, trans, id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = suc.get_repository_in_tool_shed( trans, id )
        repo = hg.repository( suc.get_configured_ui(), repository.repo_path( trans.app ) )
        changesets = []
        for changeset in repo.changelog:
            ctx = repo.changectx( changeset )
            if suc.get_repository_metadata_by_changeset_revision( trans, id, str( ctx ) ):
                has_metadata = True
            else:
                has_metadata = False
            t, tz = ctx.date()
            date = datetime( *gmtime( float( t ) - tz )[:6] )
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
        is_malicious = suc.changeset_is_malicious( trans, id, repository.tip( trans.app ) )
        metadata = self.get_metadata( trans, id, repository.tip( trans.app ) )
        return trans.fill_template( '/webapps/tool_shed/repository/view_changelog.mako', 
                                    repository=repository,
                                    metadata=metadata,
                                    changesets=changesets,
                                    is_malicious=is_malicious,
                                    message=message,
                                    status=status )

    @web.expose
    def view_changeset( self, trans, id, ctx_str, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = suc.get_repository_in_tool_shed( trans, id )
        repo = hg.repository( suc.get_configured_ui(), repository.repo_path( trans.app ) )
        ctx = suc.get_changectx_for_changeset( repo, ctx_str )
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
            diffs.append( suc.to_safe_string( diff, to_html=True ) )
        is_malicious = suc.changeset_is_malicious( trans, id, repository.tip( trans.app ) )
        metadata = self.get_metadata( trans, id, ctx_str )
        return trans.fill_template( '/webapps/tool_shed/repository/view_changeset.mako', 
                                    repository=repository,
                                    metadata=metadata,
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
    def view_or_manage_repository( self, trans, **kwd ):
        repository = suc.get_repository_in_tool_shed( trans, kwd[ 'id' ] )
        if trans.user_is_admin() or repository.user == trans.user:
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='manage_repository',
                                                              **kwd ) )
        else:
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='view_repository',
                                                              **kwd ) )

    @web.expose
    def view_repository( self, trans, id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = suc.get_repository_in_tool_shed( trans, id )
        repo = hg.repository( suc.get_configured_ui(), repository.repo_path( trans.app ) )
        avg_rating, num_ratings = self.get_ave_item_rating_data( trans.sa_session, repository, webapp_model=trans.model )
        changeset_revision = util.restore_text( params.get( 'changeset_revision', repository.tip( trans.app ) ) )
        display_reviews = util.string_as_bool( params.get( 'display_reviews', False ) )
        alerts = params.get( 'alerts', '' )
        alerts_checked = CheckboxField.is_checked( alerts )
        if repository.email_alerts:
            email_alerts = json.from_json_string( repository.email_alerts )
        else:
            email_alerts = []
        repository_dependencies = None
        user = trans.user
        if user and params.get( 'receive_email_alerts_button', False ):
            flush_needed = False
            if alerts_checked:
                if user.email not in email_alerts:
                    email_alerts.append( user.email )
                    repository.email_alerts = json.to_json_string( email_alerts )
                    flush_needed = True
            else:
                if user.email in email_alerts:
                    email_alerts.remove( user.email )
                    repository.email_alerts = json.to_json_string( email_alerts )
                    flush_needed = True
            if flush_needed:
                trans.sa_session.add( repository )
                trans.sa_session.flush()
        checked = alerts_checked or ( user and user.email in email_alerts )
        alerts_check_box = CheckboxField( 'alerts', checked=checked )
        changeset_revision_select_field = build_changeset_revision_select_field( trans,
                                                                                 repository,
                                                                                 selected_value=changeset_revision,
                                                                                 add_id_to_name=False,
                                                                                 downloadable=False )
        revision_label = suc.get_revision_label( trans, repository, changeset_revision )
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, id, changeset_revision )
        if repository_metadata:
            repository_metadata_id = trans.security.encode_id( repository_metadata.id )
            metadata = repository_metadata.metadata
            # Get a dictionary of all repositories upon which the contents of the current repository_metadata record depend.
            repository_dependencies = suc.get_repository_dependencies_for_changeset_revision( trans=trans,
                                                                                              repository=repository,
                                                                                              repository_metadata=repository_metadata,
                                                                                              toolshed_base_url=str( web.url_for( '/', qualified=True ) ).rstrip( '/' ),
                                                                                              key_rd_dicts_to_be_processed=None,
                                                                                              all_repository_dependencies=None,
                                                                                              handled_key_rd_dicts=None )
            # Handle messaging for orphan tool dependencies.
            orphan_message = suc.generate_message_for_orphan_tool_dependencies( metadata )
            if orphan_message:
                message += orphan_message
                status = 'warning'
        else:
            repository_metadata_id = None
            metadata = None
        is_malicious = suc.changeset_is_malicious( trans, id, repository.tip( trans.app ) )
        if is_malicious:
            if trans.app.security_agent.can_push( trans.app, trans.user, repository ):
                message += malicious_error_can_push
            else:
                message += malicious_error
            status = 'error'
        # Determine if the current changeset revision has been reviewed by the current user.
        reviewed_by_user = suc.changeset_revision_reviewed_by_user( trans, trans.user, repository, changeset_revision )
        if reviewed_by_user:
            review = suc.get_review_by_repository_id_changeset_revision_user_id( trans=trans,
                                                                                 repository_id=id,
                                                                                 changeset_revision=changeset_revision,
                                                                                 user_id=trans.security.encode_id( trans.user.id ) )
            review_id = trans.security.encode_id( review.id )
        else:
            review_id = None
        containers_dict = suc.build_repository_containers_for_tool_shed( trans, repository, changeset_revision, repository_dependencies, repository_metadata )
        can_browse_repository_reviews = suc.can_browse_repository_reviews( trans, repository )
        return trans.fill_template( '/webapps/tool_shed/repository/view_repository.mako',
                                    repo=repo,
                                    repository=repository,
                                    repository_metadata_id=repository_metadata_id,
                                    metadata=metadata,
                                    containers_dict=containers_dict,
                                    avg_rating=avg_rating,
                                    display_reviews=display_reviews,
                                    num_ratings=num_ratings,
                                    alerts_check_box=alerts_check_box,
                                    changeset_revision=changeset_revision,
                                    reviewed_by_user=reviewed_by_user,
                                    review_id=review_id,
                                    changeset_revision_select_field=changeset_revision_select_field,
                                    revision_label=revision_label,
                                    is_malicious=is_malicious,
                                    can_browse_repository_reviews=can_browse_repository_reviews,
                                    message=message,
                                    status=status )

    @web.expose
    def view_tool_metadata( self, trans, repository_id, changeset_revision, tool_id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = suc.get_repository_in_tool_shed( trans, repository_id )
        repo_files_dir = repository.repo_path( trans.app )
        repo = hg.repository( suc.get_configured_ui(), repo_files_dir )
        tool_metadata_dict = {}
        tool_lineage = []
        tool = None
        guid = None
        original_tool_data_path = trans.app.config.tool_data_path
        revision_label = suc.get_revision_label( trans, repository, changeset_revision )
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, repository_id, changeset_revision )
        if repository_metadata:
            repository_metadata_id = trans.security.encode_id( repository_metadata.id )
            tool_test_errors = json.from_json_string( repository_metadata.tool_test_errors )
            metadata = repository_metadata.metadata
            if metadata:
                if 'tools' in metadata:
                    for tool_metadata_dict in metadata[ 'tools' ]:
                        if tool_metadata_dict[ 'id' ] == tool_id:
                            work_dir = tempfile.mkdtemp()
                            relative_path_to_tool_config = tool_metadata_dict[ 'tool_config' ]
                            guid = tool_metadata_dict[ 'guid' ]
                            full_path_to_tool_config = os.path.abspath( relative_path_to_tool_config )
                            full_path_to_dir, tool_config_filename = os.path.split( full_path_to_tool_config )
                            can_use_disk_file = suc.can_use_tool_config_disk_file( trans, repository, repo, full_path_to_tool_config, changeset_revision )
                            if can_use_disk_file:
                                trans.app.config.tool_data_path = work_dir
                                tool, valid, message, sample_files = suc.handle_sample_files_and_load_tool_from_disk( trans,
                                                                                                                      repo_files_dir,
                                                                                                                      full_path_to_tool_config,
                                                                                                                      work_dir )
                                if message:
                                    status = 'error'
                            else:
                                tool, message, sample_files = suc.handle_sample_files_and_load_tool_from_tmp_config( trans,
                                                                                                                     repo,
                                                                                                                     changeset_revision,
                                                                                                                     tool_config_filename,
                                                                                                                     work_dir )
                                if message:
                                    status = 'error'
                            break
                    if guid:
                        tool_lineage = self.get_versions_of_tool( trans, repository, repository_metadata, guid )
        else:
            repository_metadata_id = None
            metadata = None
            tool_test_errors = None
        is_malicious = suc.changeset_is_malicious( trans, repository_id, repository.tip( trans.app ) )
        changeset_revision_select_field = build_changeset_revision_select_field( trans,
                                                                                 repository,
                                                                                 selected_value=changeset_revision,
                                                                                 add_id_to_name=False,
                                                                                 downloadable=False )
        trans.app.config.tool_data_path = original_tool_data_path
        reviewed_by_user = suc.changeset_revision_reviewed_by_user( trans, trans.user, repository, changeset_revision )
        if reviewed_by_user:
            review = suc.get_review_by_repository_id_changeset_revision_user_id( trans=trans,
                                                                                 repository_id=repository_id,
                                                                                 changeset_revision=changeset_revision,
                                                                                 user_id=trans.security.encode_id( trans.user.id ) )
            review_id = trans.security.encode_id( review.id )
        else:
            review_id = None
        return trans.fill_template( "/webapps/tool_shed/repository/view_tool_metadata.mako",
                                    repository=repository,
                                    repository_metadata_id=repository_metadata_id,
                                    metadata=metadata,
                                    tool=tool,
                                    tool_metadata_dict=tool_metadata_dict,
                                    tool_lineage=tool_lineage,
                                    tool_test_errors=tool_test_errors,
                                    changeset_revision=changeset_revision,
                                    revision_label=revision_label,
                                    changeset_revision_select_field=changeset_revision_select_field,
                                    is_malicious=is_malicious,
                                    reviewed_by_user=reviewed_by_user,
                                    review_id=review_id,
                                    message=message,
                                    status=status )

    @web.expose
    def view_workflow( self, trans, workflow_name, repository_metadata_id, **kwd ):
        """Retrieve necessary information about a workflow from the database so that it can be displayed in an svg image."""
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        if workflow_name:
            workflow_name = encoding_util.tool_shed_decode( workflow_name )
        repository_metadata = suc.get_repository_metadata_by_id( trans, repository_metadata_id )
        repository = suc.get_repository_in_tool_shed( trans, trans.security.encode_id( repository_metadata.repository_id ) )
        changeset_revision = repository_metadata.changeset_revision
        metadata = repository_metadata.metadata
        return trans.fill_template( "/webapps/tool_shed/repository/view_workflow.mako",
                                    repository=repository,
                                    changeset_revision=changeset_revision,
                                    repository_metadata_id=repository_metadata_id,
                                    workflow_name=workflow_name,
                                    metadata=metadata,
                                    message=message,
                                    status=status )

# ----- Utility methods -----

def build_changeset_revision_select_field( trans, repository, selected_value=None, add_id_to_name=True,
                                           downloadable=False, reviewed=False, not_reviewed=False ):
    """Build a SelectField whose options are the changeset_rev strings of certain revisions of the received repository."""
    options = []
    changeset_tups = []
    refresh_on_change_values = []
    if downloadable:
        # Restrict the options to downloadable revisions.
        repository_metadata_revisions = repository.downloadable_revisions
    elif reviewed:
        # Restrict the options to revisions that have been reviewed.
        repository_metadata_revisions = []
        metadata_changeset_revision_hashes = []
        for metadata_revision in repository.metadata_revisions:
            metadata_changeset_revision_hashes.append( metadata_revision.changeset_revision )
        for review in repository.reviews:
            if review.changeset_revision in metadata_changeset_revision_hashes:
                repository_metadata_revisions.append( review.repository_metadata )
    elif not_reviewed:
        # Restrict the options to revisions that have not yet been reviewed.
        repository_metadata_revisions = []
        reviewed_metadata_changeset_revision_hashes = []
        for review in repository.reviews:
            reviewed_metadata_changeset_revision_hashes.append( review.changeset_revision )
        for metadata_revision in repository.metadata_revisions:
            if metadata_revision.changeset_revision not in reviewed_metadata_changeset_revision_hashes:
                repository_metadata_revisions.append( metadata_revision )
    else:
        # Restrict the options to all revisions that have associated metadata.
        repository_metadata_revisions = repository.metadata_revisions
    for repository_metadata in repository_metadata_revisions:
        rev, label, changeset_revision = suc.get_rev_label_changeset_revision_from_repository_metadata( trans, repository_metadata, repository=repository )
        changeset_tups.append( ( rev, label, changeset_revision ) )
        refresh_on_change_values.append( changeset_revision )
    # Sort options by the revision label.  Even though the downloadable_revisions query sorts by update_time,
    # the changeset revisions may not be sorted correctly because setting metadata over time will reset update_time.
    for changeset_tup in sorted( changeset_tups ):
        # Display the latest revision first.
        options.insert( 0, ( changeset_tup[1], changeset_tup[2] ) )
    if add_id_to_name:
        name = 'changeset_revision_%d' % repository.id
    else:
        name = 'changeset_revision'
    select_field = SelectField( name=name,
                                refresh_on_change=True,
                                refresh_on_change_values=refresh_on_change_values )
    for option_tup in options:
        selected = selected_value and option_tup[1] == selected_value
        select_field.add_option( option_tup[0], option_tup[1], selected=selected )
    return select_field
