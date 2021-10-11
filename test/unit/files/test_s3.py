import os

import pytest

from galaxy.files import ConfiguredFileSources, ConfiguredFileSourcesConfig
from ._util import (
    assert_realizes_contains,
    find,
    user_context_fixture,
)
SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "s3_file_sources_conf.yml")

skip_if_not_slow = pytest.mark.skipif(
    not os.environ.get('GALAXY_TEST_INCLUDE_SLOW'),
    reason="GALAXY_TEST_INCLUDE_SLOW not set"
)


@skip_if_not_slow
def test_file_source():
    user_context = user_context_fixture()
    file_sources = _configured_file_sources()
    file_source_pair = file_sources.get_file_source_path("gxfiles://test1")

    assert file_source_pair.path == "/"
    file_source = file_source_pair.file_source
    res = file_source.list("/", recursive=False, user_context=user_context)
    print(res)
    dup = find(res, "File", "data_use_policies.txt")
    assert dup

    assert_realizes_contains(file_sources, "gxfiles://test1/data_use_policies.txt", "DATA USE POLICIES", user_context=user_context)


def _configured_file_sources(conf_file=FILE_SOURCES_CONF):
    file_sources_config = ConfiguredFileSourcesConfig()
    return ConfiguredFileSources(file_sources_config, conf_file=conf_file)
