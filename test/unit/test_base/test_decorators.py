import os
import unittest

import pytest

from galaxy_test.base.decorators import (
    has_requirement,
    requires_admin,
    requires_celery,
    requires_new_history,
    requires_new_library,
    requires_new_published_objects,
    requires_new_user,
)


@requires_admin
@requires_new_history
def foo():
    # test metadata available from inside of function
    assert has_requirement(foo, "admin")
    assert has_requirement(foo, "new_history")
    assert "requires_admin" in [m.name for m in foo.pytestmark]
    assert "requires_new_history" in [m.name for m in foo.pytestmark]


def test_foo():
    # test metadata available from inside of function
    assert has_requirement(foo, "admin")
    assert has_requirement(foo, "new_history")
    assert "requires_admin" in [m.name for m in foo.pytestmark]
    assert "requires_new_history" in [m.name for m in foo.pytestmark]

    # fun tests from inside of foo
    foo()


class FooClass:
    @requires_admin
    @requires_new_history
    def foo(self):
        assert has_requirement(self.foo, "admin")
        assert has_requirement(self.foo, "new_history")
        assert "requires_admin" in [m.name for m in self.foo.pytestmark]
        assert "requires_new_history" in [m.name for m in self.foo.pytestmark]


def test_foo_class_methods():
    test_class = FooClass()
    foo = test_class.foo

    assert has_requirement(foo, "admin")
    assert has_requirement(foo, "new_history")
    assert "requires_admin" in [m.name for m in foo.pytestmark]
    assert "requires_new_history" in [m.name for m in foo.pytestmark]

    foo()


# Uncomment and run pytest to ensure the unittest.SkipTest actually skips
# def test_pytest_skips_this_should_be_skipped():
#    os.environ["GALAXY_TEST_SKIP_IF_REQUIRES_ADMIN"] = "1"
#    foo()
#    del os.environ["GALAXY_TEST_SKIP_IF_REQUIRES_ADMIN"]


def test_skipping_foo():
    os.environ["GALAXY_TEST_SKIP_IF_REQUIRES_ADMIN"] = "1"
    skip_raised = False
    try:
        foo()
    except unittest.SkipTest:
        skip_raised = True
    assert skip_raised
    del os.environ["GALAXY_TEST_SKIP_IF_REQUIRES_ADMIN"]


@requires_new_library
def library_func():
    pass


def test_requires_new_library_implies_requires_admin():
    assert has_requirement(library_func, "admin")
    assert has_requirement(library_func, "new_library")


@requires_new_user
def user_func():
    pass


def test_requires_new_user_implies_requires_admin():
    assert has_requirement(user_func, "admin")
    assert has_requirement(user_func, "new_user")


@pytest.mark.parametrize(
    "decorator,requirement",
    [
        (requires_admin, "admin"),
        (requires_new_history, "new_history"),
        (requires_new_library, "new_library"),
        (requires_new_user, "new_user"),
        (requires_celery, "celery"),
        (requires_new_published_objects, "new_published_objects"),
    ],
)
@pytest.mark.parametrize("skip_value", [None, "0", "1"])
def test_requirement_preserves_callable_and_skips(monkeypatch, decorator, requirement, skip_value):
    calls = []

    def method(value):
        calls.append(value)
        return value

    decorated = decorator(method)
    assert callable(decorated)
    assert decorated.__name__ == method.__name__
    monkeypatch.delenv("GALAXY_TEST_SKIP_IF_REQUIRES_ADMIN", raising=False)
    variable = f"GALAXY_TEST_SKIP_IF_REQUIRES_{requirement.upper()}"
    if skip_value is None:
        monkeypatch.delenv(variable, raising=False)
    else:
        monkeypatch.setenv(variable, skip_value)
    if skip_value == "1":
        with pytest.raises(unittest.SkipTest):
            decorated("result")
        assert calls == []
    else:
        assert decorated("result") == "result"
        assert calls == ["result"]
