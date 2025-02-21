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


def get_displayable_roles(session, trans_user, user_is_admin, security_agent):
    roles = []
    stmt = (
        select(Role, User.email)
        .outerjoin(
            UserRoleAssociation,
            and_(Role.id == UserRoleAssociation.role_id, Role.type == Role.types.PRIVATE),
        )
        .outerjoin(User)
        .where(Role.deleted == false())
    )

    for role, user_email in session.execute(stmt):
        if user_is_admin or security_agent.ok_to_display(trans_user, role):
            roles.append(role)
            if role.type == Role.types.PRIVATE:
                # For private roles, we expect an associated user. We use that user's email
                # as the private role's description.
                assert user_email, "Did not find user for private role {role}"
                role.description = f"Private role for {user_email}"
    return roles
