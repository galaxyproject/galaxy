from galaxy.managers import users as lib
from galaxy.webapps.galaxy.services.users import get_users_for_index
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


def test_get_users_for_index(session, make_user):
    u1 = make_user(email="a", username="b")
    u2 = make_user(email="c", username="d")
    u3 = make_user(email="e", username="f")
    u4 = make_user(email="g", username="h")
    u5 = make_user(email="i", username="z")
    u6 = make_user(email="z", username="i")

    users = get_users_for_index(session, False, f_email="a", expose_user_email=True)
    verify_items(users, 1, [u1])
    users = get_users_for_index(session, False, f_email="c", is_admin=True)
    verify_items(users, 1, [u2])
    users = get_users_for_index(session, False, f_name="f", expose_user_name=True)
    verify_items(users, 1, [u3])
    users = get_users_for_index(session, False, f_name="h", is_admin=True)
    verify_items(users, 1, [u4])
    users = get_users_for_index(session, False, f_any="i", is_admin=True)
    verify_items(users, 2, [u5, u6])
    users = get_users_for_index(session, False, f_any="i", expose_user_email=True, expose_user_name=True)
    verify_items(users, 2, [u5, u6])
    users = get_users_for_index(session, False, f_any="i", expose_user_email=True)
    verify_items(users, 1, [u5])
    users = get_users_for_index(session, False, f_any="i", expose_user_name=True)
    verify_items(users, 1, [u6])

    u1.deleted = True
    users = get_users_for_index(session, True)
    verify_items(users, 1, [u1])


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
