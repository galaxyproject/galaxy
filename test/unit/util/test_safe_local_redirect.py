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


# Keep these vectors in step with client/src/utils/redirect.test.ts, which checks safeLoginRedirect.
ALLOWED_HOSTS = ["tools.example.org", "data.example.org:8443", "[2001:db8::1]"]


@pytest.mark.parametrize(
    "target",
    [
        "https://tools.example.org/landing",
        "https://TOOLS.example.org/landing",
        "https://tools.example.org:443/landing",
        "https://data.example.org:8443/back",
        "https://[2001:db8::1]/back",
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
        # spellings a browser normalizes to an allowed host
        "https://tools\uff0eexample\uff0eorg/",
        "https://tools%2eexample.org/",
        "https://tools.example.org:8443/",
        "https://data.example.org/",
        "http://tools.example.org/",
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
        "https://tools.example.org/landing",
        "https://tools.example.org:443/landing",
        "https://[2001:db8::1]/back",
    ],
)
def test_allowlist_entries_may_name_the_default_port(target):
    assert is_safe_login_redirect(target, ["Tools.Example.org:443", "[2001:DB8::1]:443"]) is True


def test_no_external_login_redirects_without_allowlist():
    assert is_safe_login_redirect("https://tools.example.org/") is False


BASE_URL = "https://galaxy.example/galaxy/"


@pytest.mark.parametrize(
    "target",
    ["https://galaxy.example/other", "https://GALAXY.example:443/galaxy/x", "https://tools.example.org/back"],
)
def test_absolute_urls_back_to_base_url_are_safe_login_redirects(target):
    assert is_safe_login_redirect(target, ["tools.example.org"], base_url=BASE_URL) is True


@pytest.mark.parametrize(
    "target",
    [
        "http://galaxy.example/galaxy/x",
        "https://galaxy.example:8443/galaxy/x",
        "https://user@galaxy.example/galaxy/x",
        "https://evil.example.com\\@galaxy.example/",
        " https://galaxy.example/galaxy/x",
        "https://galaxy.example/galaxy/\tx",
        "https://[galaxy.example/",
    ],
)
def test_base_url_shares_the_ambiguous_url_refusals(target):
    assert is_safe_login_redirect(target, base_url=BASE_URL) is False
