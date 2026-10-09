from galaxy.model.db.library import (
    get_libraries_by_name,
    get_libraries_for_admins,
    get_libraries_for_nonadmins,
    get_library_ids,
    get_library_permissions_by_role,
)
from . import have_same_elements


def test_get_library_ids(session, make_library, make_library_permissions):
    l1, l2, l3, l4 = make_library(), make_library(), make_library(), make_library()
    make_library_permissions(library=l1, action="a")
    make_library_permissions(library=l2, action="b")
    make_library_permissions(library=l3, action="b")
    make_library_permissions(library=l3, action="b")  # intentional duplicate
    make_library_permissions(library=l4, action="c")

    ids = get_library_ids(session, "b").all()
    expected = [l2.id, l3.id]
    have_same_elements(ids, expected)


def test_get_library_permissions_by_role(session, make_role, make_library_permissions):
    r1, r2 = make_role(), make_role()
    make_library_permissions()
    make_library_permissions()
    make_library_permissions(role=r1)
    make_library_permissions(role=r2)
    lps = get_library_permissions_by_role(session, (r1.id, r2.id)).all()

    lp_roles = [lp.role for lp in lps]
    expected = [r1, r2]
    have_same_elements(lp_roles, expected)


def test_get_libraries_for_admins(session, make_library):
    libs = [make_library() for _ in range(5)]
    libs[0].deleted = True
    libs[1].deleted = True
    libs[2].deleted = False
    libs[3].deleted = False
    libs[4].deleted = False

    libs_deleted = get_libraries_for_admins(session, True).all()
    expected = [libs[0], libs[1]]
    have_same_elements(libs_deleted, expected)

    libs_not_deleted = get_libraries_for_admins(session, False).all()
    expected = [libs[2], libs[3], libs[4]]
    have_same_elements(libs_not_deleted, expected)

    libs_all = get_libraries_for_admins(session, None).all()
    have_same_elements(libs_all, libs)


def test_get_libraries_for_admins__ordering(session, make_library):
    l1 = make_library(name="c")
    l2 = make_library(name="B")
    l3 = make_library(name="a")

    libs = get_libraries_for_admins(session, None).all()
    assert libs == [l3, l2, l1]  # sorted by name, case insensitive


def test_get_libraries_for_non_admins(session, make_library):
    l1, l2, l3, l4 = (make_library() for _ in range(4))
    restricted_ids = (l2.id, l3.id, l4.id)
    accessible_restricted_ids = (l2.id,)
    l2.deleted = False  # use default for l1.deleted
    l3.deleted = False
    l4.deleted = True

    allowed = get_libraries_for_nonadmins(session, restricted_ids, accessible_restricted_ids).all()
    # Expected:  l1 (not deleted, not restricted), l2 (not deleted, restricted but accessible)
    # Not returned: l3 (not deleted but restricted), l4 (deleted)
    expected = [l1, l2]
    have_same_elements(allowed, expected)


def test_get_libraries_for_admins_non_admins__ordering(session, make_library):
    l1 = make_library(name="c")
    l2 = make_library(name="B")
    l3 = make_library(name="a")

    expected = [l3, l2, l1]  # sorted by Library.name, case insensitive
    libs = get_libraries_for_admins(session, None).all()
    assert libs == expected
    libs = get_libraries_for_nonadmins(session, [], []).all()
    assert libs == expected


def test_get_libraries_by_name(session, make_library):
    make_library(name="a")
    l2 = make_library(name="b")
    l3 = make_library(name="b")  # intentional duplicate
    l3.deleted = True  # should not be returned

    libs = get_libraries_by_name(session, "b").all()
    assert libs == [l2]
