import unittest

import pytest


def pytest_configure(config):
    try:
        import sqlalchemy.exc  # noqa: F401
    except ImportError:
        pass
    else:
        config.addinivalue_line("filterwarnings", "error::sqlalchemy.exc.SAWarning")


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item):
    try:
        return (yield)
    finally:
        # pytest keeps every test class instance referenced from its item until the
        # session ends (https://github.com/pytest-dev/pytest/issues/11374), so whatever
        # setup_method stored on self (often a whole mock Galaxy app) is never freed and
        # xdist workers grow by gigabytes over a unit test run. pytest already releases
        # unittest.TestCase instances itself.
        cls = getattr(item, "cls", None)
        if cls is not None and not issubclass(cls, unittest.TestCase):
            item.instance.__dict__.clear()
