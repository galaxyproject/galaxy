import logging
import os
from galaxy.webapps.tool_shed import model
from galaxy.web.framework.helpers import grids
from galaxy.model.orm import and_
from galaxy.model.orm import or_
from galaxy.util import json
import tool_shed.util.shed_util_common as suc
import tool_shed.grids.util as grids_util
from tool_shed.util import metadata_util

from galaxy import eggs

eggs.require('markupsafe')
from markupsafe import escape as escape_html

eggs.require('mercurial')
from mercurial import commands
from mercurial import hg
from mercurial import patch
from mercurial import ui

log = logging.getLogger( __name__ )

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
    use_paging = False


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
            select_field = grids_util.build_changeset_revision_select_field( trans, repository, downloadable=False )
            if len( select_field.options ) > 1:
                return select_field.get_html()
            elif len( select_field.options ) == 1:
                return select_field.options[ 0 ][ 0 ]
            return ''


    class LatestInstallableRevisionColumn( grids.GridColumn ):

        def __init__( self, col_name ):
            grids.GridColumn.__init__( self, col_name )

        def get_value( self, trans, grid, repository ):
            """Display the latest installable revision label (may not be the repository tip)."""
            select_field = grids_util.build_changeset_revision_select_field( trans, repository, downloadable=False )
            if select_field.options:
                return select_field.options[ 0 ][ 0 ]
            return ''


    class TipRevisionColumn( grids.GridColumn ):

        def __init__( self, col_name ):
            grids.GridColumn.__init__( self, col_name )

        def get_value( self, trans, grid, repository ):
            """Display the repository tip revision label."""
            return escape_html( repository.revision( trans.app ) )


    class ToolsFunctionallyCorrectColumn( grids.BooleanColumn ):

        def get_value( self, trans, grid, repository ):
            # This column will display the value associated with the currently displayed metadata revision.
            try:
                displayed_metadata_revision = repository.metadata_revisions[ -1 ]
                if displayed_metadata_revision.includes_tools:
                    if displayed_metadata_revision.tools_functionally_correct:
                        return 'yes'
                    else:
                        return 'no'
                return 'n/a'
            except:
                return 'n/a'


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
                    attach_popup=False ),
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
    operations = []
    standard_filters = []
    default_filter = dict( deleted="False" )
    num_rows_per_page = 50
    preserve_state = False
    use_paging = False

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( model.Repository ) \
                               .filter( and_( model.Repository.table.c.deleted == False,
                                              model.Repository.table.c.deprecated == False ) ) \
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
    operations = []
    global_actions = [
            grids.GridAction( "User preferences", dict( controller='user', action='index', cntrller='repository' ) )
    ]


class MatchedRepositoryGrid( grids.Grid ):
    # This grid filters out repositories that have been marked as deleted or deprecated.


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
    operations = [ grids.GridOperation( "Install to Galaxy", allow_multiple=True  ) ]
    standard_filters = []
    default_filter = {}
    num_rows_per_page = 50
    preserve_state = False
    use_paging = False

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


