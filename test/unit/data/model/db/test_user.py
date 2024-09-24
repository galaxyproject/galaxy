import pytest
from sqlalchemy.exc import IntegrityError

from galaxy.model.db.user import (
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
