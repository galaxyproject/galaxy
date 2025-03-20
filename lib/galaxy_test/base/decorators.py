"""Test decorators for test methods meant to be run on external Galaxy instances.

These decorators should not be needed for integration tests, unit tests, etc... but
are appropriate for the API and Selenium tests that are meant to be executable on
external Galaxies.

Running this class of tests should implicitly come with the expectation that new
jobs, workflows, and datasets will be created. But tests creating new published objects,
histories, libraries, etc... should be annotated ideally.
"""

import os
import unittest
from functools import wraps
from typing import Union

import pytest
from typing_extensions import Literal

KnownRequirementT = Union[
    Literal["admin"],
    Literal["celery"],
    Literal["new_history"],
    Literal["new_library"],
    Literal["new_published_objects"],
    Literal["new_user"],
]


def has_requirement(method, tag: KnownRequirementT):
    try:
        # Skipping B009 (use of getattr with constant attribute) in
        # this next line because method may be a bound class method
        # and direct attribute access appends the class name and such.
        return tag in getattr(method, "__required_galaxy_features")  # noqa: B009
    except AttributeError:
        return False


def using_requirement(tag: KnownRequirementT):
    """At runtime, indicate we're using a Galaxy feature.

    This allows runtime test skips if the appropriate environment variable is set.
    """
    requirement = f"requires_{tag}"
    skip_environment_variable = f"GALAXY_TEST_SKIP_IF_{requirement.upper()}"
    if (env_value := os.environ.get(skip_environment_variable, "0")) != "0":
        raise unittest.SkipTest(f"[{env_value}] Skipping due to {skip_environment_variable} being set to {env_value}")


def _attach_requirements(method, tag: KnownRequirementT):
    requirement = f"requires_{tag}"
    if not hasattr(method, "__required_galaxy_features"):
        method.__required_galaxy_features = []
    method.__required_galaxy_features.append(tag)
    getattr(pytest.mark, requirement)(method)


def _wrap_method_with_galaxy_requirement(method, tag: KnownRequirementT):
    _attach_requirements(method, tag)

    @wraps(method)
    def wrapped_method(*args, **kwargs):
        using_requirement(tag)
        return method(*args, **kwargs)

    return wrapped_method


def requires_tool_id(tool_id: str):

    def method_wrapper(method):
        return pytest.mark.requires_tool_id(tool_id)(method)

    return method_wrapper


def requires_new_history(method):
    return _wrap_method_with_galaxy_requirement(method, "new_history")


def requires_new_user(method):
    method = _wrap_method_with_galaxy_requirement(method, "new_user")
    method = _wrap_method_with_galaxy_requirement(method, "admin")
    return method


def requires_new_library(method):
    method = _wrap_method_with_galaxy_requirement(method, "new_library")
    method = _wrap_method_with_galaxy_requirement(method, "admin")
    return method


def requires_new_published_objects(method):
    method = _wrap_method_with_galaxy_requirement(method, "new_published_objects")


def requires_admin(method):
    return _wrap_method_with_galaxy_requirement(method, "admin")


def requires_celery(method):
    return _wrap_method_with_galaxy_requirement(method, "celery")


__all__ = (
    "has_requirement",
    "requires_admin",
    "requires_celery",
    "requires_new_history",
    "requires_new_library",
    "requires_new_published_objects",
    "requires_new_user",
    "using_requirement",
)
