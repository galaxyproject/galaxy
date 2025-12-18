import os
from datetime import datetime
from functools import wraps
from typing import (
    Callable,
    TypeVar,
    Union,
)
from unittest import SkipTest

import pytest
from typing_extensions import ParamSpec

from galaxy.util import requests
from galaxy.util.commands import which


def is_site_up(url: str) -> bool:
    try:
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except Exception:
        return False


P = ParamSpec("P")
T = TypeVar("T")


def skip_if_site_down(url: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def method_wrapper(method: Callable[P, T]) -> Callable[P, T]:
        @wraps(method)
        def wrapped_method(*args: P.args, **kwargs: P.kwargs) -> T:
            if not is_site_up(url):
                raise SkipTest(f"Test depends on [{url}] being up and it appears to be down.")
            return method(*args, **kwargs)

        return wrapped_method

    return method_wrapper


skip_if_github_down = skip_if_site_down("https://github.com/")


def _identity(func: Callable[P, T]) -> Callable[P, T]:
    return func


def skip_unless_executable(executable: str) -> Union[Callable[[Callable[P, T]], Callable[P, T]], pytest.MarkDecorator]:
    if which(executable):
        return _identity
    return pytest.mark.skip(f"PATH doesn't contain executable {executable}")


def skip_unless_environ(env_var: str) -> Union[Callable[[Callable[P, T]], Callable[P, T]], pytest.MarkDecorator]:
    if os.environ.get(env_var):
        return _identity

    return pytest.mark.skip(f"{env_var} must be set for this test")


def transient_failure(issue: int, potentially_fixed: bool = False) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Mark test as known transient failure with GitHub issue tracking.

    This decorator catches exceptions from tests and rewraps them with a marker
    indicating this is a known transient failure. This allows automated tooling
    to categorize failures and helps reviewers quickly identify flaky tests.

    Please create an issue on Github to track each transient failure.

    If a potential fix is implemented, set potentially_fixed=True to
    indicate that the failure may have been resolved. This will update the
    displayed error message and help us know if the issue can be potentially
    closed after a month of not being reported.

    Args:
        issue: GitHub issue number tracking this transient failure
        potentially_fixed: If True, indicates that the underlying issue may have been fixed,
            and the test failure comment will require the PR reviewer to report
            potential failures on the tracking issue and remove potentially_fixed.

    Example:
        @transient_failure(issue=12345)
        def test_flaky_selenium(self):
            # Test that sometimes fails due to race condition
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if potentially_fixed:
                    current_datetime = datetime.now().isoformat()
                    report_this = (
                        "We have previously implemented a potential fix for this issue, "
                        "if you are seeing this failure in CI on a recently branched commit, please report it on the tracking issue "
                        f"https://github.com/galaxyproject/galaxy/issues/{issue} including the comment "
                        f"'This issue is not fixed and was last seen at {current_datetime}' so we can mark the previous fix as insufficient."
                    )
                else:
                    report_this = "This is known issue and doesn't need to be reported."

                msg = f"KNOWN TRANSIENT FAILURE [Issue #{issue}] [{report_this}]: {str(e)}"
                # Try to preserve exception type, fallback to plain Exception
                try:
                    raise type(e)(msg) from e
                except (TypeError, AttributeError):
                    # type(e) doesn't accept single string arg
                    raise Exception(msg) from e

        return wrapper

    return decorator
