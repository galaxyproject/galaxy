from typing import Optional

from sqlalchemy import (
    false,
    func,
    or_,
    select,
    true,
)

from galaxy.model import (
    Role,
    User,
)
from galaxy.model.scoped_session import galaxy_scoped_session


def get_users_by_ids(session: galaxy_scoped_session, user_ids):
    stmt = select(User).where(User.id.in_(user_ids))
    return session.scalars(stmt).all()


# The get_user_by_email and get_user_by_username functions may be called from
# the tool_shed app, which has its own User model, which is different from
# galaxy.model.User. In that case, the tool_shed user model should be passed as
# the model_class argument.
def get_user_by_email(session, email: str, model_class=User, case_sensitive=True):
    filter_clause = model_class.email == email
    if not case_sensitive:
        filter_clause = func.lower(model_class.email) == func.lower(email)
    stmt = select(model_class).where(filter_clause).limit(1)
    return session.scalars(stmt).first()


def get_user_by_username(session, username: str, model_class=User):
    stmt = select(model_class).filter(model_class.username == username).limit(1)
    return session.scalars(stmt).first()


def get_users_for_index(
    session,
    deleted: bool,
    f_email: Optional[str] = None,
    f_name: Optional[str] = None,
    f_any: Optional[str] = None,
    is_admin: bool = False,
    expose_user_email: bool = False,
    expose_user_name: bool = False,
):
    stmt = select(User)
    if f_email and (is_admin or expose_user_email):
        stmt = stmt.where(User.email.like(f"%{f_email}%"))
    if f_name and (is_admin or expose_user_name):
        stmt = stmt.where(User.username.like(f"%{f_name}%"))
    if f_any:
        if is_admin:
            stmt = stmt.where(or_(User.email.like(f"%{f_any}%"), User.username.like(f"%{f_any}%")))
        else:
            if expose_user_email and expose_user_name:
                stmt = stmt.where(or_(User.email.like(f"%{f_any}%"), User.username.like(f"%{f_any}%")))
            elif expose_user_email:
                stmt = stmt.where(User.email.like(f"%{f_any}%"))
            elif expose_user_name:
                stmt = stmt.where(User.username.like(f"%{f_any}%"))
    if deleted:
        stmt = stmt.where(User.deleted == true())
    else:
        stmt = stmt.where(User.deleted == false())
    return session.scalars(stmt).all()


def _cleanup_nonprivate_user_roles(session, user, private_role_id):
    """
    Delete UserRoleAssociations EXCEPT FOR THE PRIVATE ROLE;
    Delete sharing roles that are associated with this user only;
    Remove user email from sharing role names associated with multiple users.

    Note: this method updates the session without flushing or committing.
    """
    user_roles = [ura for ura in user.roles if ura.role_id != private_role_id]
    for user_role_assoc in user_roles:
        role = user_role_assoc.role
        if role.type == Role.types.SHARING:
            if len(role.users) == 1:
                # This role is associated with this user only, so we can delete it
                session.delete(role)
            elif user.email in role.name:
                # Remove user email from sharing role's name
                role.name = role.name.replace(user.email, "[USER PURGED]")
                session.add(role)
        # Delete user role association
        session.delete(user_role_assoc)
