import logging

from sqlalchemy import and_

from tool_shed.util import hg_util

log = logging.getLogger(__name__)


def can_browse_repository_reviews(app, user, repository):
    """
    Determine if there are any reviews of the received repository for which the
    current user has permission to browse any component reviews.
    """
    if user:
        for review in repository.reviews:
            for component_review in review.component_reviews:
                if app.security_agent.user_can_browse_component_review(app, repository, component_review, user):
                    return True
    return False


def changeset_revision_reviewed_by_user(user, repository, changeset_revision):
    """Determine if the current changeset revision has been reviewed by the current user."""
    for review in repository.reviews:
        if review.changeset_revision == changeset_revision and review.user == user:
            return True
    return False


def get_component(app, id):
    """Get a component from the database."""
    sa_session = app.model.session
    return sa_session.query(app.model.Component).get(app.security.decode_id(id))


def get_component_review(app, id):
    """Get a component_review from the database"""
    sa_session = app.model.session
    return sa_session.query(app.model.ComponentReview).get(app.security.decode_id(id))


def get_component_by_name(app, name):
    """Get a component from the database via a name."""
    sa_session = app.model.session
    return sa_session.query(app.model.Component).filter(app.model.Component.table.c.name == name).first()


def get_component_review_by_repository_review_id_component_id(app, repository_review_id, component_id):
    """Get a component_review from the database via repository_review_id and component_id."""
    sa_session = app.model.session
    return (
        sa_session.query(app.model.ComponentReview)
        .filter(
            and_(
                app.model.ComponentReview.table.c.repository_review_id == app.security.decode_id(repository_review_id),
                app.model.ComponentReview.table.c.component_id == app.security.decode_id(component_id),
            )
        )
        .first()
    )


def get_components(app):
    sa_session = app.model.session
    return sa_session.query(app.model.Component).order_by(app.model.Component.name).all()


def get_previous_repository_reviews(app, repository, changeset_revision):
    """
    Return an ordered dictionary of repository reviews up to and including the
    received changeset revision.
    """
    repo = repository.hg_repo
    reviewed_revision_hashes = [review.changeset_revision for review in repository.reviews]
    previous_reviews_dict = {}
    for changeset in hg_util.reversed_upper_bounded_changelog(repo, changeset_revision):
        previous_changeset_revision = str(repo[changeset])
        if previous_changeset_revision in reviewed_revision_hashes:
            previous_rev, previous_changeset_revision_label = hg_util.get_rev_label_from_changeset_revision(
                repo, previous_changeset_revision
            )
            revision_reviews = get_reviews_by_repository_id_changeset_revision(
                app, app.security.encode_id(repository.id), previous_changeset_revision
            )
            previous_reviews_dict[previous_changeset_revision] = dict(
                changeset_revision_label=previous_changeset_revision_label, reviews=revision_reviews
            )
    return previous_reviews_dict


def get_review(app, id):
    """Get a repository_review from the database via id."""
    sa_session = app.model.session
    return sa_session.query(app.model.RepositoryReview).get(app.security.decode_id(id))


def get_review_by_repository_id_changeset_revision_user_id(app, repository_id, changeset_revision, user_id):
    """
    Get a repository_review from the database via repository id, changeset_revision
    and user_id.
    """
    sa_session = app.model.session
    return (
        sa_session.query(app.model.RepositoryReview)
        .filter(
            and_(
                app.model.RepositoryReview.repository_id == app.security.decode_id(repository_id),
                app.model.RepositoryReview.changeset_revision == changeset_revision,
                app.model.RepositoryReview.user_id == app.security.decode_id(user_id),
            )
        )
        .first()
    )


def get_reviews_by_repository_id_changeset_revision(app, repository_id, changeset_revision):
    """Get all repository_reviews from the database via repository id and changeset_revision."""
    sa_session = app.model.session
    return (
        sa_session.query(app.model.RepositoryReview)
        .filter(
            and_(
                app.model.RepositoryReview.repository_id == app.security.decode_id(repository_id),
                app.model.RepositoryReview.changeset_revision == changeset_revision,
            )
        )
        .all()
    )


def has_previous_repository_reviews(app, repository, changeset_revision):
    """
    Determine if a repository has a changeset revision review prior to the
    received changeset revision.
    """
    repo = repository.hg_repo
    reviewed_revision_hashes = [review.changeset_revision for review in repository.reviews]
    for changeset in hg_util.reversed_upper_bounded_changelog(repo, changeset_revision):
        previous_changeset_revision = str(repo[changeset])
        if previous_changeset_revision in reviewed_revision_hashes:
            return True
    return False
