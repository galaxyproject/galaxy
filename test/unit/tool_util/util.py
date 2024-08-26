import json
from contextlib import contextmanager
from os import environ
from typing import (
    Any,
    List,
)

import pytest

external_dependency_management = pytest.mark.external_dependency_management


def dict_verify_each(target_dict: dict, expectations: List[Any]):
    assert_json_encodable(target_dict)
    for path, expectation in expectations:
        exception = target_dict.get("exception")
        assert not exception, f"Test failed to generate with exception {exception}"
        dict_verify(target_dict, path, expectation)


def dict_verify(target_dict: dict, expectation_path: List[str], expectation: Any):
    rest = target_dict
    for path_part in expectation_path:
        rest = rest[path_part]
    assert rest == expectation, f"{rest} != {expectation} for {expectation_path}"


def assert_json_encodable(as_dict: dict):
    json.dumps(as_dict)


@contextmanager
def modify_environ(values, keys_to_remove=None):
    """
    Modify the environment for a test, adding/updating values in dict `values` and
    removing any environment variables mentioned in list `keys_to_remove`.
    """
    old_environ = environ.copy()
    try:
        if values:
            environ.update(values)
        if keys_to_remove:
            for key in keys_to_remove:
                if key in environ:
                    del environ[key]
        yield
    finally:
        environ.clear()
        environ.update(old_environ)
