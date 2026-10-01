import os
import re
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


def is_site_up(url: str) -> bool:
    try:
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except Exception:
        return False


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
            if not is_site_up(url):
                raise SkipTest(f"Test depends on [{url}] being up and it appears to be down.")
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
# Quay's homepage can be available while API requests are rate-limited or fail during pagination.
skip_if_quay_down = skip_if_site_down(
    "https://quay.io/",
    unavailable_pattern=r"\b(?:429 Client|5\d\d Server) Error: [^\n]* for url: https://quay\.io/api/",
)
skip_if_workflowhub_down = skip_if_site_down("https://workflowhub.eu/")


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
