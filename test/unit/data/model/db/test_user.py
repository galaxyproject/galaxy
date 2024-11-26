import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from galaxy.model import (
    Role,
    UserRoleAssociation,
)
from galaxy.model.db.user import (
    _cleanup_nonprivate_user_roles,
    get_user_by_email,
    get_user_by_username,
    get_users_by_ids,
    get_users_for_index,
)
from . import have_same_elements


@pytest.fixture
def make_random_users(session, make_user):
    def f(count):
        return [make_user() for _ in range(count)]

    return f


def test_get_user_by_username(session, make_user):
    my_user = make_user(username="a")
    make_user()  # make another user
    make_user(email="other_username")  # make another user

    user = get_user_by_username(session, "a")
    assert user is my_user


def test_get_user_by_email(session, make_user):
    my_user = make_user(email="a@foo.bar")
    make_user(email="other_email")  # make another user

    user = get_user_by_email(session, "a@foo.bar")
    assert user is my_user


def test_get_users_by_ids(session, make_random_users):
    users = make_random_users(10)
    u1, u2, u3 = users[0], users[3], users[7]  # select some random users
    ids = [u1.id, u2.id, u3.id]

    users2 = get_users_by_ids(session, ids)
    expected = [u1, u2, u3]
    have_same_elements(users2, expected)


def test_get_users_for_index(session, make_user):
    u1 = make_user(email="a", username="b")
    u2 = make_user(email="c", username="d")
    u3 = make_user(email="e", username="f")
    u4 = make_user(email="g", username="h")
    u5 = make_user(email="i", username="z")
    u6 = make_user(email="z", username="i")

    users = get_users_for_index(session, False, f_email="a", expose_user_email=True)
    have_same_elements(users, [u1])
    users = get_users_for_index(session, False, f_email="c", is_admin=True)
    have_same_elements(users, [u2])
    users = get_users_for_index(session, False, f_name="f", expose_user_name=True)
    have_same_elements(users, [u3])
    users = get_users_for_index(session, False, f_name="h", is_admin=True)
    have_same_elements(users, [u4])
    users = get_users_for_index(session, False, f_any="i", is_admin=True)
    have_same_elements(users, [u5, u6])
    users = get_users_for_index(session, False, f_any="i", expose_user_email=True, expose_user_name=True)
    have_same_elements(users, [u5, u6])
    users = get_users_for_index(session, False, f_any="i", expose_user_email=True)
    have_same_elements(users, [u5])
    users = get_users_for_index(session, False, f_any="i", expose_user_name=True)
    have_same_elements(users, [u6])

    u1.deleted = True
    users = get_users_for_index(session, True)
    have_same_elements(users, [u1])


def test_username_is_unique(make_user):
    # Verify username model definition
    make_user(username="a")
    with pytest.raises(IntegrityError):
        make_user(username="a")


def test_cleanup_nonprivate_user_roles(session, make_user_and_role, make_role, make_user_role_association):
    # Create 3 users with private roles
    user1, role_private1 = make_user_and_role(email="user1@foo.com")
    user2, role_private2 = make_user_and_role(email="user2@foo.com")
    user3, role_private3 = make_user_and_role(email="user3@foo.com")

    # Create role_sharing1 and associated it with user1 and user2
    role_sharing1 = make_role(type=Role.types.SHARING, name="sharing role for user1@foo.com, user2@foo.com")
    make_user_role_association(user1, role_sharing1)
    make_user_role_association(user2, role_sharing1)

    # Create role_sharing2 and associated it with user3
    role_sharing2 = make_role(type=Role.types.SHARING, name="sharing role for user3@foo.com")
    make_user_role_association(user3, role_sharing2)

    # Create another role and associate it with all users
    role6 = make_role()
    make_user_role_association(user1, role6)
    make_user_role_association(user2, role6)
    make_user_role_association(user3, role6)

    # verify number of all user role associations
    associations = session.scalars(select(UserRoleAssociation)).all()
    assert len(associations) == 9  # 3 private, 2 + 1 sharing, 3 with role6

    # verify user1 roles
    assert len(user1.roles) == 3
    assert role_private1 in [ura.role for ura in user1.roles]
    assert role_sharing1 in [ura.role for ura in user1.roles]
    assert role6 in [ura.role for ura in user1.roles]

    # run cleanup on user user1
    _cleanup_nonprivate_user_roles(session, user1, role_private1.id)
    session.commit()  # must commit since method does not commit

    # private role not deleted, associations with role6 and with sharing role deleted, sharing role name updated
    assert len(user1.roles) == 1
    assert user1.roles[0].id == role_private1.id
    assert role_sharing1.name == "sharing role for [USER PURGED], user2@foo.com"

    # verify user2 roles
    assert len(user2.roles) == 3
    assert role_private2 in [ura.role for ura in user2.roles]
    assert role_sharing1 in [ura.role for ura in user2.roles]
    assert role6 in [ura.role for ura in user2.roles]

    # run cleanup on user user2
    _cleanup_nonprivate_user_roles(session, user2, role_private2.id)
    session.commit()

    # private role not deleted, association with sharing role deleted
    assert len(user2.roles) == 1
    assert user2.roles[0].id == role_private2.id
    # sharing role1 deleted since it has no more users associated with it
    roles = session.scalars(select(Role)).all()
    assert len(roles) == 5  # 3 private, role6, sharing2
    assert role_sharing1.id not in [role.id for role in roles]

    # verify user3 roles
    assert len(user3.roles) == 3
    assert role_private3 in [ura.role for ura in user3.roles]
    assert role_sharing2 in [ura.role for ura in user3.roles]
    assert role6 in [ura.role for ura in user3.roles]

    # run cleanup on user user3
    _cleanup_nonprivate_user_roles(session, user3, role_private3.id)
    session.commit()

    # remaining: 3 private roles + 3 associations, role6
    roles = session.scalars(select(Role)).all()
    assert len(roles) == 4
    associations = session.scalars(select(UserRoleAssociation)).all()
    assert len(associations) == 3
