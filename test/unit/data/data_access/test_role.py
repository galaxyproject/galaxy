from galaxy import model as m
from galaxy.model.security import get_npns_roles
from . import verify_items

def test_get_npns_roles(session, make_role):
    r1 = make_role(deleted=True)
    r2 = make_role(type=m.Role.types.PRIVATE)
    r3 = make_role(type=m.Role.types.SHARING)
    r4 = make_role()
    r5 = make_role()

    roles = get_npns_roles(session).all()
    verify_items(roles, 2, (r4, r5))
