import ipaddress
import logging
import traceback

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


@pytest.mark.parametrize(
    "bad_url",
    [
        "https://.../SRR1957099.fastq.gz",
        "https://./foo",
        "https://..example.com/x",
        "https:///foo",
        "http:// /foo",
    ],
)
def test_validate_non_local_rejects_malformed_host(bad_url):
    with pytest.raises(RequestParameterInvalidException):
        validate_non_local(bad_url, [])


@pytest.mark.parametrize(
    "bad_url",
    [
        "https://user:secret@..example.com/x",
        "https://user:secret@example.org:notaport/x",
        "https://user:sec ret@..example.com/x",
        "https://example.org:notaport/a?next=ftp://user:secret@inner.example.org/b",
        "https://example.org:notaport/a?next=//user:secret@inner.example.org/b",
        "https://..example.com/a?next=ftp://user:secret@inner.example.org/b",
    ],
)
def test_validate_non_local_errors_hide_userinfo(bad_url, caplog):
    caplog.set_level(logging.DEBUG, logger="galaxy.files.uris")
    with pytest.raises(RequestParameterInvalidException) as exc_info:
        validate_non_local(bad_url, [])
    assert "secret" not in str(exc_info.value)
    assert "sec ret" not in str(exc_info.value)
    assert "secret" not in caplog.text
    assert "sec ret" not in caplog.text


def test_validate_non_local_parser_error_hides_userinfo(caplog):
    caplog.set_level(logging.DEBUG, logger="galaxy.files.uris")
    # urlparse() rejects this netloc with a ValueError that quotes it whole.
    bad_url = "https://user:secret@exa／mple.org/x"
    with pytest.raises(RequestParameterInvalidException) as exc_info:
        validate_non_local(bad_url, [])
    assert "secret" not in str(exc_info.value)
    assert exc_info.value.__cause__ is None
    assert exc_info.value.__context__ is None
    assert "secret" not in "".join(traceback.format_exception(exc_info.value))
    assert "secret" not in caplog.text


@pytest.mark.usefixtures("fake_public_dns")
def test_validate_non_local_strips_surrounding_whitespace():
    # Leading whitespace was already tolerated; trailing whitespace used to
    # slip through to getaddrinfo and raise an opaque error.
    assert validates_as_non_local("  http://google.com/x  ", [])
    assert validates_as_non_local("\thttp://google.com/x\n", [])


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
