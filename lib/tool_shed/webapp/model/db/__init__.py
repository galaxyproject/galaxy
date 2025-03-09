from typing import TYPE_CHECKING

from sqlalchemy import and_
from sqlalchemy.orm import joinedload

from tool_shed.webapp.model import (
    Repository,
    User,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import scoped_session


def get_repository_query(session: "scoped_session"):
    return session.query(Repository)


def get_repository_by_name(session: "scoped_session", name):
    """Get a repository from the database via name."""
    return get_repository_query(session).filter_by(name=name).first()


def get_repository_by_name_and_owner(session: "scoped_session", name, owner, eagerload_columns=None):
    """Get a repository from the database via name and owner"""
    repository_query = get_repository_query(session)
    q = repository_query.filter(
        and_(
            Repository.name == name,
            User.username == owner,
            Repository.user_id == User.id,
        )
    )
    if eagerload_columns:
        q = q.options(joinedload(*eagerload_columns))
    return q.first()