class MyWritableRepositoriesGrid( RepositoryGrid ):
    # This grid filters out repositories that have been marked as either deprecated or deleted.
    title = 'Repositories I can change'
    columns = [
        RepositoryGrid.NameColumn( "Name",
                                   key="name",
                                   link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                   attach_popup=False ),
        RepositoryGrid.MetadataRevisionColumn( "Metadata Revisions" ),
        RepositoryGrid.ToolsFunctionallyCorrectColumn( "Tools Verified" ),
        RepositoryGrid.UserColumn( "Owner",
                                   model_class=model.User,
                                   link=( lambda item: dict( operation="repositories_by_user", id=item.id ) ),
                                   attach_popup=False,
                                   key="User.username" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name", 
                                                cols_to_filter=[ columns[ 0 ] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = []
    use_paging = False

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
                                   .join( model.User.table )
        # Return an empty query.
        return trans.sa_session.query( model.Repository ) \
                               .filter( model.Repository.table.c.id < 0 )


class RepositoriesByUserGrid( RepositoryGrid ):
    title = "Repositories by user"
    columns = [
        RepositoryGrid.NameColumn( "Name",
                                   key="name",
                                   link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                   attach_popup=False ),
        RepositoryGrid.DescriptionColumn( "Synopsis",
                                          key="description",
                                          attach_popup=False ),
        RepositoryGrid.MetadataRevisionColumn( "Metadata Revisions" ),
        RepositoryGrid.ToolsFunctionallyCorrectColumn( "Tools Verified" ),
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
    use_paging = False

    def build_initial_query( self, trans, **kwd ):
        decoded_user_id = trans.security.decode_id( kwd[ 'user_id' ] )
        return trans.sa_session.query( model.Repository ) \
                               .filter( and_( model.Repository.table.c.deleted == False,
                                              model.Repository.table.c.deprecated == False,
                                              model.Repository.table.c.user_id == decoded_user_id ) ) \
                               .join( model.User.table ) \
                               .outerjoin( model.RepositoryCategoryAssociation.table ) \
                               .outerjoin( model.Category.table )


class RepositoriesInCategoryGrid( RepositoryGrid ):
    title = "Category"

    columns = [
        RepositoryGrid.NameColumn( "Name",
                                   key="name",
                                   link=( lambda item: dict( controller="repository", operation="view_or_manage_repository", id=item.id ) ),
                                   attach_popup=False ),
        RepositoryGrid.DescriptionColumn( "Synopsis",
                                          key="description",
                                          attach_popup=False ),
        RepositoryGrid.MetadataRevisionColumn( "Metadata Revisions" ),
        RepositoryGrid.ToolsFunctionallyCorrectColumn( "Tools Verified" ),
        RepositoryGrid.UserColumn( "Owner",
                                   model_class=model.User,
                                   link=( lambda item: dict( controller="repository", operation="repositories_by_user", id=item.id ) ),
                                   attach_popup=False,
                                   key="User.username" ),
        # Columns that are valid for filtering but are not visible.
        RepositoryGrid.EmailColumn( "Email",
                                    model_class=model.User,
                                    key="email",
                                    visible=False )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name, description", 
                                                cols_to_filter=[ columns[0], columns[1] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = []
    use_paging = False

    def build_initial_query( self, trans, **kwd ):
        category_id = kwd.get( 'id', None )
        if category_id:
            category = suc.get_category( trans, category_id )
            if category:
                return trans.sa_session.query( model.Repository ) \
                                       .filter( and_( model.Repository.table.c.deleted == False,
                                                      model.Repository.table.c.deprecated == False ) ) \
                                       .join( model.User.table ) \
                                       .outerjoin( model.RepositoryCategoryAssociation.table ) \
                                       .outerjoin( model.Category.table ) \
                                       .filter( model.Category.table.c.name == category.name )
        return trans.sa_session.query( model.Repository ) \
                               .filter( and_( model.Repository.table.c.deleted == False,
                                              model.Repository.table.c.deprecated == False ) ) \
                               .join( model.User.table ) \
                               .outerjoin( model.RepositoryCategoryAssociation.table ) \
                               .outerjoin( model.Category.table )


class RepositoriesIOwnGrid( RepositoryGrid ):
    title = "Repositories I own"
    columns = [
        RepositoryGrid.NameColumn( "Name",
                                   key="name",
                                   link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                   attach_popup=False ),
        RepositoryGrid.MetadataRevisionColumn( "Metadata Revisions" ),
        RepositoryGrid.ToolsFunctionallyCorrectColumn( "Tools Verified" ),
        RepositoryGrid.DeprecatedColumn( "Deprecated" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name", 
                                                cols_to_filter=[ columns[0] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = []
    use_paging = False

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( model.Repository ) \
                               .filter( and_( model.Repository.table.c.deleted == False,
                                              model.Repository.table.c.user_id == trans.user.id ) ) \
                               .join( model.User.table ) \
                               .outerjoin( model.RepositoryCategoryAssociation.table ) \
                               .outerjoin( model.Category.table )


class RepositoriesMissingToolTestComponentsGrid( RepositoryGrid ):
    # This grid displays only the latest installable revision of each repository.
    title = "Repositories with missing tool test components"
    columns = [
        RepositoryGrid.NameColumn( "Name",
                                   key="name",
                                   link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                   attach_popup=False ),
        RepositoryGrid.LatestInstallableRevisionColumn( "Latest Installable Revision" ),
        RepositoryGrid.UserColumn( "Owner",
                                   key="User.username",
                                   model_class=model.User,
                                   link=( lambda item: dict( operation="repositories_by_user", id=item.id ) ),
                                   attach_popup=False )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name", 
                                                cols_to_filter=[ columns[0] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = []
    use_paging = False

    def build_initial_query( self, trans, **kwd ):
        # Filter by latest installable revisions that contain tools with missing tool test components.
        revision_clause_list = []
        for repository in trans.sa_session.query( model.Repository ) \
                                          .filter( and_( model.Repository.table.c.deprecated == False,
                                                         model.Repository.table.c.deleted == False ) ):
            changeset_revision = filter_by_latest_downloadable_changeset_revision_that_has_missing_tool_test_components( trans, repository )
            if changeset_revision:
                revision_clause_list.append( model.RepositoryMetadata.table.c.changeset_revision == changeset_revision )
        if revision_clause_list:
            return trans.sa_session.query( model.Repository ) \
                                   .filter( and_( model.Repository.table.c.deprecated == False,
                                                  model.Repository.table.c.deleted == False ) ) \
                                   .join( model.RepositoryMetadata ) \
                                   .filter( or_( *revision_clause_list ) ) \
                                   .join( model.User.table )
        # Return an empty query.
        return trans.sa_session.query( model.Repository ) \
                               .filter( model.Repository.table.c.id < 0 )


class MyWritableRepositoriesMissingToolTestComponentsGrid( RepositoriesMissingToolTestComponentsGrid ):
    # This grid displays only the latest installable revision of each repository.
    title = "Repositories I can change with missing tool test components"
    columns = [ col for col in RepositoriesMissingToolTestComponentsGrid.columns ]
    operations = []
    use_paging = False

    def build_initial_query( self, trans, **kwd ):
        # First get all repositories that the current user is authorized to update.
        username = trans.user.username
        user_clause_list = []
        for repository in trans.sa_session.query( model.Repository ) \
                                          .filter( and_( model.Repository.table.c.deprecated == False,
                                                         model.Repository.table.c.deleted == False ) ):
            allow_push = repository.allow_push( trans.app )
            if allow_push:
                allow_push_usernames = allow_push.split( ',' )
                if username in allow_push_usernames:
                    user_clause_list.append( model.Repository.table.c.id == repository.id )
        if user_clause_list:
            # We have the list of repositories that the current user is authorized to update, so filter further by latest installable revisions that contain
            # tools with missing tool test components.
            revision_clause_list = []
            for repository in trans.sa_session.query( model.Repository ) \
                                              .filter( and_( model.Repository.table.c.deprecated == False,
                                                             model.Repository.table.c.deleted == False ) ) \
                                              .filter( or_( *user_clause_list ) ):
                changeset_revision = filter_by_latest_downloadable_changeset_revision_that_has_missing_tool_test_components( trans, repository )
                if changeset_revision:
                    revision_clause_list.append( model.RepositoryMetadata.table.c.changeset_revision == changeset_revision )
            if revision_clause_list:
                return trans.sa_session.query( model.Repository ) \
                                       .filter( and_( model.Repository.table.c.deprecated == False,
                                                      model.Repository.table.c.deleted == False ) ) \
                                       .join( model.User.table ) \
                                       .filter( or_( *user_clause_list ) ) \
                                       .join( model.RepositoryMetadata ) \
                                       .filter( or_( *revision_clause_list ) )
        # Return an empty query.
        return trans.sa_session.query( model.Repository ) \
                               .filter( model.Repository.table.c.id < 0 )


class DeprecatedRepositoriesIOwnGrid( RepositoriesIOwnGrid ):
    title = "Deprecated repositories I own"
    columns = [
        RepositoriesIOwnGrid.NameColumn( "Name",
                                         key="name",
                                         link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                         attach_popup=False ),
        RepositoriesIOwnGrid.MetadataRevisionColumn( "Metadata Revisions" ),
        RepositoryGrid.ToolsFunctionallyCorrectColumn( "Tools Verified" ),
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
    use_paging = False

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( model.Repository ) \
                               .filter( and_( model.Repository.table.c.deleted == False,
                                              model.Repository.table.c.user_id == trans.user.id,
                                              model.Repository.table.c.deprecated == True ) ) \
                               .join( model.User.table ) \
                               .outerjoin( model.RepositoryCategoryAssociation.table ) \
                               .outerjoin( model.Category.table )


class RepositoriesWithFailingToolTestsGrid( RepositoryGrid ):
    # This grid displays only the latest installable revision of each repository.
    title = "Repositories with failing tool tests"
    columns = [
        RepositoryGrid.NameColumn( "Name",
                                   key="name",
                                   link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                   attach_popup=False ),
        RepositoryGrid.LatestInstallableRevisionColumn( "Latest Installable Revision" ),
        RepositoryGrid.UserColumn( "Owner",
                                   key="User.username",
                                   model_class=model.User,
                                   link=( lambda item: dict( operation="repositories_by_user", id=item.id ) ),
                                   attach_popup=False )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name", 
                                                cols_to_filter=[ columns[0] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = []
    use_paging = False

    def build_initial_query( self, trans, **kwd ):
        # Filter by latest installable revisions that contain tools with at least 1 failing tool test.
        revision_clause_list = []
        for repository in trans.sa_session.query( model.Repository ) \
                                          .filter( and_( model.Repository.table.c.deprecated == False,
                                                         model.Repository.table.c.deleted == False ) ):
            changeset_revision = filter_by_latest_downloadable_changeset_revision_that_has_failing_tool_tests( trans, repository )
            if changeset_revision:
                revision_clause_list.append( model.RepositoryMetadata.table.c.changeset_revision == changeset_revision )
        if revision_clause_list:
            return trans.sa_session.query( model.Repository ) \
                                   .filter( and_( model.Repository.table.c.deprecated == False,
                                                  model.Repository.table.c.deleted == False ) ) \
                                   .join( model.RepositoryMetadata ) \
                                   .filter( or_( *revision_clause_list ) ) \
                                   .join( model.User.table )
        # Return an empty query.
        return trans.sa_session.query( model.Repository ) \
                               .filter( model.Repository.table.c.id < 0 )


class MyWritableRepositoriesWithFailingToolTestsGrid( RepositoriesWithFailingToolTestsGrid ):
    # This grid displays only the latest installable revision of each repository.
    title = "Repositories I can change with failing tool tests"
    columns = [ col for col in RepositoriesWithFailingToolTestsGrid.columns ]
    operations = []
    use_paging = False

    def build_initial_query( self, trans, **kwd ):
        # First get all repositories that the current user is authorized to update.
        username = trans.user.username
        user_clause_list = []
        for repository in trans.sa_session.query( model.Repository ) \
                                          .filter( and_( model.Repository.table.c.deprecated == False,
                                                         model.Repository.table.c.deleted == False ) ):
            allow_push = repository.allow_push( trans.app )
            if allow_push:
                allow_push_usernames = allow_push.split( ',' )
                if username in allow_push_usernames:
                    user_clause_list.append( model.Repository.table.c.id == repository.id )
        if user_clause_list:
            # We have the list of repositories that the current user is authorized to update, so filter further by latest installable revisions that contain
            # tools with at least 1 failing tool test.
            revision_clause_list = []
            for repository in trans.sa_session.query( model.Repository ) \
                                              .filter( and_( model.Repository.table.c.deprecated == False,
                                                             model.Repository.table.c.deleted == False ) ) \
                                              .filter( or_( *user_clause_list ) ):
                changeset_revision = filter_by_latest_downloadable_changeset_revision_that_has_failing_tool_tests( trans, repository )
                if changeset_revision:
                    revision_clause_list.append( model.RepositoryMetadata.table.c.changeset_revision == changeset_revision )
            if revision_clause_list:
                return trans.sa_session.query( model.Repository ) \
                                       .filter( and_( model.Repository.table.c.deprecated == False,
                                                      model.Repository.table.c.deleted == False ) ) \
                                       .join( model.User.table ) \
                                       .filter( or_( *user_clause_list ) ) \
                                       .join( model.RepositoryMetadata ) \
                                       .filter( or_( *revision_clause_list ) )
        # Return an empty query.
        return trans.sa_session.query( model.Repository ) \
                               .filter( model.Repository.table.c.id < 0 )


class RepositoriesWithNoFailingToolTestsGrid( RepositoryGrid ):
    # This grid displays only the latest installable revision of each repository.
    title = "Repositories with no failing tool tests"
    columns = [
        RepositoryGrid.NameColumn( "Name",
                                   key="name",
                                   link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                   attach_popup=False ),
        RepositoryGrid.LatestInstallableRevisionColumn( "Latest Installable Revision" ),
        RepositoryGrid.UserColumn( "Owner",
                                   key="User.username",
                                   model_class=model.User,
                                   link=( lambda item: dict( operation="repositories_by_user", id=item.id ) ),
                                   attach_popup=False )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name", 
                                                cols_to_filter=[ columns[0] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = []
    use_paging = False

    def build_initial_query( self, trans, **kwd ):
        # We have the list of repositories that the current user is authorized to update, so filter further by latest installable revisions that contain
        # tools with at least 1 failing tool test.
        revision_clause_list = []
        for repository in trans.sa_session.query( model.Repository ) \
                                          .filter( and_( model.Repository.table.c.deprecated == False,
                                                         model.Repository.table.c.deleted == False ) ):
            changeset_revision = filter_by_latest_downloadable_changeset_revision_that_has_no_failing_tool_tests( trans, repository )
            if changeset_revision:
                revision_clause_list.append( model.RepositoryMetadata.table.c.changeset_revision == changeset_revision )
        if revision_clause_list:
            return trans.sa_session.query( model.Repository ) \
                                   .filter( and_( model.Repository.table.c.deprecated == False,
                                                  model.Repository.table.c.deleted == False ) ) \
                                   .join( model.RepositoryMetadata ) \
                                   .filter( or_( *revision_clause_list ) ) \
                                   .join( model.User.table )
        # Return an empty query.
        return trans.sa_session.query( model.Repository ) \
                               .filter( model.Repository.table.c.id < 0 )


class MyWritableRepositoriesWithNoFailingToolTestsGrid( RepositoriesWithNoFailingToolTestsGrid ):
    # This grid displays only the latest installable revision of each repository.
    title = "Repositories I can change with no failing tool tests"
    columns = [ col for col in RepositoriesWithNoFailingToolTestsGrid.columns ]
    operations = []
    use_paging = False

    def build_initial_query( self, trans, **kwd ):
        # First get all repositories that the current user is authorized to update.
        username = trans.user.username
        user_clause_list = []
        for repository in trans.sa_session.query( model.Repository ) \
                                          .filter( and_( model.Repository.table.c.deprecated == False,
                                                         model.Repository.table.c.deleted == False ) ):
            allow_push = repository.allow_push( trans.app )
            if allow_push:
                allow_push_usernames = allow_push.split( ',' )
                if username in allow_push_usernames:
                    user_clause_list.append( model.Repository.table.c.id == repository.id )
        if user_clause_list:
            # We have the list of repositories that the current user is authorized to update, so filter further by latest installable revisions that contain
            # at least 1 tool, no missing tool test components, and no failing tool tests.
            revision_clause_list = []
            for repository in trans.sa_session.query( model.Repository ) \
                                              .filter( and_( model.Repository.table.c.deprecated == False,
                                                             model.Repository.table.c.deleted == False ) ) \
                                              .filter( or_( *user_clause_list ) ):
                changeset_revision = filter_by_latest_downloadable_changeset_revision_that_has_no_failing_tool_tests( trans, repository )
                if changeset_revision:
                    revision_clause_list.append( model.RepositoryMetadata.table.c.changeset_revision == changeset_revision )
            if revision_clause_list:
                return trans.sa_session.query( model.Repository ) \
                                       .filter( and_( model.Repository.table.c.deprecated == False,
                                                      model.Repository.table.c.deleted == False ) ) \
                                       .join( model.User.table ) \
                                       .filter( or_( *user_clause_list ) ) \
                                       .join( model.RepositoryMetadata ) \
                                       .filter( or_( *revision_clause_list ) )
        # Return an empty query.
        return trans.sa_session.query( model.Repository ) \
                               .filter( model.Repository.table.c.id < 0 )


class RepositoriesWithInvalidToolsGrid( RepositoryGrid ):
    # This grid displays only the latest installable revision of each repository.


    class InvalidToolConfigColumn( grids.GridColumn ):

        def __init__( self, col_name ):
            grids.GridColumn.__init__( self, col_name )

        def get_value( self, trans, grid, repository ):
            # At the time this grid is displayed we know that the received repository will have invalid tools in it's latest changeset revision
            # that has associated metadata.
            val = ''
            repository_metadata = get_latest_repository_metadata_if_it_includes_invalid_tools( trans, repository )
            metadata = repository_metadata.metadata
            invalid_tools = metadata.get( 'invalid_tools', [] )
            if invalid_tools:
                for invalid_tool_config in invalid_tools:
                    href_str = '<a href="load_invalid_tool?repository_id=%s&tool_config=%s&changeset_revision=%s">%s</a>' % \
                        ( trans.security.encode_id( repository.id ), invalid_tool_config, repository_metadata.changeset_revision, invalid_tool_config )
                    val += href_str
                    val += '<br/>'
                val = val.rstrip( '<br/>' )
            return val

    title = "Repositories with invalid tools"
    columns = [               
        InvalidToolConfigColumn( "Tool config" ),
        RepositoryGrid.NameColumn( "Name",
                                   key="name",
                                   link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                   attach_popup=False ),
        RepositoryGrid.LatestInstallableRevisionColumn( "Latest Metadata Revision" ),
        RepositoryGrid.UserColumn( "Owner",
                                   key="User.username",
                                   model_class=model.User,
                                   link=( lambda item: dict( operation="repositories_by_user", id=item.id ) ),
                                   attach_popup=False )
    ]
    operations = []
    use_paging = False

    def build_initial_query( self, trans, **kwd ):
        # Filter by latest metadata revisions that contain invalid tools.
        revision_clause_list = []
        for repository in trans.sa_session.query( model.Repository ) \
                                          .filter( and_( model.Repository.table.c.deprecated == False,
                                                         model.Repository.table.c.deleted == False ) ):
            changeset_revision = filter_by_latest_metadata_changeset_revision_that_has_invalid_tools( trans, repository )
            if changeset_revision:
                revision_clause_list.append( model.RepositoryMetadata.table.c.changeset_revision == changeset_revision )
        if revision_clause_list:
            return trans.sa_session.query( model.Repository ) \
                                   .filter( and_( model.Repository.table.c.deprecated == False,
                                                  model.Repository.table.c.deleted == False ) ) \
                                   .join( model.RepositoryMetadata ) \
                                   .filter( or_( *revision_clause_list ) ) \
                                   .join( model.User.table )
        # Return an empty query.
        return trans.sa_session.query( model.Repository ) \
                               .filter( model.Repository.table.c.id < 0 )


class MyWritableRepositoriesWithInvalidToolsGrid( RepositoriesWithInvalidToolsGrid ):
    # This grid displays only the latest installable revision of each repository.
    title = "Repositories I can change with invalid tools"
    columns = [ col for col in RepositoriesWithInvalidToolsGrid.columns ]
    operations = []
    use_paging = False

    def build_initial_query( self, trans, **kwd ):
        # First get all repositories that the current user is authorized to update.
        username = trans.user.username
        user_clause_list = []
        for repository in trans.sa_session.query( model.Repository ) \
                                          .filter( and_( model.Repository.table.c.deprecated == False,
                                                         model.Repository.table.c.deleted == False ) ):
            allow_push = repository.allow_push( trans.app )
            if allow_push:
                allow_push_usernames = allow_push.split( ',' )
                if username in allow_push_usernames:
                    user_clause_list.append( model.Repository.table.c.id == repository.id )
        if user_clause_list:
            # We have the list of repositories that the current user is authorized to update, so filter further by latest metadata revisions that contain
            # invalid tools.
            revision_clause_list = []
            for repository in trans.sa_session.query( model.Repository ) \
                                              .filter( and_( model.Repository.table.c.deprecated == False,
                                                             model.Repository.table.c.deleted == False ) ) \
                                              .filter( or_( *user_clause_list ) ):
                changeset_revision = filter_by_latest_metadata_changeset_revision_that_has_invalid_tools( trans, repository )
                if changeset_revision:
                    revision_clause_list.append( model.RepositoryMetadata.table.c.changeset_revision == changeset_revision )
            if revision_clause_list:
                return trans.sa_session.query( model.Repository ) \
                                       .filter( and_( model.Repository.table.c.deprecated == False,
                                                      model.Repository.table.c.deleted == False ) ) \
                                       .join( model.User.table ) \
                                       .filter( or_( *user_clause_list ) ) \
                                       .join( model.RepositoryMetadata ) \
                                       .filter( or_( *revision_clause_list ) )
        # Return an empty query.
        return trans.sa_session.query( model.Repository ) \
                               .filter( model.Repository.table.c.id < 0 )


class RepositoryMetadataGrid( grids.Grid ):


    class RepositoryNameColumn( grids.TextColumn ):

        def get_value( self, trans, grid, repository_metadata ):
            repository = repository_metadata.repository
            return escape_html( repository.name )


    class RepositoryOwnerColumn( grids.TextColumn ):

        def get_value( self, trans, grid, repository_metadata ):
            repository = repository_metadata.repository
            return escape_html( repository.user.username )


    class ChangesetRevisionColumn( grids.TextColumn ):

        def get_value( self, trans, grid, repository_metadata ):
            repository = repository_metadata.repository
            changeset_revision = repository_metadata.changeset_revision
            changeset_revision_label = suc.get_revision_label( trans, repository, changeset_revision )
            return escape_html( changeset_revision_label )


    class MaliciousColumn( grids.BooleanColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            if repository_metadata.malicious:
                return 'yes'
            return ''


    class DownloadableColumn( grids.BooleanColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            if repository_metadata.downloadable:
                return 'yes'
            return ''


    class ToolsFunctionallyCorrectColumn( grids.BooleanColumn ):

        def get_value( self, trans, grid, repository ):
            # This column will display the value associated with the currently displayed metadata revision.
            try:
                displayed_metadata_revision = repository.metadata_revisions[ -1 ]
                if displayed_metadata_revision.includes_tools:
                    if displayed_metadata_revision.tools_functionally_correct:
                        return 'yes'
                    else:
                        return 'no'
                return 'n/a'
            except:
                return 'n/a'


    class DoNotTestColumn( grids.BooleanColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            if repository_metadata.do_not_test:
                return 'yes'
            return ''


    class TimeLastTestedColumn( grids.DateTimeColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            return repository_metadata.time_last_tested


    class HasRepositoryDependenciesColumn( grids.BooleanColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            if repository_metadata.has_repository_dependencies:
                return 'yes'
            return ''


    class IncludesDatatypesColumn( grids.BooleanColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            if repository_metadata.includes_datatypes:
                return 'yes'
            return ''


    class IncludesToolsColumn( grids.BooleanColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            if repository_metadata.includes_tools:
                return 'yes'
            return ''


    class IncludesToolDependenciesColumn( grids.BooleanColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            if repository_metadata.includes_tool_dependencies:
                return 'yes'
            return ''


    class IncludesWorkflowsColumn( grids.BooleanColumn ):
        def get_value( self, trans, grid, repository_metadata ):
            if repository_metadata.includes_workflows:
                return 'yes'
            return ''

    title = "Repository metadata"
    model_class = model.RepositoryMetadata
    template='/webapps/tool_shed/repository/grid.mako'
    default_sort_key = "Repository.name"
    columns = [
        RepositoryNameColumn( "Repository name",
                              key="Repository.name",
                              link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                              attach_popup=False ),
        RepositoryOwnerColumn( "Owner",
                               model_class=model.User,
                               attach_popup=False,
                               key="User.username" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name, description", 
                                                cols_to_filter=[ columns[0], columns[1] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = []
    standard_filters = []
    default_filter = dict( malicious="False" )
    num_rows_per_page = 50
    preserve_state = False
    use_paging = False

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( model.RepositoryMetadata ) \
                               .join( model.Repository ) \
                               .filter( and_( model.Repository.table.c.deleted == False,
                                              model.Repository.table.c.deprecated == False ) ) \
                               .join( model.User.table )


class RepositoryDependenciesGrid( RepositoryMetadataGrid ):


    class RequiredRepositoryColumn( grids.TextColumn ):

        def get_value( self, trans, grid, repository_metadata ):
            rd_str = ''
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    rd_dict = metadata.get( 'repository_dependencies', {} )
                    if rd_dict:
                        rd_tups = rd_dict[ 'repository_dependencies' ]
                        # "repository_dependencies": [["http://localhost:9009", "bwa059", "test", "a07baa797d53"]]
                        # Sort rd_tups by by required repository name.
                        sorted_rd_tups = sorted( rd_tups, key=lambda rd_tup: rd_tup[ 1 ] )
                        num_tups = len( sorted_rd_tups )
                        for index, rd_tup in enumerate( sorted_rd_tups ):
                            name = rd_tup[ 1 ]
                            owner = rd_tup[ 2 ]
                            changeset_revision = rd_tup[ 3 ]
                            required_repository = suc.get_repository_by_name_and_owner( trans.app, name, owner )
                            if required_repository:
                                required_repository_id = trans.security.encode_id( required_repository.id )
                                required_repository_metadata = metadata_util.get_repository_metadata_by_repository_id_changeset_revision( trans,
                                                                                                                                          required_repository_id,
                                                                                                                                          changeset_revision )
                                if not required_repository_metadata:
                                    repo_dir = required_repository.repo_path( trans.app )
                                    repo = hg.repository( suc.get_configured_ui(), repo_dir )
                                    updated_changeset_revision = suc.get_next_downloadable_changeset_revision( required_repository, repo, changeset_revision )
                                    required_repository_metadata = metadata_util.get_repository_metadata_by_repository_id_changeset_revision( trans,
                                                                                                                                              required_repository_id,
                                                                                                                                              updated_changeset_revision )
                                required_repository_metadata_id = trans.security.encode_id( required_repository_metadata.id )
                                rd_str += '<a href="browse_repository_dependencies?operation=view_or_manage_repository&id=%s">' % ( required_repository_metadata_id )
                            rd_str += 'Repository <b>%s</b> revision <b>%s</b> owned by <b>%s</b>' % ( escape_html( rd_tup[ 1 ] ), escape_html( rd_tup[ 3 ] ), escape_html( rd_tup[ 2 ] ) )
                            if required_repository:
                                rd_str += '</a>'
                            if index < num_tups - 1:
                                rd_str += '<br/>'
            return rd_str

    title = "Valid repository dependency definitions in this tool shed"
    default_sort_key = "Repository.name"
    columns = [
        RequiredRepositoryColumn( "Repository dependency",
                                   attach_popup=False ),
        RepositoryMetadataGrid.RepositoryNameColumn( "Repository name",
                                                     model_class=model.Repository,
                                                     link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                                     attach_popup=False,
                                                     key="Repository.name" ),
        RepositoryMetadataGrid.RepositoryOwnerColumn( "Owner",
                                                      model_class=model.User,
                                                      attach_popup=False,
                                                      key="User.username" ),
        RepositoryMetadataGrid.ChangesetRevisionColumn( "Revision",
                                                        attach_popup=False )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name, owner", 
                                                cols_to_filter=[ columns[1], columns[2] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( model.RepositoryMetadata ) \
                               .join( model.Repository ) \
                               .filter( and_( model.RepositoryMetadata.table.c.has_repository_dependencies == True,
                                              model.Repository.table.c.deleted == False,
                                              model.Repository.table.c.deprecated == False ) ) \
                               .join( model.User.table )


class DatatypesGrid( RepositoryMetadataGrid ):


    class DatatypesColumn( grids.TextColumn ):

        def get_value( self, trans, grid, repository_metadata ):
            datatype_str = ''
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    datatype_dicts = metadata.get( 'datatypes', [] )
                    if datatype_dicts:
                        # Create tuples of the attributes we want so we can sort them by extension.
                        datatype_tups = []
                        for datatype_dict in datatype_dicts:
                            # Example: {"display_in_upload": "true", "dtype": "galaxy.datatypes.blast:BlastXml", "extension": "blastxml", "mimetype": "application/xml"}
                            extension = datatype_dict.get( 'extension', '' )
                            dtype = datatype_dict.get( 'dtype', '' )
                            mimetype = datatype_dict.get( 'mimetype', '' )
                            display_in_upload = datatype_dict.get( 'display_in_upload', False )
                            # For now we'll just display extension and dtype.
                            if extension and dtype:
                                datatype_tups.append( ( extension, dtype ) )
                        sorted_datatype_tups = sorted( datatype_tups, key=lambda datatype_tup: datatype_tup[ 0 ] )
                        num_datatype_tups = len( sorted_datatype_tups )
                        for index, datatype_tup in enumerate( sorted_datatype_tups ):
                            extension = datatype_tup[ 0 ]
                            dtype = datatype_tup[ 1 ]
                            datatype_str += '<a href="browse_datatypes?operation=view_or_manage_repository&id=%s">' % trans.security.encode_id( repository_metadata.id )
                            datatype_str += '<b>%s:</b> %s' % ( escape_html( extension ), escape_html( dtype ) )
                            datatype_str += '</a>'
                            if index < num_datatype_tups - 1:
                                datatype_str += '<br/>'
            return datatype_str

    title = "Custom datatypes in this tool shed"
    default_sort_key = "Repository.name"
    columns = [
        DatatypesColumn( "Datatype extension and class",
                         attach_popup=False ),
        RepositoryMetadataGrid.RepositoryNameColumn( "Repository name",
                                                     model_class=model.Repository,
                                                     link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                                     attach_popup=False,
                                                     key="Repository.name" ),
        RepositoryMetadataGrid.RepositoryOwnerColumn( "Owner",
                                                      model_class=model.User,
                                                      attach_popup=False,
                                                      key="User.username" ),
        RepositoryMetadataGrid.ChangesetRevisionColumn( "Revision",
                                                        attach_popup=False )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name, owner", 
                                                cols_to_filter=[ columns[1], columns[2] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( model.RepositoryMetadata ) \
                               .join( model.Repository ) \
                               .filter( and_( model.RepositoryMetadata.table.c.includes_datatypes == True,
                                              model.Repository.table.c.deleted == False,
                                              model.Repository.table.c.deprecated == False ) ) \
                               .join( model.User.table )


class ToolDependenciesGrid( RepositoryMetadataGrid ):


    class ToolDependencyColumn( grids.TextColumn ):

        def get_value( self, trans, grid, repository_metadata ):
            td_str = ''
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    tds_dict = metadata.get( 'tool_dependencies', {} )
                    if tds_dict:
                        # Example: {"bwa/0.5.9": {"name": "bwa", "type": "package", "version": "0.5.9"}}
                        sorted_keys = sorted( [ k for k in tds_dict.keys() ] )
                        num_keys = len( sorted_keys )
                        # Handle environment settings first.
                        if 'set_environment' in sorted_keys:
                            # Example: "set_environment": [{"name": "JAVA_JAR_FILE", "type": "set_environment"}]
                            env_dicts = tds_dict[ 'set_environment' ]
                            num_env_dicts = len( env_dicts )
                            if num_env_dicts > 0:
                                td_str += '<a href="browse_datatypes?operation=view_or_manage_repository&id=%s">' % trans.security.encode_id( repository_metadata.id )
                                td_str += '<b>environment:</b> '
                                for index, env_dict in enumerate( env_dicts ):
                                    td_str += '%s' % escape_html( env_dict[ 'name' ] )
                                    if index < num_env_dicts - 1:
                                        td_str += ', '
                                td_str += '</a><br/>'
                        for index, key in enumerate( sorted_keys ):
                            if key == 'set_environment':
                                continue
                            td_dict = tds_dict[ key ]
                            # Example: {"name": "bwa", "type": "package", "version": "0.5.9"}
                            name = td_dict[ 'name' ]
                            type = td_dict[ 'type' ]
                            version = td_dict[ 'version' ]
                            td_str += '<a href="browse_datatypes?operation=view_or_manage_repository&id=%s">' % trans.security.encode_id( repository_metadata.id )
                            td_str += '<b>%s</b> version <b>%s</b>' % ( escape_html( name ), escape_html( version ) )
                            td_str += '</a>'
                            if index < num_keys - 1:
                                td_str += '<br/>'
            return td_str

    title = "Tool dependency definitions in this tool shed"
    default_sort_key = "Repository.name"
    columns = [
        ToolDependencyColumn( "Tool dependency",
                              attach_popup=False ),
        RepositoryMetadataGrid.RepositoryNameColumn( "Repository name",
                                                     model_class=model.Repository,
                                                     link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                                     attach_popup=False,
                                                     key="Repository.name" ),
        RepositoryMetadataGrid.RepositoryOwnerColumn( "Owner",
                                                      model_class=model.User,
                                                      attach_popup=False,
                                                      key="User.username" ),
        RepositoryMetadataGrid.ChangesetRevisionColumn( "Revision",
                                                        attach_popup=False )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name, owner", 
                                                cols_to_filter=[ columns[1], columns[2] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( model.RepositoryMetadata ) \
                               .join( model.Repository ) \
                               .filter( and_( model.RepositoryMetadata.table.c.includes_tool_dependencies == True,
                                              model.Repository.table.c.deleted == False,
                                              model.Repository.table.c.deprecated == False ) ) \
                               .join( model.User.table )


class ToolsGrid( RepositoryMetadataGrid ):


    class ToolsColumn( grids.TextColumn ):

        def get_value( self, trans, grid, repository_metadata ):
            tool_str = ''
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    tool_dicts = metadata.get( 'tools', [] )
                    if tool_dicts:
                        # Create tuples of the attributes we want so we can sort them by extension.
                        tool_tups = []
                        for tool_dict in tool_dicts:
                            tool_id = tool_dict.get( 'id', '' )
                            version = tool_dict.get( 'version', '' )
                            # For now we'll just display tool id and version.
                            if tool_id and version:
                                tool_tups.append( ( tool_id, version ) )
                        sorted_tool_tups = sorted( tool_tups, key=lambda tool_tup: tool_tup[ 0 ] )
                        num_tool_tups = len( sorted_tool_tups )
                        for index, tool_tup in enumerate( sorted_tool_tups ):
                            tool_id = tool_tup[ 0 ]
                            version = tool_tup[ 1 ]
                            tool_str += '<a href="browse_datatypes?operation=view_or_manage_repository&id=%s">' % trans.security.encode_id( repository_metadata.id )
                            tool_str += '<b>%s:</b> %s' % ( escape_html( tool_id ), escape_html( version ) )
                            tool_str += '</a>'
                            if index < num_tool_tups - 1:
                                tool_str += '<br/>'
            return tool_str

    title = "Valid tools in this tool shed"
    default_sort_key = "Repository.name"
    columns = [
        ToolsColumn( "Tool id and version",
                      attach_popup=False ),
        RepositoryMetadataGrid.RepositoryNameColumn( "Repository name",
                                                     model_class=model.Repository,
                                                     link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                                     attach_popup=False,
                                                     key="Repository.name" ),
        RepositoryMetadataGrid.RepositoryOwnerColumn( "Owner",
                                                      model_class=model.User,
                                                      attach_popup=False,
                                                      key="User.username" ),
        RepositoryMetadataGrid.ChangesetRevisionColumn( "Revision",
                                                        attach_popup=False )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name, owner", 
                                                cols_to_filter=[ columns[1], columns[2] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( model.RepositoryMetadata ) \
                               .join( model.Repository ) \
                               .filter( and_( model.RepositoryMetadata.table.c.includes_tools == True,
                                              model.Repository.table.c.deleted == False,
                                              model.Repository.table.c.deprecated == False ) ) \
                               .join( model.User.table )


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
    use_paging = False


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


    class InstallableRevisionColumn( grids.GridColumn ):

        def __init__( self, col_name ):
            grids.GridColumn.__init__( self, col_name )

        def get_value( self, trans, grid, repository ):
            """Display a SelectField whose options are the changeset_revision strings of all download-able revisions of this repository."""
            select_field = grids_util.build_changeset_revision_select_field( trans, repository, downloadable=True )
            if len( select_field.options ) > 1:
                return select_field.get_html()
            elif len( select_field.options ) == 1:
                return select_field.options[ 0 ][ 0 ]
            return ''

    title = "Valid repositories"
    columns = [
        RepositoryGrid.NameColumn( "Name",
                                   key="name",
                                   attach_popup=False ),
        RepositoryGrid.DescriptionColumn( "Synopsis",
                                          key="description",
                                          attach_popup=False ),
        InstallableRevisionColumn( "Installable Revisions" ),
        RepositoryGrid.ToolsFunctionallyCorrectColumn( "Tools Verified" ),
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
    use_paging = False

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

# ------ utility methods -------------------

def filter_by_latest_downloadable_changeset_revision_that_has_failing_tool_tests( trans, repository ):
    """
    Inspect the latest installable changeset revision for the received repository to see if it includes at least 1 tool that has at least 1 failing test.
    """
    encoded_repository_id = trans.security.encode_id( repository.id )
    repo = hg.repository( suc.get_configured_ui(), repository.repo_path( trans.app ) )
    tip_ctx = str( repo.changectx( repo.changelog.tip() ) )
    repository_metadata = get_latest_installable_repository_metadata_if_it_includes_tools( trans, repository )
    if repository_metadata and not repository_metadata.missing_test_components and not repository_metadata.tools_functionally_correct:
        return repository_metadata.changeset_revision
    return None

def filter_by_latest_downloadable_changeset_revision_that_has_missing_tool_test_components( trans, repository ):
    """
    Inspect the latest installable changeset revision for the received repository to see if it includes tools that are either missing functional tests
    or functional test data.  If the changset revision includes tools, but is missing tool test components, return the changeset revision hash.
    """
    encoded_repository_id = trans.security.encode_id( repository.id )
    repo = hg.repository( suc.get_configured_ui(), repository.repo_path( trans.app ) )
    tip_ctx = str( repo.changectx( repo.changelog.tip() ) )
    repository_metadata = get_latest_installable_repository_metadata_if_it_includes_tools( trans, repository )
    if repository_metadata and repository_metadata.missing_test_components:
        return repository_metadata.changeset_revision
    return None

def filter_by_latest_downloadable_changeset_revision_that_has_no_failing_tool_tests( trans, repository ):
    """
    Inspect the latest installable changeset revision for the received repository to see if it includes tools with no failing tests.
    """
    encoded_repository_id = trans.security.encode_id( repository.id )
    repo = hg.repository( suc.get_configured_ui(), repository.repo_path( trans.app ) )
    tip_ctx = str( repo.changectx( repo.changelog.tip() ) )
    repository_metadata = get_latest_installable_repository_metadata_if_it_includes_tools( trans, repository )
    if repository_metadata and not repository_metadata.missing_test_components and repository_metadata.tools_functionally_correct:
        return repository_metadata.changeset_revision
    return None

def filter_by_latest_metadata_changeset_revision_that_has_invalid_tools( trans, repository ):
    """
    Inspect the latest changeset revision with associated metadata for the received repository to see if it has invalid tools.
    """
    encoded_repository_id = trans.security.encode_id( repository.id )
    repo = hg.repository( suc.get_configured_ui(), repository.repo_path( trans.app ) )
    tip_ctx = str( repo.changectx( repo.changelog.tip() ) )
    repository_metadata = get_latest_repository_metadata_if_it_includes_invalid_tools( trans, repository )
    if repository_metadata:
        return repository_metadata.changeset_revision
    return None

def get_latest_repository_metadata_if_it_includes_invalid_tools( trans, repository ):
    """Return the latest repository_metadata record for the received repository that contains invalid tools if one exists."""
    encoded_repository_id = trans.security.encode_id( repository.id )
    repo = hg.repository( suc.get_configured_ui(), repository.repo_path( trans.app ) )
    tip_ctx = str( repo.changectx( repo.changelog.tip() ) )
    repository_metadata = None
    try:
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, encoded_repository_id, tip_ctx )
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata and 'invalid_tools' in metadata:
                return repository_metadata
            return None
        return None
    except:
        latest_installable_revision = suc.get_previous_metadata_changeset_revision( repository, repo, tip_ctx, downloadable=False )
        if latest_installable_revision == suc.INITIAL_CHANGELOG_HASH:
            return None
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, encoded_repository_id, latest_installable_revision )
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata and 'invalid_tools' in metadata:
                return repository_metadata
            return None
        return None

def get_latest_installable_repository_metadata_if_it_includes_tools( trans, repository ):
    """Return the latest installable repository_metadata record for the received repository that contains valid tools if one exists."""
    encoded_repository_id = trans.security.encode_id( repository.id )
    repo = hg.repository( suc.get_configured_ui(), repository.repo_path( trans.app ) )
    tip_ctx = str( repo.changectx( repo.changelog.tip() ) )
    repository_metadata = None
    try:
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, encoded_repository_id, tip_ctx )
        if repository_metadata and repository_metadata.includes_tools and repository_metadata.downloadable:
            return repository_metadata
        return None
    except:
        latest_installable_revision = suc.get_previous_metadata_changeset_revision( repository, repo, tip_ctx, downloadable=True )
        if latest_installable_revision == suc.INITIAL_CHANGELOG_HASH:
            return None
        repository_metadata = suc.get_repository_metadata_by_changeset_revision( trans, encoded_repository_id, latest_installable_revision )
        if repository_metadata and repository_metadata.includes_tools and repository_metadata.downloadable:
            return repository_metadata
        return None
