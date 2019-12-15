import unittest
from contextlib import contextmanager
from os import environ


def skip_unless_environ(var):
    if var in environ:
        return lambda func: func
    template = "Environment variable %s not found, dependent test skipped."
    return unittest.skip(template % var)


external_dependency_management = skip_unless_environ("GALAXY_TEST_INCLUDE_SLOW")


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
