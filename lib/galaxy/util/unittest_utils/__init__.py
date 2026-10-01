import os
import re
from datetime import datetime
from functools import wraps
from typing import (
    Callable,
    List,
    Optional,
    TypeVar,
    Union,
)
from unittest import SkipTest

import pytest
from typing_extensions import ParamSpec

from galaxy.util import requests
from galaxy.util.commands import which


def site_down_reason(url: str) -> Optional[str]:
    try:
        response = requests.get(url, timeout=10)
    except Exception as e:
        return f"request failed: {e}"
    if response.status_code == 200:
        return None
    if response.headers.get("cf-mitigated") == "challenge":
        return f"Cloudflare challenged the request (HTTP {response.status_code})"
    if response.headers.get("server") == "cloudflare":
        return f"Cloudflare returned HTTP {response.status_code}"
    return f"HTTP {response.status_code}"


def is_site_up(url: str) -> bool:
    return site_down_reason(url) is None


P = ParamSpec("P")
T = TypeVar("T")


def _failure_texts(exception: Exception) -> List[str]:
    texts = [str(exception)]
    # requests.HTTPError carries the response, whose body holds the server's error message.
    response_text = getattr(getattr(exception, "response", None), "text", None)
    if isinstance(response_text, str):
        texts.append(response_text)
    return texts


def skip_if_site_down(
    url: str, unavailable_pattern: Optional[str] = None
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Skip the test if ``url`` does not answer with HTTP 200.

    With ``unavailable_pattern``, a test that fails with an exception whose message or
    HTTP response body matches the pattern is skipped too; the pattern describes the
    errors the site produces when it is down or blocking requests.
    """

    def method_wrapper(method: Callable[P, T]) -> Callable[P, T]:
        @wraps(method)
        def wrapped_method(*args: P.args, **kwargs: P.kwargs) -> T:
            reason = site_down_reason(url)
            if reason:
                raise SkipTest(f"Test depends on [{url}] being up and it appears to be down ({reason}).")
            if unavailable_pattern is None:
                return method(*args, **kwargs)
            try:
                return method(*args, **kwargs)
            except Exception as e:
                for text in _failure_texts(e):
                    match = re.search(unavailable_pattern, text)
                    if match:
                        raise SkipTest(f"Test depends on [{url}] and it became unavailable: {match.group(0)}") from e
                raise

        return wrapped_method

    return method_wrapper


def skip_on_network_error(method: Callable[P, T]) -> Callable[P, T]:
    """Skip the test if it fails because a remote site could not be reached or timed out."""

    @wraps(method)
    def wrapped_method(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return method(*args, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            raise SkipTest(f"Test depends on a remote site that could not be reached: {e}") from e

    return wrapped_method


skip_if_github_down = skip_if_site_down("https://github.com/")
# Galaxy's TRS proxy reports these when WorkflowHub (or Cloudflare in front of it) is down or
# blocking requests, which happens to CI runners while the homepage check still passes.
skip_if_workflowhub_down = skip_if_site_down(
    "https://workflowhub.eu/",
    unavailable_pattern=(
        r"TRS server https://workflowhub\.eu "
        r"(responded with HTTP (403|429|5\d\d)|did not respond in time|could not be reached)"
    ),
)


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


# Pytest mark for tests that require a live LLM connection
# Set GALAXY_TEST_ENABLE_LIVE_LLM=1 to run these tests
pytestmark_live_llm = pytest.mark.skipif(
    not os.environ.get("GALAXY_TEST_ENABLE_LIVE_LLM"),
    reason="Live LLM tests disabled. Set GALAXY_TEST_ENABLE_LIVE_LLM=1 to enable.",
)


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
