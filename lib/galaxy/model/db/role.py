from sqlalchemy import (
    and_,
    false,
    func,
    or_,
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


def get_displayable_roles(
    session,
    trans_user,
    user_is_admin,
    search: str | None = None,
    limit: int | None = None,
    offset: int = 0,
):
    stmt = select(Role).where(Role.deleted == false())
    if not user_is_admin:
        if trans_user:
            # Non-admin users see: all non-private/non-sharing roles,
            # plus their own private role and their own sharing roles.
            user_role_ids = select(UserRoleAssociation.role_id).where(UserRoleAssociation.user_id == trans_user.id)
            stmt = stmt.where(
                or_(
                    ~Role.type.in_((Role.types.PRIVATE, Role.types.SHARING)),
                    and_(Role.type.in_((Role.types.PRIVATE, Role.types.SHARING)), Role.id.in_(user_role_ids)),
                )
            )
        else:
            # Anonymous: exclude private and sharing roles entirely
            stmt = stmt.where(~Role.type.in_((Role.types.PRIVATE, Role.types.SHARING)))
    if search:
        # LEFT JOIN to User via UserRoleAssociation for private roles only,
        # so coalesce(User.email, Role.name) gives the displayed name.
        stmt = stmt.outerjoin(
            UserRoleAssociation,
            and_(UserRoleAssociation.role_id == Role.id, Role.type == Role.types.PRIVATE),
        ).outerjoin(User, UserRoleAssociation.user_id == User.id)
        displayed_name = func.coalesce(User.email, Role.name)
        stmt = stmt.where(displayed_name.ilike(f"%{search}%"))
    stmt = stmt.order_by(Role.id)
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return session.scalars(stmt).all()


def get_private_role_user_emails_dict(session, role_ids: set[int] | None = None) -> dict[int, str]:
    """Return a mapping of private role ids to user emails.

    If role_ids is provided, only return mappings for roles in that set,
    avoiding a full table scan on large instances.
    """
    if role_ids is not None and not role_ids:
        return {}
    stmt = select(UserRoleAssociation.role_id, User.email).join(Role).join(User).where(Role.type == Role.types.PRIVATE)
    if role_ids is not None:
        stmt = stmt.where(UserRoleAssociation.role_id.in_(role_ids))
    roleid_email_tuples = session.execute(stmt).all()
    return dict(roleid_email_tuples)
