from galaxy.model.db.user import (
    get_user_by_email,
    get_user_by_username,
)


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
