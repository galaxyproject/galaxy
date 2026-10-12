import os

from ._util import (
    assert_realizes_contains,
    configured_file_sources,
    user_context_fixture,
)
from .conftest import FtpServerFixture

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "ftp_file_sources_conf.yml")


def test_file_source_ftp_specific_url_routing():
    test_url = "ftp://ftp.gnu.org/README"
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path(test_url)

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test1"


def test_file_source_ftp_specific(ftp_server: FtpServerFixture):
    (ftp_server.root / "README").write_text("Served by the host specific file source.\n")
    test_url = f"ftp://{ftp_server.host}:{ftp_server.port}/README"
    user_context = user_context_fixture()
    file_sources = configured_file_sources(
        [
            {
                "type": "ftp",
                "id": "test1",
                "doc": "A specific ftp url handler",
                "host": ftp_server.host,
                "port": ftp_server.port,
            },
            {
                "type": "ftp",
                "id": "test2",
                "doc": "A default ftp handler, built-in and not needed other than for tests",
            },
        ]
    )
    file_source_pair = file_sources.get_file_source_path(test_url)

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test1"

    assert_realizes_contains(
        file_sources,
        test_url,
        "Served by the host specific file source.",
        user_context=user_context,
    )


def test_file_source_ftp_generic(ftp_server: FtpServerFixture):
    (ftp_server.root / "welcome.msg").write_text("Served by the generic file source.\n")
    test_url = f"ftp://{ftp_server.host}:{ftp_server.port}/welcome.msg"
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path(test_url)

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test2"

    assert_realizes_contains(
        file_sources,
        test_url,
        "Served by the generic file source.",
        user_context=user_context,
    )


def test_file_source_ftp_host_specific_not_matched_by_port_prefix():
    file_sources = configured_file_sources(
        [
            {
                "type": "ftp",
                "id": "test1",
                "doc": "A specific ftp url handler",
                "host": "ftp.example.org",
                "port": 21,
                "user": "alice",
                "passwd": "secret",
            },
            {
                "type": "ftp",
                "id": "test2",
                "doc": "A default ftp handler, built-in and not needed other than for tests",
            },
        ]
    )

    assert file_sources.get_file_source_path("ftp://ftp.example.org:21/README").file_source.id == "test1"
    assert file_sources.get_file_source_path("ftp://ftp.example.org/README").file_source.id == "test1"
    # The credentials configured for port 21 must not be sent to another port on the same host.
    assert file_sources.get_file_source_path("ftp://ftp.example.org:2121/README").file_source.id == "test2"
