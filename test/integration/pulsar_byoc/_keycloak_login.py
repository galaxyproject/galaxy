"""Drive Keycloak's HTML login form so e2e tests can complete an OIDC sign-in.

Keycloak's login page contains a ``<form action="...">`` whose URL embeds the
session state. We GET the page, parse out the action URL, then POST username
+ password to it. Keycloak responds with a 302 redirect to the relay's
configured ``redirect_uri`` carrying ``code=`` + ``state=``.

Cookies: Keycloak unconditionally sets its session cookies with
``Secure; SameSite=None``, which httpx's stdlib-backed cookie jar refuses to
send over plain HTTP (and Python's cookielib mis-stores cookies for the
single-label ``localhost`` host under a ``localhost.local`` bucket). For a
test rig that's intentionally talking HTTP to a dev-mode Keycloak, the
correct fix is to bypass the jar entirely: capture every ``Set-Cookie`` from
the redirect chain and pass them through verbatim on the form POST.
"""

from __future__ import annotations

import re
from html import unescape
from http.cookies import SimpleCookie

import httpx

_FORM_ACTION_RE = re.compile(
    r'<form[^>]*\bid=["\']kc-form-login["\'][^>]*\baction=["\']([^"\']+)["\']',
    re.IGNORECASE | re.DOTALL,
)


def _extract_form_action(html: str) -> str:
    match = _FORM_ACTION_RE.search(html)
    if not match:
        raise RuntimeError("could not find Keycloak login form action URL in HTML")
    return unescape(match.group(1))


def _absolute(base: str, location: str) -> str:
    if location.startswith("http://") or location.startswith("https://"):
        return location
    if location.startswith("/"):
        from urllib.parse import urlsplit

        s = urlsplit(base)
        return f"{s.scheme}://{s.netloc}{location}"
    return location


def _walk_redirects_capturing_cookies(
    client: httpx.Client, start_url: str, max_hops: int = 10
) -> tuple[httpx.Response, dict[str, str]]:
    """Walk redirects manually, accumulating ``Set-Cookie`` values into a dict.

    Returns the terminal (non-redirect) response and the accumulated cookies.
    Bypasses httpx's cookie jar so secure-flag / path / domain rules don't
    drop cookies in the HTTP-localhost test environment.
    """
    cookies: dict[str, str] = {}
    url = start_url
    for _ in range(max_hops):
        headers = {"Cookie": _format_cookie_header(cookies)} if cookies else {}
        resp = client.get(url, headers=headers)
        for raw in resp.headers.get_list("set-cookie"):
            for name, morsel in SimpleCookie(raw).items():
                cookies[name] = morsel.value
        if resp.status_code in (301, 302, 303, 307, 308):
            url = _absolute(url, resp.headers["location"])
            continue
        return resp, cookies
    raise RuntimeError(f"too many redirects starting at {start_url}")


def _format_cookie_header(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


def login_via_keycloak(
    *,
    authorization_url: str,
    username: str,
    password: str,
    follow_relay_callback: bool = False,
) -> httpx.Response:
    """Walk the auth-code flow through Keycloak and return the final response.

    ``authorization_url`` is the URL the relay redirected the operator to
    (i.e. the ``Location`` header of ``GET /auth/oidc/keycloak/login``).

    By default we stop at the redirect *out* of Keycloak (so the caller can
    inspect the ``Location`` header to extract ``code`` + ``state``). With
    ``follow_relay_callback=True`` we also follow into the relay's callback
    and return its response.
    """
    with httpx.Client(timeout=10.0, follow_redirects=False) as client:
        # 1. Walk redirects to the login page, capturing all cookies.
        login_page, cookies = _walk_redirects_capturing_cookies(client, authorization_url)
        if login_page.status_code != 200:
            raise RuntimeError(
                f"Expected Keycloak login page, got HTTP {login_page.status_code}: {login_page.text[:200]!r}"
            )
        action_url = _extract_form_action(login_page.text)

        # 2. POST credentials with the accumulated cookies.
        submit = client.post(
            action_url,
            data={
                "username": username,
                "password": password,
                "credentialId": "",
            },
            headers={"Cookie": _format_cookie_header(cookies)},
        )
        # Capture any new cookies set by the form submission too.
        for raw in submit.headers.get_list("set-cookie"):
            for name, morsel in SimpleCookie(raw).items():
                cookies[name] = morsel.value
        if submit.status_code not in (302, 303):
            raise RuntimeError(
                f"Unexpected response from Keycloak login form: {submit.status_code} {submit.text[:300]!r}"
            )
        if follow_relay_callback:
            cb_url = _absolute(action_url, submit.headers["location"])
            return client.get(
                cb_url,
                headers={"Cookie": _format_cookie_header(cookies)},
            )
        return submit


def code_and_state_from_callback(location: str) -> tuple[str, str]:
    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(location)
    qs = parse_qs(parsed.query)
    if "code" not in qs or "state" not in qs:
        raise RuntimeError(f"Callback URL missing code/state: {location}")
    return qs["code"][0], qs["state"][0]


__all__ = ["login_via_keycloak", "code_and_state_from_callback"]
