import os

from galaxy.datatypes import sniff
from galaxy.files import ConfiguredFileSourcesConfig
from galaxy.files.unittest_utils import (
    setup_root,
    TestConfiguredFileSources,
    write_file_fixtures,
)


def test_posix():
    file_sources = _configured_file_sources()
    as_dict = file_sources.to_dict()
    assert len(as_dict["file_sources"]) == 1
    file_source_as_dict = as_dict["file_sources"][0]
    assert file_source_as_dict["uri_root"] == "gxfiles://test1"

    _download_and_check_file(file_sources)


def _download_and_check_file(file_sources):
    tmp_name = sniff.stream_url_to_file("gxfiles://test1/a", file_sources=file_sources)
    try:
        a_contents = open(tmp_name).read()
        assert a_contents == "a\n"
    finally:
        os.remove(tmp_name)


def _configured_file_sources() -> TestConfiguredFileSources:
    tmp, root = setup_root()
    file_sources_config = ConfiguredFileSourcesConfig()
    plugin = {
        "type": "posix",
    }
    plugin["root"] = root
    write_file_fixtures(tmp, root)
    file_sources = TestConfiguredFileSources(file_sources_config, conf_dict={"test1": plugin}, test_root=root)
    return file_sources
