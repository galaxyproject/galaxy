import os

from ._util import assert_simple_file_realize, write_from, configured_file_sources

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "ssh_file_sources_conf.yml")


def test_file_source():
    assert_simple_file_realize(FILE_SOURCES_CONF, recursive=False, contains=False)


def test_file_write():
    fs = configured_file_sources(FILE_SOURCES_CONF)
    write_from(
        fs,
        uri="gxfiles://test1/aaa",
        content="???")
