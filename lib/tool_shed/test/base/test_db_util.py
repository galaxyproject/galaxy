import logging
from typing import (
    List,
    Optional,
)

from sqlalchemy import (
    and_,
    false,
    true,
)

import galaxy.model
import galaxy.model.tool_shed_install
import tool_shed.webapp.model as model
from galaxy.managers.users import get_user_by_username

log = logging.getLogger("test.tool_shed.test_db_util")


def sa_session():
    from galaxy_test.driver.driver_util import tool_shed_context as sa_session

    return sa_session


def install_session():
    from galaxy_test.driver.driver_util import install_context as install_session

    return install_session


def flush(obj):
    sa_session().add(obj)
    sa_session().flush()


def get_all_repositories():
    return sa_session().query(model.Repository).all()


def get_all_installed_repositories(session=None) -> List[galaxy.model.tool_shed_install.ToolShedRepository]:
    if session is None:
        session = install_session()
    return list(
        session.query(galaxy.model.tool_shed_install.ToolShedRepository)
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


def get_installed_repository_by_id(repository_id):
    return (
        install_session()
        .query(galaxy.model.tool_shed_install.ToolShedRepository)
        .filter(galaxy.model.tool_shed_install.ToolShedRepository.table.c.id == repository_id)
        .first()
    )


def get_installed_repository_by_name_owner(repository_name, owner, return_multiple=False, session=None):
    if session is None:
        session = install_session()
    query = session.query(galaxy.model.tool_shed_install.ToolShedRepository).filter(
        and_(
            galaxy.model.tool_shed_install.ToolShedRepository.table.c.name == repository_name,
            galaxy.model.tool_shed_install.ToolShedRepository.table.c.owner == owner,
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


def get_user(email):
    return sa_session().query(model.User).filter(model.User.table.c.email == email).first()


def refresh(obj):
    sa_session().refresh(obj)


def ga_refresh(obj):
    install_session().refresh(obj)


def get_repository_by_name_and_owner(name, owner_username, return_multiple=False):
    owner = get_user_by_username(sa_session(), owner_username, model.User)
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
