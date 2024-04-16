import pytest

from galaxy.model.db.user import (
    get_user_by_email,
    get_user_by_username,
    get_users_by_ids,
)
from . import verify_items


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
    verify_items(users2, expected)
