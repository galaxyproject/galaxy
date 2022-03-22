from os import environ
from typing import Dict

import pytest

from .util import modify_environ


@pytest.fixture
def load_keyval(request):
    """
    Create key/value pair and load it into os.environ. Delete on teardown.
    """
    keys = []  # preserve keys for teardown

    def _load_keyval(key="a unique key", val="a value"):
        # If this is called twice with default values within the same test function,
        #   it will raise a KeyError. This is intentional: os.environ cannot have duplicate keys.
        keys.append(key)
        environ[key] = val
        return key, val

    def _teardown():
        for k in keys:
            del environ[k]

    request.addfinalizer(_teardown)
    return _load_keyval


def test_modify_environ__restore(load_keyval):
    key, val = load_keyval()
    with modify_environ({}):
        assert environ[key] == val  # key/val unchanged
    assert environ[key] == val  # key/val unchanged


def test_modify_environ__add_and_restore(load_keyval):
    key1, val1 = load_keyval()
    key2, val2 = "key to add", "value to add"
    to_update = {key2: val2}

    assert key2 not in environ  # ensure key to add does not exist
    with modify_environ(to_update):
        assert environ[key1] == val1  # key/val unchanged
        assert environ[key2] == val2  # new key/val added
    assert environ[key1] == val1  # key/val unchanged
    assert key2 not in environ  # new key removed


def test_modify_environ__update_and_restore(load_keyval):
    key1, val1 = load_keyval()
    key2, val2 = load_keyval("key to update", "value to update")
    val2_updated = "updated"
    to_update = {key2: val2_updated}

    with modify_environ(to_update):
        assert environ[key1] == val1  # key/val unchanged
        assert environ[key2] == val2_updated  # value updated
    assert environ[key1] == val1  # key/val unchanged
    assert environ[key2] == val2  # value restored


def test_modify_environ__remove_and_restore(load_keyval):
    key1, val1 = load_keyval()
    key2, val2 = load_keyval("key to remove", "value to remove")
    to_update: Dict[str, str] = {}
    to_remove = [key2]

    with modify_environ(to_update, to_remove):
        assert environ[key1] == val1  # key/val unchanged
        assert key2 not in environ  # key removed
    assert environ[key1] == val1  # key/val unchanged
    assert environ[key2] == val2  # key/value restored


def test_modify_environ__remove_nonexistant_key(load_keyval):
    # Test that removing wrong key does not raise an error
    key1, val1 = load_keyval()
    key_nonexistant = "no such key"
    to_update: Dict[str, str] = {}
    to_remove = [key_nonexistant]

    assert key_nonexistant not in environ  # ensure key to remove does not exist
    with modify_environ(to_update, to_remove):
        assert environ[key1] == val1  # key/val unchanged
    assert environ[key1] == val1  # key/val unchanged
