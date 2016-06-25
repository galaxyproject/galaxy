import logging

from sqlalchemy import and_, func, false

import tool_shed.grids.repository_review_grids as repository_review_grids
import tool_shed.grids.util as grids_util
from galaxy import util
from galaxy import web
from galaxy.util.odict import odict
from galaxy.web.base.controller import BaseUIController
from galaxy.web.form_builder import CheckboxField
from galaxy.webapps.tool_shed.util import ratings_util
from tool_shed.util import hg_util
from tool_shed.util import review_util
from tool_shed.util import metadata_util
from tool_shed.util import repository_util
from tool_shed.util import shed_util_common as suc
from tool_shed.util.container_util import STRSEP
from tool_shed.util.web_util import escape

log = logging.getLogger( __name__ )


class RepositoryReviewController( BaseUIController, ratings_util.ItemRatings ):

    component_grid = repository_review_grids.ComponentGrid()
    repositories_ready_for_review_grid = repository_review_grids.RepositoriesReadyForReviewGrid()
    repositories_reviewed_by_me_grid = repository_review_grids.RepositoriesReviewedByMeGrid()
    repositories_with_reviews_grid = repository_review_grids.RepositoriesWithReviewsGrid()
    repositories_without_reviews_grid = repository_review_grids.RepositoriesWithoutReviewsGrid()
    repository_reviews_by_user_grid = repository_review_grids.RepositoryReviewsByUserGrid()
    reviewed_repositories_i_own_grid = repository_review_grids.ReviewedRepositoriesIOwnGrid()
    repositories_with_no_tool_tests_grid = repository_review_grids.RepositoriesWithNoToolTestsGrid()

    @web.expose
    @web.require_login( "approve repository review" )
    def approve_repository_review( self, trans, **kwd ):
        # The value of the received id is the encoded review id.
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        encoded_review_id = kwd[ 'id' ]
        review = review_util.get_review( trans.app, encoded_review_id )
        if kwd.get( 'approve_repository_review_button', False ):
            approved_select_field_name = '%s%sapproved' % ( encoded_review_id, STRSEP )
            approved_select_field_value = str( kwd[ approved_select_field_name ] )
            review.approved = approved_select_field_value
            trans.sa_session.add( review )
            trans.sa_session.flush()
            message = 'Approved value <b>%s</b> saved for this revision.' % escape( approved_select_field_value )
        repository_id = trans.security.encode_id( review.repository_id )
        changeset_revision = review.changeset_revision
        return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                          action='manage_repository_reviews_of_revision',
                                                          id=repository_id,
                                                          changeset_revision=changeset_revision,
                                                          message=message,
                                                          status=status ) )

    @web.expose
    @web.require_login( "browse components" )
    def browse_components( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd[ 'operation' ].lower()
            if operation == "create":
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='create_component',
                                                                  **kwd ) )
        return self.component_grid( trans, **kwd )

    @web.expose
    @web.require_login( "browse review" )
    def browse_review( self, trans, **kwd ):
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        review = review_util.get_review( trans.app, kwd[ 'id' ] )
        repository = review.repository
        repo = hg_util.get_repo_for_repository( trans.app, repository=repository, repo_path=None, create=False )
        rev, changeset_revision_label = hg_util.get_rev_label_from_changeset_revision( repo, review.changeset_revision )
        return trans.fill_template( '/webapps/tool_shed/repository_review/browse_review.mako',
                                    repository=repository,
                                    changeset_revision_label=changeset_revision_label,
                                    review=review,
                                    message=message,
                                    status=status )

    def copy_review( self, trans, review_to_copy, review ):
        for component_review in review_to_copy.component_reviews:
            copied_component_review = trans.model.ComponentReview( repository_review_id=review.id,
                                                                   component_id=component_review.component.id,
                                                                   comment=component_review.comment,
                                                                   private=component_review.private,
                                                                   approved=component_review.approved,
                                                                   rating=component_review.rating )
            trans.sa_session.add( copied_component_review )
            trans.sa_session.flush()
        review.approved = review_to_copy.approved
        review.rating = review_to_copy.rating
        trans.sa_session.add( review )
        trans.sa_session.flush()

    @web.expose
    @web.require_login( "create component" )
    def create_component( self, trans, **kwd ):
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        name = kwd.get( 'name', '' )
        description = kwd.get( 'description', '' )
        if kwd.get( 'create_component_button', False ):
            if not name or not description:
                message = 'Enter a valid name and a description'
                status = 'error'
            elif review_util.get_component_by_name( trans.app, name ):
                message = 'A component with that name already exists'
                status = 'error'
            else:
                component = trans.app.model.Component( name=name, description=description )
                trans.sa_session.add( component )
                trans.sa_session.flush()
                message = "Component '%s' has been created" % escape( component.name )
                status = 'done'
                trans.response.send_redirect( web.url_for( controller='repository_review',
                                                           action='manage_components',
                                                           message=message,
                                                           status=status ) )
        return trans.fill_template( '/webapps/tool_shed/repository_review/create_component.mako',
                                    name=name,
                                    description=description,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_login( "create review" )
    def create_review( self, trans, **kwd ):
        # The value of the received id is the encoded repository id.
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        repository_id = kwd.get( 'id', None )
        changeset_revision = kwd.get( 'changeset_revision', None )
        previous_review_id = kwd.get( 'previous_review_id', None )
        create_without_copying = 'create_without_copying' in kwd
        if repository_id:
            if changeset_revision:
                # Make sure there is not already a review of the revision by the user.
                repository = repository_util.get_repository_in_tool_shed( trans.app, repository_id )
                if review_util.get_review_by_repository_id_changeset_revision_user_id( app=trans.app,
                                                                                       repository_id=repository_id,
                                                                                       changeset_revision=changeset_revision,
                                                                                       user_id=trans.security.encode_id( trans.user.id ) ):
                    message = "You have already created a review for revision <b>%s</b> of repository <b>%s</b>." % ( changeset_revision, escape( repository.name ) )
                    status = "error"
                else:
                    # See if there are any reviews for previous changeset revisions that the user can copy.
                    if not create_without_copying and \
                            not previous_review_id and \
                            review_util.has_previous_repository_reviews( trans.app, repository, changeset_revision ):
                        return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                          action='select_previous_review',
                                                                          **kwd ) )
                    # A review can be initially performed only on an installable revision of a repository, so make sure we have metadata associated
                    # with the received changeset_revision.
                    repository_metadata = metadata_util.get_repository_metadata_by_changeset_revision( trans.app, repository_id, changeset_revision )
                    if repository_metadata:
                        metadata = repository_metadata.metadata
                        if metadata:
                            review = trans.app.model.RepositoryReview( repository_id=repository_metadata.repository_id,
                                                                       changeset_revision=changeset_revision,
                                                                       user_id=trans.user.id,
                                                                       rating=None,
                                                                       deleted=False )
                            trans.sa_session.add( review )
                            trans.sa_session.flush()
                            if previous_review_id:
                                review_to_copy = review_util.get_review( trans.app, previous_review_id )
                                self.copy_review( trans, review_to_copy, review )
                            review_id = trans.security.encode_id( review.id )
                            message = "Begin your review of revision <b>%s</b> of repository <b>%s</b>." \
                                % ( changeset_revision, repository.name )
                            status = 'done'
                            trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                       action='edit_review',
                                                                       id=review_id,
                                                                       message=message,
                                                                       status=status ) )
                    else:
                        message = "A new review cannot be created for revision <b>%s</b> of repository <b>%s</b>.  Select a valid revision and try again." \
                            % ( changeset_revision, escape( repository.name ) )
                        kwd[ 'message' ] = message
                        kwd[ 'status' ] = 'error'
            else:
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='manage_repository_reviews',
                                                                  **kwd ) )
        return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                          action='view_or_manage_repository',
                                                          **kwd ) )

    @web.expose
    @web.require_login( "edit component" )
    def edit_component( self, trans, **kwd ):
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        id = kwd.get( 'id', None )
        if not id:
            message = "No component ids received for editing"
            trans.response.send_redirect( web.url_for( controller='admin',
                                                       action='manage_categories',
                                                       message=message,
                                                       status='error' ) )
        component = review_util.get_component( trans.app, id )
        if kwd.get( 'edit_component_button', False ):
            new_description = kwd.get( 'description', '' ).strip()
            if component.description != new_description:
                component.description = new_description
                trans.sa_session.add( component )
                trans.sa_session.flush()
                message = "The information has been saved for the component named <b>%s</b>" % escape( component.name )
                status = 'done'
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='manage_components',
                                                                  message=message,
                                                                  status=status ) )
        return trans.fill_template( '/webapps/tool_shed/repository_review/edit_component.mako',
                                    component=component,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_login( "edit review" )
    def edit_review( self, trans, **kwd ):
        # The value of the received id is the encoded review id.
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        review_id = kwd.get( 'id', None )
        review = review_util.get_review( trans.app, review_id )
        components_dict = odict()
        for component in review_util.get_components( trans.app ):
            components_dict[ component.name ] = dict( component=component, component_review=None )
        repository = review.repository
        repo = hg_util.get_repo_for_repository( trans.app, repository=repository, repo_path=None, create=False )
        for component_review in review.component_reviews:
            if component_review and component_review.component:
                component_name = component_review.component.name
                if component_name in components_dict:
                    component_review_dict = components_dict[ component_name ]
                    component_review_dict[ 'component_review' ] = component_review
                    components_dict[ component_name ] = component_review_dict
        # Handle a Save button click.
        save_button_clicked = False
        save_buttons = [ '%s%sreview_button' % ( comp_name, STRSEP ) for comp_name in components_dict.keys() ]
        save_buttons.append( 'revision_approved_button' )
        for save_button in save_buttons:
            if save_button in kwd:
                save_button_clicked = True
                break
        if save_button_clicked:
            # Handle the revision_approved_select_field value.
            revision_approved = kwd.get( 'revision_approved', None )
            revision_approved_setting_changed = False
            if revision_approved:
                revision_approved = str( revision_approved )
                if review.approved != revision_approved:
                    revision_approved_setting_changed = True
                    review.approved = revision_approved
                    trans.sa_session.add( review )
                    trans.sa_session.flush()
            saved_component_names = []
            for component_name in components_dict.keys():
                flushed = False
                # Retrieve the review information from the form.
                # The star rating form field is a radio button list, so it will not be received if it was not clicked in the form.
                # Due to this behavior, default the value to 0.
                rating = 0
                for k, v in kwd.items():
                    if k.startswith( '%s%s' % ( component_name, STRSEP ) ):
                        component_review_attr = k.replace( '%s%s' % ( component_name, STRSEP ), '' )
                        if component_review_attr == 'component_id':
                            component_id = str( v )
                        elif component_review_attr == 'comment':
                            comment = str( v )
                        elif component_review_attr == 'private':
                            private = CheckboxField.is_checked( v )
                        elif component_review_attr == 'approved':
                            approved = str( v )
                        elif component_review_attr == 'rating':
                            rating = int( str( v ) )
                component = review_util.get_component( trans.app, component_id )
                component_review = \
                    review_util.get_component_review_by_repository_review_id_component_id( trans.app,
                                                                                           review_id,
                                                                                           component_id )
                if component_review:
                    # See if the existing component review should be updated.
                    if component_review.comment != comment or \
                            component_review.private != private or \
                            component_review.approved != approved or \
                            component_review.rating != rating:
                        component_review.comment = comment
                        component_review.private = private
                        component_review.approved = approved
                        component_review.rating = rating
                        trans.sa_session.add( component_review )
                        trans.sa_session.flush()
                        flushed = True
                        saved_component_names.append( component_name )
                else:
                    # See if a new component_review should be created.
                    if comment or private or approved != trans.model.ComponentReview.approved_states.NO or rating:
                        component_review = trans.model.ComponentReview( repository_review_id=review.id,
                                                                        component_id=component.id,
                                                                        comment=comment,
                                                                        approved=approved,
                                                                        rating=rating )
                        trans.sa_session.add( component_review )
                        trans.sa_session.flush()
                        flushed = True
                        saved_component_names.append( component_name )
                if flushed:
                    # Update the repository rating value to be the average of all component review ratings.
                    average_rating = trans.sa_session.query( func.avg( trans.model.ComponentReview.table.c.rating ) ) \
                                                     .filter( and_( trans.model.ComponentReview.table.c.repository_review_id == review.id,
                                                                    trans.model.ComponentReview.table.c.deleted == false(),
                                                                    trans.model.ComponentReview.table.c.approved != trans.model.ComponentReview.approved_states.NA ) ) \
                                                     .scalar()
                    if average_rating is not None:
                        review.rating = int( average_rating )
                    trans.sa_session.add( review )
                    trans.sa_session.flush()
                    # Update the information in components_dict.
                    if component_name in components_dict:
                        component_review_dict = components_dict[ component_name ]
                        component_review_dict[ 'component_review' ] = component_review
                        components_dict[ component_name ] = component_review_dict
            if revision_approved_setting_changed:
                message += 'Approved value <b>%s</b> saved for this revision.<br/>' % review.approved
            if saved_component_names:
                message += 'Reviews were saved for components: %s' % ', '.join( saved_component_names )
            if not revision_approved_setting_changed and not saved_component_names:
                message += 'No changes were made to this review, so nothing was saved.'
        if review and review.approved:
            selected_value = review.approved
        else:
            selected_value = trans.model.ComponentReview.approved_states.NO
        revision_approved_select_field = grids_util.build_approved_select_field( trans,
                                                                                 name='revision_approved',
                                                                                 selected_value=selected_value,
                                                                                 for_component=False )
        rev, changeset_revision_label = hg_util.get_rev_label_from_changeset_revision( repo, review.changeset_revision )
        return trans.fill_template( '/webapps/tool_shed/repository_review/edit_review.mako',
                                    repository=repository,
                                    review=review,
                                    changeset_revision_label=changeset_revision_label,
                                    revision_approved_select_field=revision_approved_select_field,
                                    components_dict=components_dict,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_login( "manage components" )
    def manage_components( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "create":
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='create_component',
                                                                  **kwd ) )
            elif operation == "edit":
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='edit_component',
                                                                  **kwd ) )
        if 'message' not in kwd:
            message = "This is a list of repository components (features) that can be reviewed.  You can add new components or change "
            message += "the description of an existing component if appropriate.  Click on the name link to change the description."
            status = "warning"
            kwd[ 'message' ] = message
            kwd[ 'status' ] = status
        return self.component_grid( trans, **kwd )

    @web.expose
    @web.require_login( "manage repositories ready for review" )
    def manage_repositories_ready_for_review( self, trans, **kwd ):
        """
        A repository is ready to be reviewed if one of the following conditions is met:
        1) It contains no tools
        2) It contains tools the tools_functionally_correct flag is set to True.  This implies that the repository metadata revision was installed and tested
           by the Tool Shed's install and test framework.
        """
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "inspect repository revisions":
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='create_review',
                                                                  **kwd ) )
            if operation == "view_or_manage_repository":
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='view_or_manage_repository',
                                                                  **kwd ) )
        message = 'Any of these repositories that contain tools have been installed into Galaxy and proven to be functionally correct by executing the tests defined '
        message += 'for each tool.  Repositories that do not contain tools have not been installed into Galaxy. '
        kwd[ 'message' ] = message
        kwd[ 'status' ] = 'warning'
        return self.repositories_ready_for_review_grid( trans, **kwd )

    @web.expose
    @web.require_login( "manage repositories reviewed by me" )
    def manage_repositories_reviewed_by_me( self, trans, **kwd ):
        # The value of the received id is the encoded repository id.
        if 'operation' in kwd:
            kwd[ 'mine' ] = True
            return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                              action='manage_repositories_with_reviews',
                                                              **kwd ) )
        self.repositories_reviewed_by_me_grid.title = 'Repositories reviewed by me'
        return self.repositories_reviewed_by_me_grid( trans, **kwd )

    @web.expose
    @web.require_login( "manage repositories with invalid tests" )
    def manage_repositories_with_invalid_tests( self, trans, **kwd ):
        """
        Display a list of repositories that contain tools, have not yet been reviewed, and have invalid functional tests.  Tests are defined as
        invalid if they are missing from the tool config or if defined test data is not included in the repository.
        """
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "inspect repository revisions":
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='create_review',
                                                                  **kwd ) )
            if operation == "view_or_manage_repository":
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='view_or_manage_repository',
                                                                  **kwd ) )
        message = 'These repositories contain tools with missing functional tests or test data.  '
        kwd[ 'message' ] = message
        kwd[ 'status' ] = 'warning'
        return self.repositories_with_no_tool_tests_grid( trans, **kwd )

    @web.expose
    @web.require_login( "manage repositories with reviews" )
    def manage_repositories_with_reviews( self, trans, **kwd ):
        # The value of the received id is the encoded repository id.
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "inspect repository revisions":
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='manage_repository_reviews',
                                                                  **kwd ) )
            if operation == "view_or_manage_repository":
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='view_or_manage_repository',
                                                                  **kwd ) )
        return self.repositories_with_reviews_grid( trans, **kwd )

    @web.expose
    @web.require_login( "manage repositories without reviews" )
    def manage_repositories_without_reviews( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "inspect repository revisions":
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='create_review',
                                                                  **kwd ) )
            if operation == "view_or_manage_repository":
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='view_or_manage_repository',
                                                                  **kwd ) )
        return self.repositories_without_reviews_grid( trans, **kwd )

    @web.expose
    @web.require_login( "manage repository reviews" )
    def manage_repository_reviews( self, trans, mine=False, **kwd ):
        # The value of the received id is the encoded repository id.
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        repository_id = kwd.get( 'id', None )
        if repository_id:
            repository = suc.get_repository_in_tool_shed( trans.app, repository_id )
            repo = hg_util.get_repo_for_repository( trans.app, repository=repository, repo_path=None, create=False )
            metadata_revision_hashes = [ metadata_revision.changeset_revision for metadata_revision in repository.metadata_revisions ]
            reviewed_revision_hashes = [ review.changeset_revision for review in repository.reviews ]
            reviews_dict = odict()
            for changeset in hg_util.get_reversed_changelog_changesets( repo ):
                ctx = repo.changectx( changeset )
                changeset_revision = str( ctx )
                if changeset_revision in metadata_revision_hashes or changeset_revision in reviewed_revision_hashes:
                    rev, changeset_revision_label = hg_util.get_rev_label_from_changeset_revision( repo, changeset_revision )
                    if changeset_revision in reviewed_revision_hashes:
                        # Find the review for this changeset_revision
                        repository_reviews = \
                            review_util.get_reviews_by_repository_id_changeset_revision( trans.app,
                                                                                         repository_id,
                                                                                         changeset_revision )
                        # Determine if the current user can add a review to this revision.
                        can_add_review = trans.user not in [ repository_review.user for repository_review in repository_reviews ]
                        repository_metadata = metadata_util.get_repository_metadata_by_changeset_revision( trans.app, repository_id, changeset_revision )
                        if repository_metadata:
                            repository_metadata_reviews = util.listify( repository_metadata.reviews )
                        else:
                            repository_metadata_reviews = []
                    else:
                        repository_reviews = []
                        repository_metadata_reviews = []
                        can_add_review = True
                    installable = changeset_revision in metadata_revision_hashes
                    revision_dict = dict( changeset_revision_label=changeset_revision_label,
                                          repository_reviews=repository_reviews,
                                          repository_metadata_reviews=repository_metadata_reviews,
                                          installable=installable,
                                          can_add_review=can_add_review )
                    reviews_dict[ changeset_revision ] = revision_dict
        return trans.fill_template( '/webapps/tool_shed/repository_review/reviews_of_repository.mako',
                                    repository=repository,
                                    reviews_dict=reviews_dict,
                                    mine=mine,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_login( "manage repository reviews of revision" )
    def manage_repository_reviews_of_revision( self, trans, **kwd ):
        # The value of the received id is the encoded repository id.
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        repository_id = kwd.get( 'id', None )
        changeset_revision = kwd.get( 'changeset_revision', None )
        repository = repository_util.get_repository_in_tool_shed( trans.app, repository_id )
        repo = hg_util.get_repo_for_repository( trans.app, repository=repository, repo_path=None, create=False )
        installable = changeset_revision in [ metadata_revision.changeset_revision for metadata_revision in repository.metadata_revisions ]
        rev, changeset_revision_label = hg_util.get_rev_label_from_changeset_revision( repo, changeset_revision )
        reviews = review_util.get_reviews_by_repository_id_changeset_revision( trans.app,
                                                                               repository_id,
                                                                               changeset_revision )
        return trans.fill_template( '/webapps/tool_shed/repository_review/reviews_of_changeset_revision.mako',
                                    repository=repository,
                                    changeset_revision=changeset_revision,
                                    changeset_revision_label=changeset_revision_label,
                                    reviews=reviews,
                                    installable=installable,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_login( "repository reviews by user" )
    def repository_reviews_by_user( self, trans, **kwd ):

        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            # The value of the received id is the encoded review id.
            review = review_util.get_review( trans.app, kwd[ 'id' ] )
            repository = review.repository
            kwd[ 'id' ] = trans.security.encode_id( repository.id )
            if operation == "inspect repository revisions":
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='manage_repository_reviews',
                                                                  **kwd ) )
            if operation == "view_or_manage_repository":
                kwd[ 'changeset_revision' ] = review.changeset_revision
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='view_or_manage_repository',
                                                                  **kwd ) )
        # The user may not be the current user.  The value of the received id is the encoded user id.
        user = suc.get_user( trans.app, kwd[ 'id' ] )
        self.repository_reviews_by_user_grid.title = "All repository revision reviews for user '%s'" % user.username
        return self.repository_reviews_by_user_grid( trans, **kwd )

    @web.expose
    @web.require_login( "reviewed repositories i own" )
    def reviewed_repositories_i_own( self, trans, **kwd ):
        # The value of the received id is the encoded repository id.
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "inspect repository revisions":
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='manage_repository_reviews',
                                                                  **kwd ) )
            if operation == "view_or_manage_repository":
                return trans.response.send_redirect( web.url_for( controller='repository_review',
                                                                  action='view_or_manage_repository',
                                                                  **kwd ) )
        return self.reviewed_repositories_i_own_grid( trans, **kwd )

    @web.expose
    @web.require_login( "select previous review" )
    def select_previous_review( self, trans, **kwd ):
        # The value of the received id is the encoded repository id.
        message = escape( kwd.get( 'message', '' ) )
        status = kwd.get( 'status', 'done' )
        repository = repository_util.get_repository_in_tool_shed( trans.app, kwd[ 'id' ] )
        changeset_revision = kwd.get( 'changeset_revision', None )
        repo = hg_util.get_repo_for_repository( trans.app, repository=repository, repo_path=None, create=False )
        previous_reviews_dict = review_util.get_previous_repository_reviews( trans.app,
                                                                             repository,
                                                                             changeset_revision )
        rev, changeset_revision_label = hg_util.get_rev_label_from_changeset_revision( repo, changeset_revision )
        return trans.fill_template( '/webapps/tool_shed/repository_review/select_previous_review.mako',
                                    repository=repository,
                                    changeset_revision=changeset_revision,
                                    changeset_revision_label=changeset_revision_label,
                                    previous_reviews_dict=previous_reviews_dict,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_login( "view or manage repository" )
    def view_or_manage_repository( self, trans, **kwd ):
        repository = repository_util.get_repository_in_tool_shed( trans.app, kwd[ 'id' ] )
        if trans.user_is_admin() or repository.user == trans.user:
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='manage_repository',
                                                              **kwd ) )
        else:
            return trans.response.send_redirect( web.url_for( controller='repository',
                                                              action='view_repository',
                                                              **kwd ) )
