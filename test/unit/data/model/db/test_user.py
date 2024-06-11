from galaxy.managers.users import (
    filter_out_invalid_username_characters,
    username_exists,
    username_from_email,
)
from galaxy.model import User


def test_username_from_email(session, make_user):
    make_user(username="foo")
    next_username = username_from_email(session, "foo@.foo.com", User)
    assert next_username == "foo-1"  # because foo exists

    make_user(username="foo-1")
    next_username = username_from_email(session, "foo@.foo.com", User)
    assert next_username == "foo-2"  # because foo and foo-1 exist

    make_user(username="foo-2")
    next_username = username_from_email(session, "foo@.foo.com", User)
    assert next_username == "foo-3"  # because foo and foo-1 and foo-2 exist

    next_username = username_from_email(session, "bar@.foo.com", User)
    assert next_username == "bar"  # no change


def test_filter_out_invalid_username_characters():
    username = "abcDCE123$%^-."
    assert filter_out_invalid_username_characters(username) == "abc---123----."


def test_username_exists(session, make_user):
    make_user(username="foo", email="foo@foo.com")
    assert username_exists(session, "foo")
    assert not username_exists(session, "bar")
