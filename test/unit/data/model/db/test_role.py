from galaxy.model import Role
from galaxy.model.db.role import (
    get_displayable_roles,
    get_npns_roles,
    get_private_role_user_emails_dict,
    get_private_user_role,
    get_roles_by_ids,
)
from galaxy.model.security import _get_valid_roles_exposed
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


def test_get_valid_roles_exposed(session, make_user_and_role, make_user, make_role, make_user_role_association):
    # Make 3 users with private roles
    (
        u1,
        rp1,
    ) = make_user_and_role(email="foo1@x.com")
    (
        u2,
        rp2,
    ) = make_user_and_role(email="foo2@x.com")
    (
        u3,
        rp3,
    ) = make_user_and_role(email="bar@x.com")

    # Make 2 sharing roles
    rs1 = make_role(type="sharing", name="sharing role for u1")
    make_user_role_association(user=u1, role=rs1)
    rs2 = make_role(type="sharing", name="sharing role for u2")
    make_user_role_association(user=u2, role=rs2)

    # Make 4 admin roles
    ra1 = make_role(type="admin", name="admin role1")
    make_user_role_association(user=u1, role=ra1)
    make_user_role_association(user=u2, role=ra1)
    ra2 = make_role(type="admin", name="admin role2")
    make_user_role_association(user=u1, role=ra2)
    make_user_role_association(user=u2, role=ra2)

    limit, page, page_limit = 1000, 1, 1000

    is_admin = True

    search_query = None
    roles = _get_valid_roles_exposed(session, search_query, is_admin, limit, page, page_limit)
    assert len(roles) == 7  # all roles returned

    search_query = "foo%"
    roles = _get_valid_roles_exposed(session, search_query, is_admin, limit, page, page_limit)
    assert len(roles) == 2
    assert rp1 in roles
    assert rp2 in roles

    search_query = "foo1%"
    roles = _get_valid_roles_exposed(session, search_query, is_admin, limit, page, page_limit)
    assert len(roles) == 1
    assert roles[0] == rp1

    search_query = "sharing%"
    roles = _get_valid_roles_exposed(session, search_query, is_admin, limit, page, page_limit)
    assert len(roles) == 2
    assert rs1 in roles
    assert rs2 in roles

    search_query = "sharing role for u1%"
    roles = _get_valid_roles_exposed(session, search_query, is_admin, limit, page, page_limit)
    assert len(roles) == 1
    assert roles[0] == rs1

    search_query = "admin role%"
    roles = _get_valid_roles_exposed(session, search_query, is_admin, limit, page, page_limit)
    assert len(roles) == 2
    assert ra1 in roles
    assert ra2 in roles

    search_query = "admin role1%"
    roles = _get_valid_roles_exposed(session, search_query, is_admin, limit, page, page_limit)
    assert len(roles) == 1
    assert roles[0] == ra1

    is_admin = False  # non admins should see only private roles

    search_query = None
    roles = _get_valid_roles_exposed(session, search_query, is_admin, limit, page, page_limit)
    assert len(roles) == 3

    search_query = "foo%"
    roles = _get_valid_roles_exposed(session, search_query, is_admin, limit, page, page_limit)
    assert len(roles) == 2
    assert rp1 in roles
    assert rp2 in roles

    search_query = "foo1%"
    roles = _get_valid_roles_exposed(session, search_query, is_admin, limit, page, page_limit)
    assert len(roles) == 1
    assert roles[0] == rp1

    search_query = "sharing%"
    roles = _get_valid_roles_exposed(session, search_query, is_admin, limit, page, page_limit)
    assert len(roles) == 0

    search_query = "admin role%"
    roles = _get_valid_roles_exposed(session, search_query, is_admin, limit, page, page_limit)
    assert len(roles) == 0


def test_get_displayable_roles(session, make_role, make_user_and_role):
    # make users with private roles
    user1, private_role1 = make_user_and_role(email="user1@example.com")
    user2, private_role2 = make_user_and_role(email="user2@example.com")
    # make 2 non-private roles, one is deleted, so it should not be returned
    admin_role1 = make_role(type="admin", name="admin-role-1", description="Description of admin-role1")
    make_role(type="admin", description="Description of admin-role1", deleted=True)

    user_is_admin, security_agent = True, None
    roles = get_displayable_roles(session, user1, user_is_admin, security_agent)
    assert len(roles) == 3
    assert roles[0].id == private_role1.id
    assert roles[1].id == private_role2.id
    assert roles[2].id == admin_role1.id
    assert roles[0].name == "private role"
    assert roles[1].name == "private role"
    assert roles[2].name == "admin-role-1"


def test_get_private_role_user_emails_dict(session, make_role, make_user_and_role):
    # make users with private roles
    user1, private_role1 = make_user_and_role(email="user1@example.com")
    user2, private_role2 = make_user_and_role(email="user2@example.com")
    user3, private_role3 = make_user_and_role(email="user3@example.com")
    # make 2 non-private roles
    make_role(type="admin", name="admin-role-1", description="Description of admin-role1")
    make_role(type="admin", name="admin-role-2", description="Description of admin-role2")

    data = get_private_role_user_emails_dict(session)
    assert len(data) == 3  # only private role mappings are returned
    assert data[private_role1.id] == "user1@example.com"
    assert data[private_role2.id] == "user2@example.com"
    assert data[private_role3.id] == "user3@example.com"
