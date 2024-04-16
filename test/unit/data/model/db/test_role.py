from galaxy.model import Role
from galaxy.model.db.role import get_npns_roles
from . import verify_items


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
    verify_items(roles, expected)
