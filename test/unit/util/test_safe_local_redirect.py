"""Tests for ``is_safe_local_redirect``, which guards post-login redirect targets.

These values reach Galaxy from a query string or a cookie, so the interesting cases are
all the spellings of "another origin" that a browser will happily resolve.
"""

import pytest

from galaxy.util import is_safe_local_redirect


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/tool_landings/1234-5678?public=true",
        "/histories/list#anchor",
        "/workflows/edit?id=abc&version=2",
        # a path that merely mentions a URL in its query string is still local
        "/authnz/cilogon/login?idphint=https://test.com",
    ],
)
def test_relative_paths_are_safe(path):
    assert is_safe_local_redirect(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "https://evil.example.com/",
        "http://evil.example.com/",
        "//evil.example.com/",
        "/\\evil.example.com/",
        "/\\\\evil.example.com/",
        # browsers strip tabs and newlines, turning these into "//evil.example.com"
        "/\t/evil.example.com",
        "/\n/evil.example.com",
        "/\r/evil.example.com",
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        # scheme-relative with leading whitespace a browser would trim
        " //evil.example.com",
        " /histories/list",
        "/histories/list ",
    ],
)
def test_anything_leaving_this_server_is_refused(path):
    assert is_safe_local_redirect(path) is False


@pytest.mark.parametrize("path", ["/foo\tbar", "/foo\nbar", "/foo\rbar", "/foo\x00bar", "/foo\x7fbar"])
def test_control_characters_are_refused_outright(path):
    """Accepting these would store a value that only fails later, when it is redirected to."""
    assert is_safe_local_redirect(path) is False


@pytest.mark.parametrize("path", [None, "", "histories/list", 42, ["/histories/list"], b"/histories/list"])
def test_empty_and_non_string_values_are_refused(path):
    assert is_safe_local_redirect(path) is False
