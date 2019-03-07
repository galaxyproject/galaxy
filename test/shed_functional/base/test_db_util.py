import logging

from sqlalchemy import and_, false, true

import galaxy.model
import galaxy.model.tool_shed_install
import galaxy.webapps.tool_shed.model as model
from base.driver_util import (  # noqa: I100,I201
    galaxy_context as ga_session,
    install_context as install_session,
    tool_shed_context as sa_session
)

log = logging.getLogger('test.tool_shed.test_db_util')


def delete_obj(obj):
    sa_session.delete(obj)
    sa_session.flush()


def delete_user_roles(user):
    for ura in user.roles:
        sa_session.delete(ura)
    sa_session.flush()


def flush(obj):
    sa_session.add(obj)
    sa_session.flush()


def get_all_repositories():
    return sa_session.query(model.Repository).all()


def get_all_installed_repositories(actually_installed=False):
    if actually_installed:
        return install_session.query(galaxy.model.tool_shed_install.ToolShedRepository) \
                              .filter(and_(galaxy.model.tool_shed_install.ToolShedRepository.table.c.deleted == false(),
                                           galaxy.model.tool_shed_install.ToolShedRepository.table.c.uninstalled == false(),
                                           galaxy.model.tool_shed_install.ToolShedRepository.table.c.status == galaxy.model.tool_shed_install.ToolShedRepository.installation_status.INSTALLED)) \
                              .all()
    else:
        return install_session.query(galaxy.model.tool_shed_install.ToolShedRepository).all()


def get_category_by_name(name):
    return sa_session.query(model.Category) \
                     .filter(model.Category.table.c.name == name) \
                     .first()


def get_default_user_permissions_by_role(role):
    return sa_session.query(model.DefaultUserPermissions) \
                     .filter(model.DefaultUserPermissions.table.c.role_id == role.id) \
                     .all()


def get_default_user_permissions_by_user(user):
    return sa_session.query(model.DefaultUserPermissions) \
                     .filter(model.DefaultUserPermissions.table.c.user_id == user.id) \
                     .all()


def get_galaxy_repository_by_name_owner_changeset_revision(repository_name, owner, changeset_revision):
    return install_session.query(galaxy.model.tool_shed_install.ToolShedRepository) \
                          .filter(and_(galaxy.model.tool_shed_install.ToolShedRepository.table.c.name == repository_name,
                                       galaxy.model.tool_shed_install.ToolShedRepository.table.c.owner == owner,
                                       galaxy.model.tool_shed_install.ToolShedRepository.table.c.changeset_revision == changeset_revision)) \
                          .first()


def get_installed_repository_by_id(repository_id):
    return install_session.query(galaxy.model.tool_shed_install.ToolShedRepository) \
                          .filter(galaxy.model.tool_shed_install.ToolShedRepository.table.c.id == repository_id) \
                          .first()


def get_installed_repository_by_name_owner(repository_name, owner, return_multiple=False):
    query = install_session.query(galaxy.model.tool_shed_install.ToolShedRepository) \
                           .filter(and_(galaxy.model.tool_shed_install.ToolShedRepository.table.c.name == repository_name,
                                        galaxy.model.tool_shed_install.ToolShedRepository.table.c.owner == owner))
    if return_multiple:
        return query.all()
    return query.first()


def get_private_role(user):
    for role in user.all_roles():
        if role.name == user.email and role.description == 'Private Role for %s' % user.email:
            return role
    raise AssertionError("Private role not found for user '%s'" % user.email)


def get_role(user, role_name):
    for role in user.all_roles():
        if role.name == role_name:
            return role
    return None


def get_repository_role_association(repository_id, role_id):
    rra = sa_session.query(model.RepositoryRoleAssociation) \
                    .filter(and_(model.RepositoryRoleAssociation.table.c.role_id == role_id,
                                 model.RepositoryRoleAssociation.table.c.repository_id == repository_id)) \
                    .first()
    return rra


