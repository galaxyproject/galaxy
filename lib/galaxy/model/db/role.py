from sqlalchemy import (
    and_,
    false,
    select,
)

from galaxy.model import (
    Role,
    UserRoleAssociation,
)


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
