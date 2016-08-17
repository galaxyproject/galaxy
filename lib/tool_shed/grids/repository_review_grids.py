import logging

from markupsafe import escape
from sqlalchemy import and_, false, null, or_, true

from galaxy.web.framework.helpers import grids
from galaxy.webapps.tool_shed import model
from tool_shed.grids.repository_grids import RepositoryGrid
from tool_shed.util import hg_util, metadata_util

log = logging.getLogger( __name__ )


class ComponentGrid( grids.Grid ):

    class NameColumn( grids.TextColumn ):

        def get_value( self, trans, grid, component ):
            return escape( component.name )

    class DescriptionColumn( grids.TextColumn ):

        def get_value( self, trans, grid, component ):
            return escape( component.description )

    title = "Repository review components"
    model_class = model.Component
    template = '/webapps/tool_shed/repository_review/grid.mako'
    default_sort_key = "name"
    use_hide_message = False
    columns = [
        NameColumn( "Name",
                    key="Component.name",
                    link=( lambda item: dict( operation="edit", id=item.id ) ),
                    attach_popup=False ),
        DescriptionColumn( "Description",
                           key="Component.description",
                           attach_popup=False )
    ]
    default_filter = {}
    global_actions = [
        grids.GridAction( "Add new component",
                          dict( controller='repository_review', action='manage_components', operation='create' ) )
    ]
    operations = []
    standard_filters = []
    num_rows_per_page = 50
    preserve_state = False
    use_paging = False