def get_repository_reviews(repository_id, reviewer_user_id=None, changeset_revision=None):
    if reviewer_user_id and changeset_revision:
        reviews = sa_session.query(model.RepositoryReview) \
                            .filter(and_(model.RepositoryReview.table.c.repository_id == repository_id,
                                         model.RepositoryReview.table.c.deleted == false(),
                                         model.RepositoryReview.table.c.changeset_revision == changeset_revision,
                                         model.RepositoryReview.table.c.user_id == reviewer_user_id)) \
                            .all()
    elif reviewer_user_id:
        reviews = sa_session.query(model.RepositoryReview) \
                            .filter(and_(model.RepositoryReview.table.c.repository_id == repository_id,
                                         model.RepositoryReview.table.c.deleted == false(),
                                         model.RepositoryReview.table.c.user_id == reviewer_user_id)) \
                            .all()
    else:
        reviews = sa_session.query(model.RepositoryReview) \
                            .filter(and_(model.RepositoryReview.table.c.repository_id == repository_id,
                                         model.RepositoryReview.table.c.deleted == false())) \
                            .all()
    return reviews


def get_reviews_ordered_by_changeset_revision(repository_id, changelog_tuples, reviewer_user_id=None):
    reviews = get_repository_reviews(repository_id, reviewer_user_id=reviewer_user_id)
    ordered_reviews = []
    for ctx_rev, changeset_hash in changelog_tuples:
        for review in reviews:
            if str(review.changeset_revision) == str(changeset_hash):
                ordered_reviews.append(review)
    return ordered_reviews


def get_repository_by_id(repository_id):
    return sa_session.query(model.Repository) \
                     .filter(model.Repository.table.c.id == repository_id) \
                     .first()


def get_repository_downloadable_revisions(repository_id):
    revisions = sa_session.query(model.RepositoryMetadata) \
                          .filter(and_(model.RepositoryMetadata.table.c.repository_id == repository_id,
                                       model.RepositoryMetadata.table.c.downloadable == true())) \
                          .all()
    return revisions


def get_repository_metadata_for_changeset_revision(repository_id, changeset_revision):
    repository_metadata = sa_session.query(model.RepositoryMetadata) \
                                    .filter(and_(model.RepositoryMetadata.table.c.repository_id == repository_id,
                                                 model.RepositoryMetadata.table.c.changeset_revision == changeset_revision)) \
                                    .first()
    return repository_metadata


def get_repository_review_by_user_id_changeset_revision(user_id, repository_id, changeset_revision):
    review = sa_session.query(model.RepositoryReview) \
                       .filter(and_(model.RepositoryReview.table.c.user_id == user_id,
                                    model.RepositoryReview.table.c.repository_id == repository_id,
                                    model.RepositoryReview.table.c.changeset_revision == changeset_revision)) \
                       .first()
    return review


def get_role_by_name(role_name):
    return sa_session.query(model.Role) \
                     .filter(model.Role.table.c.name == role_name) \
                     .first()


def get_user(email):
    return sa_session.query(model.User) \
                     .filter(model.User.table.c.email == email) \
                     .first()


def get_user_by_name(username):
    return sa_session.query(model.User) \
                     .filter(model.User.table.c.username == username) \
                     .first()


def mark_obj_deleted(obj):
    obj.deleted = True
    sa_session.add(obj)
    sa_session.flush()


def refresh(obj):
    sa_session.refresh(obj)


def ga_refresh(obj):
    install_session.refresh(obj)


def get_galaxy_private_role(user):
    for role in user.all_roles():
        if role.name == user.email and role.description == 'Private Role for %s' % user.email:
            return role
    raise AssertionError("Private role not found for user '%s'" % user.email)


def get_galaxy_user(email):
    return ga_session.query(galaxy.model.User) \
                     .filter(galaxy.model.User.table.c.email == email) \
                     .first()


def get_repository_by_name_and_owner(name, owner_username, return_multiple=False):
    owner = get_user_by_name(owner_username)
    repository = sa_session.query(model.Repository) \
                           .filter(and_(model.Repository.table.c.name == name,
                                        model.Repository.table.c.user_id == owner.id)) \
                           .first()
    return repository


def get_repository_metadata_by_repository_id_changeset_revision(repository_id, changeset_revision):
    repository_metadata = sa_session.query(model.RepositoryMetadata) \
                                    .filter(and_(model.RepositoryMetadata.table.c.repository_id == repository_id,
                                                 model.RepositoryMetadata.table.c.changeset_revision == changeset_revision)) \
                                    .first()
    return repository_metadata
