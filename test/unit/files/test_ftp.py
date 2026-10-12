import os

import pytest

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


def test_file_source_ftp_explicit_root():
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path("ftp://ftp.gnu.org/gnu/")

    assert file_source_pair.file_source.id == "test3"

    config = file_source_pair.file_source.template_config
    assert config.host == "ftp.gnu.org"
    assert config.root == "/gnu"


def test_file_source_ftp_path_in_host_backward_compat():
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path("ftp://ftp.ensemblgenomes.org/vol1/pub/")

    assert file_source_pair.file_source.id == "test4"

    config = file_source_pair.file_source.template_config
    assert config.host == "ftp.ensemblgenomes.org"
    assert config.root == "/vol1/pub/"


def test_file_source_ftp_protocol_prefixed_host():
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path("ftp://ftp.ncbi.nlm.nih.gov/pub/")

    assert file_source_pair.file_source.id == "test5"

    config = file_source_pair.file_source.template_config
    assert config.host == "ftp.ncbi.nlm.nih.gov"
    assert config.root == "/pub/"


def test_file_source_ftp_root_path_boundary():
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source = file_sources.get_file_source_path("ftp://ftp.gnu.org/gnu/").file_source
    config = file_source._evaluate_template_config()

    assert file_source._parse_url_and_get_path("ftp://ftp.gnu.org/gnu/file.txt", config) == "/file.txt"
    assert file_source._parse_url_and_get_path("ftp://ftp.gnu.org/gnu", config) == "/"
    # A path that starts with the root as a string prefix but not as a directory boundary
    # must not be stripped.
    assert file_source._parse_url_and_get_path("ftp://ftp.gnu.org/gnu-evil/file.txt", config) == "/gnu-evil/file.txt"


def test_file_source_ftp_root_rejects_traversal():
    from pydantic import ValidationError

    from galaxy.files.models import FileSourcePluginsConfig
    from galaxy.files.sources.ftp import FTPFileSourceConfiguration

    with pytest.raises(ValidationError, match="must not contain '\\.\\.'"):
        FTPFileSourceConfiguration(
            id="test", type="ftp", host="ftp.gnu.org", root="/gnu/../etc", file_sources_config=FileSourcePluginsConfig()
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
