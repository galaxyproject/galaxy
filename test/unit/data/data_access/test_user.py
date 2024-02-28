from galaxy.managers import users as lib
from . import verify_items


def test_get_user_by_username(session, make_user, make_random_users):
    make_random_users(3)
    my_user = make_user(username="a")

    user = lib.get_user_by_username(session, "a")
    assert user is my_user


def test_get_user_by_email(session, make_user, make_random_users):
    make_random_users(3)
    my_user = make_user(email="a@foo.bar")

    user = lib.get_user_by_email(session, "a@foo.bar")
    assert user is my_user


def test_get_users_by_ids(session, make_random_users):
    users = make_random_users(10)
    u1, u2, u3 = users[0], users[3], users[7]  # select some random users
    ids = [u1.id, u2.id, u3.id]

    users2 = lib.get_users_by_ids(session, ids)
    verify_items(users2, 3, (u1, u2, u3))


# TODO: factor out
# def test_get_users_by_role(session, make_user, make_role, make_user_role_association):
#    user1, user2, user3 = make_user(), make_user(), make_user()
#    role1, role2, role3 = make_role(), make_role(), make_role()
#    make_user_role_association(user1, role1)
#    make_user_role_association(user2, role1)
#    make_user_role_association(user2, role2)
#    make_user_role_association(user3, role2)
#
#    role1_users = lib.get_users_by_role(session, role1)
#    role2_users = lib.get_users_by_role(session, role2)
#    role3_users = lib.get_users_by_role(session, role3)
#    verify_items(role1_users, 2, (user1, user2))
#    verify_items(role2_users, 2, (user2, user3))
#    verify_items(role3_users, 0)


# TODO: factor out from model
# def test_email_exists(session, make_user):
#    make_user(email="a@foo.bar")
#    assert lib.email_exists(session, "a@foo.bar")
#    assert not lib.email_exists(session, "b@foo.bar")