class RepositoriesWithReviewsGrid( RepositoryGrid ):
    # This grid filters out repositories that have been marked as either deprecated or deleted.

    class WithReviewsRevisionColumn( grids.GridColumn ):
        def get_value( self, trans, grid, repository ):
            # Restrict to revisions that have been reviewed.
            if repository.reviews:
                rval = ''
                repo = hg_util.get_repo_for_repository( trans.app, repository=repository, repo_path=None, create=False )
                for review in repository.reviews:
                    changeset_revision = review.changeset_revision
                    rev, label = hg_util.get_rev_label_from_changeset_revision( repo, changeset_revision )
                    rval += '<a href="manage_repository_reviews_of_revision?id=%s&changeset_revision=%s">%s</a><br/>' % \
                        ( trans.security.encode_id( repository.id ), changeset_revision, label )
                return rval
            return ''

    class WithoutReviewsRevisionColumn( grids.GridColumn ):

        def get_value( self, trans, grid, repository ):
            # Restrict the options to revisions that have not yet been reviewed.
            repository_metadata_revisions = metadata_util.get_repository_metadata_revisions_for_review( repository, reviewed=False )
            if repository_metadata_revisions:
                rval = ''
                for repository_metadata in repository_metadata_revisions:
                    rev, label, changeset_revision = \
                        hg_util.get_rev_label_changeset_revision_from_repository_metadata( trans.app,
                                                                                           repository_metadata,
                                                                                           repository=repository,
                                                                                           include_date=True,
                                                                                           include_hash=False )
                    rval += '<a href="manage_repository_reviews_of_revision?id=%s&changeset_revision=%s">%s</a><br/>' % \
                        ( trans.security.encode_id( repository.id ), changeset_revision, label )
                return rval
            return ''

    class ReviewersColumn( grids.TextColumn ):

        def get_value( self, trans, grid, repository ):
            rval = ''
            if repository.reviewers:
                for user in repository.reviewers:
                    rval += '<a class="view-info" href="repository_reviews_by_user?id=%s">' % trans.security.encode_id( user.id )
                    rval += '%s</a> | ' % user.username
                rval = rval.rstrip( ' | ' )
            return rval

    class RatingColumn( grids.TextColumn ):

        def get_value( self, trans, grid, repository ):
            rval = ''
            for review in repository.reviews:
                if review.rating:
                    for index in range( 1, 6 ):
                        rval += '<input '
                        rval += 'name="star1-%s" ' % trans.security.encode_id( review.id )
                        rval += 'type="radio" '
                        rval += 'class="community_rating_star star" '
                        rval += 'disabled="disabled" '
                        rval += 'value="%s" ' % str( review.rating )
                        if review.rating > ( index - 0.5 ) and review.rating < ( index + 0.5 ):
                            rval += 'checked="checked" '
                        rval += '/>'
                rval += '<br/>'
            return rval

    class ApprovedColumn( grids.TextColumn ):

        def get_value( self, trans, grid, repository ):
            rval = ''
            for review in repository.reviews:
                if review.approved:
                    rval += '%s<br/>' % review.approved
            return rval

    title = "All reviewed repositories"
    model_class = model.Repository
    template = '/webapps/tool_shed/repository_review/grid.mako'
    default_sort_key = "Repository.name"
    columns = [
        RepositoryGrid.NameColumn( "Repository name",
                                   key="name",
                                   link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                   attach_popup=True ),
        RepositoryGrid.UserColumn( "Owner",
                                   model_class=model.User,
                                   attach_popup=False,
                                   key="User.username" ),
        WithReviewsRevisionColumn( "Reviewed revisions" ),
        ReviewersColumn( "Reviewers", attach_popup=False ),
        RatingColumn( "Rating", attach_popup=False ),
        ApprovedColumn( "Approved", attach_popup=False )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name",
                                                cols_to_filter=[ columns[ 0 ] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [
        grids.GridOperation( "Inspect repository revisions",
                             allow_multiple=False,
                             condition=( lambda item: not item.deleted ),
                             async_compatible=False )
    ]

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( model.Repository ) \
                               .filter( and_( model.Repository.table.c.deleted == false(),
                                              model.Repository.table.c.deprecated == false() ) ) \
                               .join( ( model.RepositoryReview.table, model.RepositoryReview.table.c.repository_id == model.Repository.table.c.id ) ) \
                               .join( ( model.User.table, model.User.table.c.id == model.Repository.table.c.user_id ) ) \
                               .outerjoin( ( model.ComponentReview.table, model.ComponentReview.table.c.repository_review_id == model.RepositoryReview.table.c.id ) ) \
                               .outerjoin( ( model.Component.table, model.Component.table.c.id == model.ComponentReview.table.c.component_id ) )


class RepositoriesWithoutReviewsGrid( RepositoriesWithReviewsGrid ):
    # This grid filters out repositories that have been marked as either deprecated or deleted.
    title = "Repositories with no reviews"
    columns = [
        RepositoriesWithReviewsGrid.NameColumn( "Repository name",
                                                key="name",
                                                link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                                attach_popup=True ),
        RepositoriesWithReviewsGrid.DescriptionColumn( "Synopsis",
                                                       key="description",
                                                       attach_popup=False ),
        RepositoriesWithReviewsGrid.WithoutReviewsRevisionColumn( "Revisions for review" ),
        RepositoriesWithReviewsGrid.UserColumn( "Owner",
                                                model_class=model.User,
                                                attach_popup=False,
                                                key="User.username" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name, description",
                                                cols_to_filter=[ columns[ 0 ], columns[ 1 ] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [ grids.GridOperation( "Inspect repository revisions",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted ),
                                        async_compatible=False ) ]

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( model.Repository ) \
                               .filter( and_( model.Repository.table.c.deleted == false(),
                                              model.Repository.table.c.deprecated == false(),
                                              model.Repository.reviews == null() ) ) \
                               .join( model.User.table )


class RepositoriesReadyForReviewGrid( RepositoriesWithoutReviewsGrid ):
    # Repositories that are ready for human review are those that either:
    # 1) Have no tools
    # 2) Have tools that have been proven to be functionally correct within Galaxy.
    # This grid filters out repositories that have been marked as either deprecated or deleted.
    title = "Repositories ready for review"
    columns = [
        RepositoriesWithoutReviewsGrid.NameColumn( "Repository name",
                                                   key="name",
                                                   link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                                   attach_popup=True ),
        RepositoriesWithoutReviewsGrid.DescriptionColumn( "Synopsis",
                                                          key="description",
                                                          attach_popup=False ),
        RepositoriesWithoutReviewsGrid.WithoutReviewsRevisionColumn( "Revisions for review" ),
        RepositoriesWithoutReviewsGrid.UserColumn( "Owner",
                                                   model_class=model.User,
                                                   attach_popup=False,
                                                   key="User.username" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name, description",
                                                cols_to_filter=[ columns[ 0 ], columns[ 1 ] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [ grids.GridOperation( "Inspect repository revisions",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted ),
                                        async_compatible=False ) ]

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( model.Repository ) \
                               .filter( and_( model.Repository.table.c.deleted == false(),
                                              model.Repository.table.c.deprecated == false(),
                                              model.Repository.reviews == null() ) ) \
                               .join( model.RepositoryMetadata.table ) \
                               .filter( and_( model.RepositoryMetadata.table.c.downloadable == true(),
                                              or_( model.RepositoryMetadata.table.c.includes_tools == false(),
                                                   and_( model.RepositoryMetadata.table.c.includes_tools == true(),
                                                         model.RepositoryMetadata.table.c.tools_functionally_correct == true() ) ) ) ) \
                               .join( model.User.table )


class RepositoriesReviewedByMeGrid( RepositoriesWithReviewsGrid ):
    # This grid filters out repositories that have been marked as either deprecated or deleted.

    columns = [
        RepositoriesWithReviewsGrid.NameColumn( "Repository name",
                                                key="name",
                                                link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                                attach_popup=True ),
        RepositoriesWithReviewsGrid.UserColumn( "Owner", attach_popup=False ),
        RepositoriesWithReviewsGrid.WithReviewsRevisionColumn( "Reviewed revisions" ),
        RepositoriesWithReviewsGrid.ReviewersColumn( "Reviewers", attach_popup=False ),
        RepositoriesWithReviewsGrid.RatingColumn( "Rating", attach_popup=False ),
        RepositoriesWithReviewsGrid.ApprovedColumn( "Approved", attach_popup=False )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name",
                                                cols_to_filter=[ columns[ 0 ] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( model.Repository ) \
                               .filter( and_( model.Repository.table.c.deleted == false(),
                                              model.Repository.table.c.deprecated == false() ) ) \
                               .join( ( model.RepositoryReview.table, model.RepositoryReview.table.c.repository_id == model.Repository.table.c.id ) ) \
                               .filter( model.RepositoryReview.table.c.user_id == trans.user.id ) \
                               .join( ( model.User.table, model.User.table.c.id == model.RepositoryReview.table.c.user_id ) ) \
                               .outerjoin( ( model.ComponentReview.table, model.ComponentReview.table.c.repository_review_id == model.RepositoryReview.table.c.id ) ) \
                               .outerjoin( ( model.Component.table, model.Component.table.c.id == model.ComponentReview.table.c.component_id ) )


class RepositoryReviewsByUserGrid( grids.Grid ):
    # This grid filters out repositories that have been marked as deprecated.

    class RepositoryNameColumn( grids.TextColumn ):

        def get_value( self, trans, grid, review ):
            return escape( review.repository.name )

    class RepositoryDescriptionColumn( grids.TextColumn ):

        def get_value( self, trans, grid, review ):
            return escape( review.repository.description )

    class RevisionColumn( grids.TextColumn ):

        def get_value( self, trans, grid, review ):
            encoded_review_id = trans.security.encode_id( review.id )
            rval = '<a class="action-button" href="'
            if review.user == trans.user:
                rval += 'edit_review'
            else:
                rval += 'browse_review'
            revision_label = hg_util.get_revision_label( trans.app,
                                                         review.repository,
                                                         review.changeset_revision,
                                                         include_date=True,
                                                         include_hash=False )
            rval += '?id=%s">%s</a>' % ( encoded_review_id, revision_label )
            return rval

    class RatingColumn( grids.TextColumn ):

        def get_value( self, trans, grid, review ):
            if review.rating:
                for index in range( 1, 6 ):
                    rval = '<input '
                    rval += 'name="star1-%s" ' % trans.security.encode_id( review.id )
                    rval += 'type="radio" '
                    rval += 'class="community_rating_star star" '
                    rval += 'disabled="disabled" '
                    rval += 'value="%s" ' % str( review.rating )
                    if review.rating > ( index - 0.5 ) and review.rating < ( index + 0.5 ):
                        rval += 'checked="checked" '
                    rval += '/>'
                return rval
            return ''

    title = "Reviews by user"
    model_class = model.RepositoryReview
    template = '/webapps/tool_shed/repository_review/grid.mako'
    default_sort_key = 'repository_id'
    use_hide_message = False
    columns = [
        RepositoryNameColumn( "Repository Name",
                              model_class=model.Repository,
                              key="Repository.name",
                              link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                              attach_popup=True ),
        RepositoryDescriptionColumn( "Description",
                                     model_class=model.Repository,
                                     key="Repository.description",
                                     attach_popup=False ),
        RevisionColumn( "Revision", attach_popup=False ),
        RatingColumn( "Rating", attach_popup=False ),
    ]
    # Override these
    default_filter = {}
    global_actions = []
    operations = [
        grids.GridOperation( "Inspect repository revisions",
                             allow_multiple=False,
                             condition=( lambda item: not item.deleted ),
                             async_compatible=False )
    ]
    standard_filters = []
    num_rows_per_page = 50
    preserve_state = False
    use_paging = False

    def build_initial_query( self, trans, **kwd ):
        user_id = trans.security.decode_id( kwd[ 'id' ] )
        return trans.sa_session.query( model.RepositoryReview ) \
                               .filter( and_( model.RepositoryReview.table.c.deleted == false(),
                                              model.RepositoryReview.table.c.user_id == user_id ) ) \
                               .join( ( model.Repository.table, model.RepositoryReview.table.c.repository_id == model.Repository.table.c.id ) ) \
                               .filter( model.Repository.table.c.deprecated == false() )


class ReviewedRepositoriesIOwnGrid( RepositoriesWithReviewsGrid ):
    title = "Reviewed repositories I own"
    columns = [
        RepositoriesWithReviewsGrid.NameColumn( "Repository name",
                                                key="name",
                                                link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                                attach_popup=True ),
        RepositoriesWithReviewsGrid.WithReviewsRevisionColumn( "Reviewed revisions" ),
        RepositoriesWithReviewsGrid.WithoutReviewsRevisionColumn( "Revisions for review" ),
        RepositoriesWithReviewsGrid.ReviewersColumn( "Reviewers", attach_popup=False ),
        RepositoryGrid.DeprecatedColumn( "Deprecated" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name",
                                                cols_to_filter=[ columns[0] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [
        grids.GridOperation( "Inspect repository revisions",
                             allow_multiple=False,
                             condition=( lambda item: not item.deleted ),
                             async_compatible=False )
    ]

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( model.Repository ) \
                               .join( ( model.RepositoryReview.table, model.RepositoryReview.table.c.repository_id == model.Repository.table.c.id ) ) \
                               .filter( model.Repository.table.c.user_id == trans.user.id ) \
                               .join( ( model.User.table, model.User.table.c.id == model.RepositoryReview.table.c.user_id ) ) \
                               .outerjoin( ( model.ComponentReview.table, model.ComponentReview.table.c.repository_review_id == model.RepositoryReview.table.c.id ) ) \
                               .outerjoin( ( model.Component.table, model.Component.table.c.id == model.ComponentReview.table.c.component_id ) )


class RepositoriesWithNoToolTestsGrid( RepositoriesWithoutReviewsGrid ):
    # Repositories that are ready for human review are those that either:
    # 1) Have no tools
    # 2) Have tools that have been proven to be functionally correct within Galaxy.
    # This grid filters out repositories that have been marked as either deprecated or deleted.
    title = "Repositories that contain tools with no tests or test data"
    columns = [
        RepositoriesWithoutReviewsGrid.NameColumn( "Repository name",
                                                   key="name",
                                                   link=( lambda item: dict( operation="view_or_manage_repository", id=item.id ) ),
                                                   attach_popup=True ),
        RepositoriesWithoutReviewsGrid.DescriptionColumn( "Synopsis",
                                                          key="description",
                                                          attach_popup=False ),
        RepositoriesWithoutReviewsGrid.WithoutReviewsRevisionColumn( "Revisions for review" ),
        RepositoriesWithoutReviewsGrid.UserColumn( "Owner",
                                                   model_class=model.User,
                                                   attach_popup=False,
                                                   key="User.username" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name, description",
                                                cols_to_filter=[ columns[ 0 ], columns[ 1 ] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    operations = [ grids.GridOperation( "Inspect repository revisions",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted ),
                                        async_compatible=False ) ]

    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( model.Repository ) \
                               .filter( and_( model.Repository.table.c.deleted == false(),
                                              model.Repository.table.c.deprecated == false() ) ) \
                               .join( model.RepositoryMetadata.table ) \
                               .filter( and_( model.RepositoryMetadata.table.c.downloadable == true(),
                                              model.RepositoryMetadata.table.c.includes_tools == true(),
                                              model.RepositoryMetadata.table.c.tools_functionally_correct == false() ) ) \
                               .join( model.User.table )
