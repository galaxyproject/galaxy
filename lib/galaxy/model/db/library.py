from sqlalchemy import (
    asc,
    false,
    func,
    not_,
    or_,
    select,
    true,
)

from galaxy.model import (
    Library,
    LibraryPermissions,
)


def get_library_ids(session, library_access_action):
    stmt = select(LibraryPermissions.library_id).where(LibraryPermissions.action == library_access_action).distinct()
    return session.scalars(stmt)


def get_library_permissions_by_role(session, role_ids):
    stmt = select(LibraryPermissions).where(LibraryPermissions.role_id.in_(role_ids))
    return session.scalars(stmt)


def get_libraries_for_admins(session, deleted):
    stmt = select(Library)
    if deleted is None:
        #  Flag is not specified, do not filter on it.
        pass
    elif deleted:
        stmt = stmt.where(Library.deleted == true())
    else:
        stmt = stmt.where(Library.deleted == false())
    stmt = stmt.order_by(asc(func.lower(Library.name)))
    return session.scalars(stmt)


def get_libraries_for_nonadmins(session, restricted_library_ids, accessible_restricted_library_ids):
    stmt = (
        select(Library)
        .where(Library.deleted == false())
        .where(
            or_(
                not_(Library.id.in_(restricted_library_ids)),
                Library.id.in_(accessible_restricted_library_ids),
            )
        )
    )
    stmt = stmt.order_by(asc(func.lower(Library.name)))
    return session.scalars(stmt)


def get_libraries_by_name(session, name):
    stmt = select(Library).where(Library.deleted == false()).where(Library.name == name)
    return session.scalars(stmt)
