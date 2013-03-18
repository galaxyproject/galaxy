import os, logging
from galaxy.util.odict import odict
import tool_shed.util.shed_util_common as suc
from galaxy.model.orm import and_

from galaxy import eggs
import pkg_resources

pkg_resources.require( 'mercurial' )
from mercurial import hg, ui, commands

log = logging.getLogger( __name__ )

def can_browse_repository_reviews( trans, repository ):
    """Determine if there are any reviews of the received repository for which the current user has permission to browse any component reviews."""
    user = trans.user
    if user:
        for review in repository.reviews:
            for component_review in review.component_reviews:
                if trans.app.security_agent.user_can_browse_component_review( trans.app, repository, component_review, user ):
                    return True
    return False

def changeset_revision_reviewed_by_user( trans, user, repository, changeset_revision ):
    """Determine if the current changeset revision has been reviewed by the current user."""
    for review in repository.reviews:
        if review.changeset_revision == changeset_revision and review.user == user:
            return True
    return False

def get_component( trans, id ):
    """Get a component from the database."""
    return trans.sa_session.query( trans.model.Component ).get( trans.security.decode_id( id ) )

def get_component_review( trans, id ):
    """Get a component_review from the database"""
    return trans.sa_session.query( trans.model.ComponentReview ).get( trans.security.decode_id( id ) )

def get_component_by_name( trans, name ):
    """Get a component from the database via a name."""
    return trans.sa_session.query( trans.app.model.Component ) \
                           .filter( trans.app.model.Component.table.c.name==name ) \
                           .first()

def get_component_review_by_repository_review_id_component_id( trans, repository_review_id, component_id ):
    """Get a component_review from the database via repository_review_id and component_id."""
    return trans.sa_session.query( trans.model.ComponentReview ) \
                           .filter( and_( trans.model.ComponentReview.table.c.repository_review_id == trans.security.decode_id( repository_review_id ),
                                          trans.model.ComponentReview.table.c.component_id == trans.security.decode_id( component_id ) ) ) \
                           .first()

def get_components( trans ):
    return trans.sa_session.query( trans.app.model.Component ) \
                           .order_by( trans.app.model.Component.name ) \
                           .all()

def get_previous_repository_reviews( trans, repository, changeset_revision ):
    """Return an ordered dictionary of repository reviews up to and including the received changeset revision."""
    repo = hg.repository( suc.get_configured_ui(), repository.repo_path( trans.app ) )
    reviewed_revision_hashes = [ review.changeset_revision for review in repository.reviews ]
    previous_reviews_dict = odict()
    for changeset in suc.reversed_upper_bounded_changelog( repo, changeset_revision ):
        previous_changeset_revision = str( repo.changectx( changeset ) )
        if previous_changeset_revision in reviewed_revision_hashes:
            previous_rev, previous_changeset_revision_label = suc.get_rev_label_from_changeset_revision( repo, previous_changeset_revision )
            revision_reviews = get_reviews_by_repository_id_changeset_revision( trans,
                                                                                trans.security.encode_id( repository.id ),
                                                                                previous_changeset_revision )
            previous_reviews_dict[ previous_changeset_revision ] = dict( changeset_revision_label=previous_changeset_revision_label,
                                                                         reviews=revision_reviews )
    return previous_reviews_dict

def get_review( trans, id ):
    """Get a repository_review from the database via id."""
    return trans.sa_session.query( trans.model.RepositoryReview ).get( trans.security.decode_id( id ) )

def get_review_by_repository_id_changeset_revision_user_id( trans, repository_id, changeset_revision, user_id ):
    """Get a repository_review from the database via repository id, changeset_revision and user_id."""
    return trans.sa_session.query( trans.model.RepositoryReview ) \
                           .filter( and_( trans.model.RepositoryReview.repository_id == trans.security.decode_id( repository_id ),
                                          trans.model.RepositoryReview.changeset_revision == changeset_revision,
                                          trans.model.RepositoryReview.user_id == trans.security.decode_id( user_id ) ) ) \
                           .first()

def get_reviews_by_repository_id_changeset_revision( trans, repository_id, changeset_revision ):
    """Get all repository_reviews from the database via repository id and changeset_revision."""
    return trans.sa_session.query( trans.model.RepositoryReview ) \
                           .filter( and_( trans.model.RepositoryReview.repository_id == trans.security.decode_id( repository_id ),
                                          trans.model.RepositoryReview.changeset_revision == changeset_revision ) ) \
                           .all()

def has_previous_repository_reviews( trans, repository, changeset_revision ):
    """Determine if a repository has a changeset revision review prior to the received changeset revision."""
    repo = hg.repository( suc.get_configured_ui(), repository.repo_path( trans.app ) )
    reviewed_revision_hashes = [ review.changeset_revision for review in repository.reviews ]
    for changeset in suc.reversed_upper_bounded_changelog( repo, changeset_revision ):
        previous_changeset_revision = str( repo.changectx( changeset ) )
        if previous_changeset_revision in reviewed_revision_hashes:
            return True
    return False
