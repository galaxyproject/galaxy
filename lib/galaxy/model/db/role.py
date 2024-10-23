from sqlalchemy import (
    and_,
    false,
    select,
)

from galaxy.model import (
    Role,
    User,
    UserRoleAssociation,
)
from galaxy.model.scoped_session import galaxy_scoped_session


def get_roles_with_resolved_names(session):
    """
    Return list of roles with names resolved against associated user
    NOTE: do not update roles from this list, otherwise, the resolved name will be saved.
    """
    stmt = select(Role, User.email).outerjoin(Role.users).outerjoin(User)
    data = session.execute(stmt)
    roles = []
    for row in data:
        role, email = row[0], row[1]
        if role.type == Role.types.PRIVATE:
            role.name = f"{Role.private_role_name_prefix}{email}"
        roles.append(role)
    return roles


def get_npns_roles(session):
    """
    non-private, non-sharing roles
    """
    stmt = (
        select(Role)
        .where(and_(Role.deleted == false(), Role.type != Role.types.PRIVATE, Role.type != Role.types.SHARING))
        .order_by(Role.name)
    )
    return session.scalars(stmt)


def get_private_user_role(user, session):
    stmt = (
        select(Role)
        .where(
            and_(
                UserRoleAssociation.user_id == user.id,
                Role.id == UserRoleAssociation.role_id,
                Role.type == Role.types.PRIVATE,
            )
        )
        .distinct()
    )
    return session.execute(stmt).scalar_one_or_none()


def get_roles_by_ids(session: galaxy_scoped_session, role_ids):
    stmt = select(Role).where(Role.id.in_(role_ids))
    return session.scalars(stmt).all()
