"""Tests for ``is_safe_local_redirect`` and ``is_safe_login_redirect``, which guard post-login redirect targets.

These values reach Galaxy from a query string or a cookie, so the interesting cases are
all the spellings of "another origin" that a browser will happily resolve.
"""

import pytest

from galaxy.util import (
    is_safe_local_redirect,
    is_safe_login_redirect,
)


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


ALLOWED_HOSTS = ["tools.example.org", "Portal.Example.org", "data.example.org:8443"]


@pytest.mark.parametrize(
    "target",
    [
        "https://tools.example.org/",
        "https://tools.example.org/landing?item=1#top",
        "https://TOOLS.example.org/landing",
        "https://tools.example.org:443/landing",
        "https://portal.example.org/back",
        "https://data.example.org:8443/back",
    ],
)
def test_allowlisted_hosts_are_safe_login_redirects(target):
    assert is_safe_login_redirect(target, ALLOWED_HOSTS) is True


@pytest.mark.parametrize(
    "target",
    [
        "https://evil.example.com/",
        "https://tools.example.org.evil.com/",
        "https://eviltools.example.org/",
        "https://tools.example.org:8443/",
        "https://data.example.org/",
        # only https may leave this server
        "http://tools.example.org/",
        "javascript://tools.example.org/%0aalert(1)",
        "javascript:alert(1)",
        "//tools.example.org/",
        "/\\tools.example.org/",
        "/\t/tools.example.org",
        "https:tools.example.org",
        "https:///tools.example.org",
        # userinfo and backslashes make parsers disagree about the host
        "https://tools.example.org@evil.com/",
        "https://user:pass@tools.example.org/",
        "https://evil.com\\@tools.example.org/",
        "https://tools.example.org\\.evil.com/",
        "https://evil.com#@tools.example.org",
        "https://tools.example.org:notaport/",
        "https://tools.example.org/\tpath",
        " https://tools.example.org/",
    ],
)
def test_other_hosts_are_refused_as_login_redirects(target):
    assert is_safe_login_redirect(target, ALLOWED_HOSTS) is False


@pytest.mark.parametrize(
    "target",
    [
        "/",
        "/histories/list",
        "https://tools.example.org/",
        "//evil.example.com/",
        "/\\evil.example.com/",
        "/\t/evil.example.com",
        "javascript:alert(1)",
        None,
        "",
        "histories/list",
    ],
)
def test_empty_allowlist_matches_safe_local_redirect(target):
    assert is_safe_login_redirect(target) is is_safe_local_redirect(target)
    assert is_safe_login_redirect(target, []) is is_safe_local_redirect(target)
