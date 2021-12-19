import os

from galaxy.files import ConfiguredFileSources, ConfiguredFileSourcesConfig
from ._util import (
    assert_realizes_contains,
    find,
    user_context_fixture,
)
SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "gcsfs_file_sources_conf.yml")


def test_file_source():
    user_context = user_context_fixture()
    file_sources = _configured_file_sources()
    file_source_pair = file_sources.get_file_source_path("gxfiles://test1")

    assert file_source_pair.path == "/"
    file_source = file_source_pair.file_source
    res = file_source.list("/", recursive=False, user_context=user_context)
    readme_file = find(res, class_="File", name="README")
    assert readme_file

    assert_realizes_contains(file_sources, "gxfiles://test1/README", "1000genomes", user_context=user_context)


def _configured_file_sources(conf_file=FILE_SOURCES_CONF):
    file_sources_config = ConfiguredFileSourcesConfig()
    return ConfiguredFileSources(file_sources_config, conf_file=conf_file)
