from galaxy.managers import libraries as lib
from . import verify_items


def test_get_library_ids(session, make_library, make_library_permissions):
    l1, l2, l3, l4 = make_library(), make_library(), make_library(), make_library()
    make_library_permissions(library=l1, action="a")
    make_library_permissions(library=l2, action="b")
    make_library_permissions(library=l3, action="b")
    make_library_permissions(library=l3, action="b")  # intentional duplicate
    make_library_permissions(library=l4, action="c")

    ids = lib.get_library_ids(session, "b").all()
    verify_items(ids, 2, (l2.id, l3.id))


def test_get_library_permissions_by_role(session, make_role, make_library_permissions):
    r1, r2 = make_role(), make_role()
    make_library_permissions()
    make_library_permissions()
    make_library_permissions(role=r1)
    make_library_permissions(role=r2)
    lps = lib.get_library_permissions_by_role(session, (r1.id, r2.id)).all()

    lp_roles = [lp.role for lp in lps]
    verify_items(lp_roles, 2, (r1, r2))


def test_get_libraries_for_admins(session, make_library):
    libs = [make_library() for _ in range(5)]
    libs[0].deleted = True
    libs[1].deleted = True
    libs[2].deleted = False
    libs[3].deleted = False
    libs[4].deleted = False

    libs_deleted = lib.get_libraries_for_admins(session, True).all()
    verify_items(libs_deleted, 2, (libs[0], libs[1]))

    libs_not_deleted = lib.get_libraries_for_admins(session, False).all()
    verify_items(libs_not_deleted, 3, (libs[2], libs[3], libs[4]))

    libs_all = lib.get_libraries_for_admins(session, None).all()
    verify_items(libs_all, 5, libs)
    # TODO: verify sorted by lib name, case insensitive


def test_get_libraries_for_non_admins(session, make_library):
    libs = [make_library() for _ in range(6)]
    restricted_ids = (libs[0].id, libs[1].id, libs[2].id, libs[3].id)
    accessible_restricted_ids = (libs[2].id, libs[3].id)
    libs[3].deleted = True
    libs[4].deleted = True
    # Expected ids: 2 (accessible restricted, not deleted), 5 (not deleted)
    # Not returned: 1 (restricted), 3(deleted), 4(deleted)
    allowed = lib.get_libraries_for_nonadmins(session, restricted_ids, accessible_restricted_ids).all()
    verify_items(allowed, 2, (libs[2], libs[5]))
