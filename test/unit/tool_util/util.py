from contextlib import contextmanager
from os import environ

import pytest

external_dependency_management = pytest.mark.skipif(
    not environ.get("GALAXY_TEST_INCLUDE_SLOW"), reason="GALAXY_TEST_INCLUDE_SLOW not set"
)


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
