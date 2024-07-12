import logging
from typing import List

from sqlalchemy import (
    false,
    select,
)

import galaxy.model
import galaxy.model.tool_shed_install
import tool_shed.webapp.model as model
from galaxy.model.db.user import (
    get_user_by_email,
    get_user_by_username,
)

log = logging.getLogger("test.tool_shed.test_db_util")


def sa_session():
    from .driver import tool_shed_context as sa_session

    return sa_session


def install_session():
    from galaxy_test.driver.driver_util import install_context as install_session

    return install_session


def flush(obj):
    sa_session().add(obj)
    sa_session().flush()


def get_all_repositories():
    return sa_session().scalars(select(model.Repository)).all()


def get_all_installed_repositories(session=None) -> List[galaxy.model.tool_shed_install.ToolShedRepository]:
    if session is None:
        session = install_session()
    ToolShedRepository = galaxy.model.tool_shed_install.ToolShedRepository
    stmt = (
        select(ToolShedRepository)
        .where(ToolShedRepository.deleted == false())
        .where(ToolShedRepository.uninstalled == false())
        .where(ToolShedRepository.status == ToolShedRepository.installation_status.INSTALLED)
    )
    return session.scalars(stmt).all()


def get_installed_repository_by_id(repository_id):
    return install_session().get(galaxy.model.tool_shed_install.ToolShedRepository, repository_id)


def get_installed_repository_by_name_owner(repository_name, owner, return_multiple=False, session=None):
    if session is None:
        session = install_session()
    ToolShedRepository = galaxy.model.tool_shed_install.ToolShedRepository
    stmt = (
        select(ToolShedRepository)
        .where(ToolShedRepository.name == repository_name)
        .where(ToolShedRepository.owner == owner)
    )
    if return_multiple:
        return session.scalars(stmt).all()
    return session.scalars(stmt.limit(1)).first()


def get_role(user, role_name):
    for role in user.all_roles():
        if role.name == role_name:
            return role
    return None


def get_repository_role_association(repository_id, role_id):
    stmt = (
        select(model.RepositoryRoleAssociation)
        .where(model.RepositoryRoleAssociation.role_id == role_id)
        .where(model.RepositoryRoleAssociation.repository_id == repository_id)
        .limit(1)
    )
    return sa_session().scalars(stmt).first()


def get_repository_by_id(repository_id):
    return sa_session().get(model.Repository, repository_id)


def get_user(email):
    return get_user_by_email(sa_session(), email, model.User)


def refresh(obj):
    sa_session().refresh(obj)


def ga_refresh(obj):
    install_session().refresh(obj)


def get_repository_by_name_and_owner(name, owner_username, return_multiple=False):
    owner = get_user_by_username(sa_session(), owner_username, model.User)
    stmt = (
        select(model.Repository)
        .where(model.Repository.name == name)
        .where(model.Repository.user_id == owner.id)
        .limit(1)
    )
    return sa_session().scalars(stmt).first()


def get_repository_metadata_by_repository_id_changeset_revision(repository_id, changeset_revision):
    stmt = (
        select(model.RepositoryMetadata)
        .where(model.RepositoryMetadata.repository_id == repository_id)
        .where(model.RepositoryMetadata.changeset_revision == changeset_revision)
        .limit(1)
    )
    return sa_session().scalars(stmt).first()
