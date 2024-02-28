from galaxy import model as m
from galaxy.model.security import (
    get_npns_roles,
    get_private_user_role,
)
from . import verify_items

def test_get_npns_roles(session, make_role):
    make_role(deleted=True)
    make_role(type=m.Role.types.PRIVATE)
    make_role(type=m.Role.types.SHARING)
    r4 = make_role()
    r5 = make_role()

    roles = get_npns_roles(session).all()
    verify_items(roles, 2, (r4, r5))


def test_get_private_user_role(session, make_user, make_role, make_user_role_association):
    u1, u2 = make_user(), make_user()
    r1 = make_role(type=m.Role.types.PRIVATE)
    r2 = make_role(type=m.Role.types.PRIVATE)
    r3 = make_role()
    make_user_role_association(u1, r1)  # user1 private
    make_user_role_association(u1, r3)  # user1 non-private
    make_user_role_association(u2, r2)  # user2 private

    role = get_private_user_role(u1, session)
    assert role is r1
