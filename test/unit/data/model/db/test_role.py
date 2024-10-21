from galaxy.model import Role
from galaxy.model.db.role import (
    get_npns_roles,
    get_private_user_role,
    get_roles_by_ids,
)
from . import have_same_elements


def test_get_npns_roles(session, make_role):
    make_role(deleted=True)
    make_role(type=Role.types.PRIVATE)
    make_role(type=Role.types.SHARING)
    r4 = make_role()
    r5 = make_role()

    roles = get_npns_roles(session).all()
    # Expected: r4, r5
    # Not returned: r1: deleted, r2: private, r3: sharing
    expected = [r4, r5]
    have_same_elements(roles, expected)


def test_get_private_user_role(session, make_user, make_role, make_user_role_association):
    u1, u2 = make_user(), make_user()
    r1 = make_role(type=Role.types.PRIVATE)
    r2 = make_role(type=Role.types.PRIVATE)
    r3 = make_role()
    make_user_role_association(u1, r1)  # user1 private
    make_user_role_association(u1, r3)  # user1 non-private
    make_user_role_association(u2, r2)  # user2 private

    role = get_private_user_role(u1, session)
    assert role is r1


def test_get_roles_by_ids(session, make_role):
    roles = [make_role() for _ in range(10)]  # create roles
    r1, r2, r3 = roles[0], roles[3], roles[7]  # select some random roles
    ids = [r1.id, r2.id, r3.id]

    roles2 = get_roles_by_ids(session, ids)
    expected = [r1, r2, r3]
    have_same_elements(roles2, expected)
