import ipaddress

import pytest

from galaxy.exceptions import (
    AdminRequiredException,
    ConfigDoesNotAllowException,
    RequestParameterInvalidException,
)
from galaxy.files.uris import (
    validate_non_local,
    validate_uri_access,
)

LOOPBACK = ipaddress.ip_address("127.0.0.1")
LOOPBACK_NET = ipaddress.ip_network("127.0.0.0/24")
TEN_NET = ipaddress.ip_network("10.0.0.0/8")


@pytest.mark.usefixtures("fake_public_dns")
@pytest.mark.parametrize(
    "url",
    [
        "http://example.org",
        "https://example.org/path?q=1",
        "http://example.org:8080/x",
        "https://user:pw@example.org/",
        "http://user@example.org:8443/",
        "http://Example.ORG/",
        "https://bücher.example/",
        "https://xn--bcher-kva.example/",
        "https://BÜCHER.example:8443/",
        "http://example.org./",
    ],
)
def test_validate_non_local_public_host_passes(url):
    assert validate_non_local(url, []) == url


@pytest.mark.usefixtures("fake_public_dns")
@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "https://127.0.0.1/",
        "http://10.1.2.3/",
        "http://127.0.0.1:8080/x",
        "http://user:pw@127.0.0.1/",
        "http://user@127.0.0.1:8080/",
        "http://example.org@127.0.0.1/",
        " http://127.0.0.1/",
        "HTTP://127.0.0.1/",
        "HtTpS://127.0.0.1/",
    ],
)
def test_validate_non_local_private_address_rejected(url):
    with pytest.raises(ConfigDoesNotAllowException):
        validate_non_local(url, [])


@pytest.mark.usefixtures("fake_public_dns")
@pytest.mark.parametrize(
    "url, allowlist",
    [
        ("http://127.0.0.1/", [LOOPBACK]),
        ("http://127.0.0.1/", [LOOPBACK_NET]),
        ("http://127.0.0.1:8080/", [LOOPBACK]),
        ("http://user:pw@127.0.0.1/", [LOOPBACK_NET]),
        ("http://10.1.2.3/", [TEN_NET]),
        ("http://10.1.2.3/", [LOOPBACK, TEN_NET]),
    ],
)
def test_validate_non_local_allowlisted_private_address_passes(url, allowlist):
    assert validate_non_local(url, allowlist) == url


@pytest.mark.usefixtures("fake_public_dns")
@pytest.mark.parametrize(
    "url, allowlist",
    [
        ("http://10.1.2.3/", [LOOPBACK, LOOPBACK_NET]),
        ("http://127.0.0.1/", [TEN_NET]),
    ],
)
def test_validate_non_local_private_address_outside_allowlist_rejected(url, allowlist):
    with pytest.raises(ConfigDoesNotAllowException):
        validate_non_local(url, allowlist)


@pytest.mark.usefixtures("fake_public_dns")
@pytest.mark.parametrize(
    "url",
    [
        # Bracketed IPv6 literals reach getaddrinfo with their brackets and do not resolve.
        "http://[::1]/",
        "http://[::1]:8080/",
        "http://example.org:abc/",
    ],
)
def test_validate_non_local_unverifiable(url):
    with pytest.raises(RequestParameterInvalidException):
        validate_non_local(url, [])


@pytest.mark.parametrize(
    "uri",
    [
        "ftp://127.0.0.1/x",
        "file:///etc/hosts",
        "not a url",
        "",
        "127.0.0.1",
        "http",
        " HTTPS",
    ],
)
def test_validate_non_local_non_http_returned_unchanged(uri):
    assert validate_non_local(uri, []) == uri


@pytest.mark.usefixtures("fake_public_dns")
@pytest.mark.parametrize(
    "url, expected",
    [
        ("  http://example.org/a", "http://example.org/a"),
        ("\thttp://example.org/a", "http://example.org/a"),
        ("http://example.org/a ", "http://example.org/a "),
        ("http://example.org/a\n", "http://example.org/a\n"),
        ("http://example.org\r\n", "http://example.org\r\n"),
    ],
)
def test_validate_non_local_whitespace(url, expected):
    assert validate_non_local(url, []) == expected


@pytest.mark.usefixtures("fake_public_dns")
def test_validate_local_ip_access():
    assert validates_as_non_local("http://google.com", [])
    assert not validates_as_non_local("http://127.0.0.1/secrets.txt", [])
    assert validates_as_non_local("http://127.0.0.1/secrets.txt", [ipaddress.ip_address("127.0.0.1")])
    assert validates_as_non_local("http://127.0.0.1/secrets.txt", [ipaddress.ip_network("127.0.0.0/24")])
    assert not validates_as_non_local("http://127.0.0.1/secrets.txt", [ipaddress.ip_network("127.0.0.0/32")])
    assert validates_as_non_local(
        "http://127.0.0.1/secrets.txt", [ipaddress.ip_network("127.0.0.0/32"), ipaddress.ip_network("127.0.0.1/32")]
    )


@pytest.mark.usefixtures("fake_public_dns")
def test_validate():
    # Check the non local ip address checks from above...
    assert validates("http://google.com", False, [])
    assert not validates("http://127.0.0.1/secrets.txt", False, [])
    assert validates("http://127.0.0.1/secrets.txt", False, [ipaddress.ip_address("127.0.0.1")])
    assert validates("http://127.0.0.1/secrets.txt", False, [ipaddress.ip_network("127.0.0.0/24")])
    assert not validates("http://127.0.0.1/secrets.txt", False, [ipaddress.ip_network("127.0.0.0/32")])
    assert validates(
        "http://127.0.0.1/secrets.txt",
        False,
        [ipaddress.ip_network("127.0.0.0/32"), ipaddress.ip_network("127.0.0.1/32")],
    )

    # check that only admins can acess files...
    assert not validates("file://foo/bar", False, [])
    assert validates("file://foo/bar", True, [])


@pytest.mark.parametrize("uri", ["FILE:///x", " File://foo/bar"])
def test_validate_uri_access_file_requires_admin(uri):
    with pytest.raises(AdminRequiredException):
        validate_uri_access(uri, False, [])
    validate_uri_access(uri, True, [])


def validates_as_non_local(uri: str, allow_list):
    try:
        validate_non_local(uri, allow_list)
    except ConfigDoesNotAllowException:
        return False
    return True


def validates(uri: str, is_admin, allow_list):
    try:
        validate_uri_access(uri, is_admin, allow_list)
    except (ConfigDoesNotAllowException, AdminRequiredException):
        return False
    return True
