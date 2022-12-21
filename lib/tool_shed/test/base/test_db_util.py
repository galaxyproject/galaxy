import logging
from typing import Optional

from sqlalchemy import (
    and_,
    false,
    true,
)

import galaxy.model
import galaxy.model.tool_shed_install
import tool_shed.webapp.model as model

log = logging.getLogger("test.tool_shed.test_db_util")


def sa_session():
    from galaxy_test.driver.driver_util import tool_shed_context as sa_session

    return sa_session


def install_session():
    from galaxy_test.driver.driver_util import install_context as install_session

    return install_session


def delete_obj(obj):
    sa_session().delete(obj)
    sa_session().flush()


def delete_user_roles(user):
    for ura in user.roles:
        sa_session().delete(ura)
    sa_session().flush()


def flush(obj):
    sa_session().add(obj)
    sa_session().flush()


def get_all_repositories():
    return sa_session().query(model.Repository).all()


def get_all_installed_repositories(actually_installed=False):
    if actually_installed:
        return (
            install_session()
            .query(galaxy.model.tool_shed_install.ToolShedRepository)
            .filter(
                and_(
                    galaxy.model.tool_shed_install.ToolShedRepository.table.c.deleted == false(),
                    galaxy.model.tool_shed_install.ToolShedRepository.table.c.uninstalled == false(),
                    galaxy.model.tool_shed_install.ToolShedRepository.table.c.status
                    == galaxy.model.tool_shed_install.ToolShedRepository.installation_status.INSTALLED,
                )
            )
            .all()
        )
    else:
        return install_session().query(galaxy.model.tool_shed_install.ToolShedRepository).all()


def get_galaxy_repository_by_name_owner_changeset_revision(repository_name, owner, changeset_revision):
    return (
        install_session()
        .query(galaxy.model.tool_shed_install.ToolShedRepository)
        .filter(
            and_(
                galaxy.model.tool_shed_install.ToolShedRepository.table.c.name == repository_name,
                galaxy.model.tool_shed_install.ToolShedRepository.table.c.owner == owner,
                galaxy.model.tool_shed_install.ToolShedRepository.table.c.changeset_revision == changeset_revision,
            )
        )
        .first()
    )


def get_installed_repository_by_id(repository_id):
    return (
        install_session()
        .query(galaxy.model.tool_shed_install.ToolShedRepository)
        .filter(galaxy.model.tool_shed_install.ToolShedRepository.table.c.id == repository_id)
        .first()
    )


def get_installed_repository_by_name_owner(repository_name, owner, return_multiple=False):
    query = (
        install_session()
        .query(galaxy.model.tool_shed_install.ToolShedRepository)
        .filter(
            and_(
                galaxy.model.tool_shed_install.ToolShedRepository.table.c.name == repository_name,
                galaxy.model.tool_shed_install.ToolShedRepository.table.c.owner == owner,
            )
        )
    )
    if return_multiple:
        return query.all()
    return query.first()


def get_role(user, role_name):
    for role in user.all_roles():
        if role.name == role_name:
            return role
    return None


def get_repository_role_association(repository_id, role_id):
    rra = (
        sa_session()
        .query(model.RepositoryRoleAssociation)
        .filter(
            and_(
                model.RepositoryRoleAssociation.table.c.role_id == role_id,
                model.RepositoryRoleAssociation.table.c.repository_id == repository_id,
            )
        )
        .first()
    )
    return rra


def get_repository_by_id(repository_id):
    return sa_session().query(model.Repository).filter(model.Repository.table.c.id == repository_id).first()


def get_repository_downloadable_revisions(repository_id):
    revisions = (
        sa_session()
        .query(model.RepositoryMetadata)
        .filter(
            and_(
                model.RepositoryMetadata.table.c.repository_id == repository_id,
                model.RepositoryMetadata.table.c.downloadable == true(),
            )
        )
        .all()
    )
    return revisions


def get_repository_metadata_for_changeset_revision(
    repository_id: int, changeset_revision: Optional[str]
) -> model.RepositoryMetadata:
    repository_metadata = (
        sa_session()
        .query(model.RepositoryMetadata)
        .filter(
            and_(
                model.RepositoryMetadata.table.c.repository_id == repository_id,
                model.RepositoryMetadata.table.c.changeset_revision == changeset_revision,
            )
        )
        .first()
    )
    return repository_metadata


def get_role_by_name(role_name):
    return sa_session().query(model.Role).filter(model.Role.table.c.name == role_name).first()


def get_user(email):
    return sa_session().query(model.User).filter(model.User.table.c.email == email).first()


def get_user_by_name(username):
    return sa_session().query(model.User).filter(model.User.table.c.username == username).first()


def mark_obj_deleted(obj):
    obj.deleted = True
    sa_session().add(obj)
    sa_session().flush()


def refresh(obj):
    sa_session().refresh(obj)


def ga_refresh(obj):
    install_session().refresh(obj)


def get_repository_by_name_and_owner(name, owner_username, return_multiple=False):
    owner = get_user_by_name(owner_username)
    repository = (
        sa_session()
        .query(model.Repository)
        .filter(and_(model.Repository.table.c.name == name, model.Repository.table.c.user_id == owner.id))
        .first()
    )
    return repository


def get_repository_metadata_by_repository_id_changeset_revision(repository_id, changeset_revision):
    repository_metadata = (
        sa_session()
        .query(model.RepositoryMetadata)
        .filter(
            and_(
                model.RepositoryMetadata.table.c.repository_id == repository_id,
                model.RepositoryMetadata.table.c.changeset_revision == changeset_revision,
            )
        )
        .first()
    )
    return repository_metadata
