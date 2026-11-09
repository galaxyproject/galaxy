import unittest

import pytest


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item):
    try:
        return (yield)
    finally:
        # pytest keeps every test class instance referenced from its item until the
        # session ends (https://github.com/pytest-dev/pytest/issues/11374), so whatever
        # setup_method stored on self (often a whole mock Galaxy app) is never freed and
        # xdist workers grow by gigabytes over a unit test run. pytest already releases
        # unittest.TestCase instances itself. This is scoped to the unit tests because
        # other suites (e.g. the tool shed functional tests) keep using the first test
        # instance of a class through class-level helpers.
        cls = getattr(item, "cls", None)
        if cls is not None and not issubclass(cls, unittest.TestCase):
            item.instance.__dict__.clear()
