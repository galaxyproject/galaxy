import os

import pytest

from galaxy.files import ConfiguredFileSources, ConfiguredFileSourcesConfig
from ._util import (
    assert_realizes_as,
    find_file_a,
    user_context_fixture,
)
SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "googledrive_file_sources_conf.yml")

skip_if_no_google_drive_access_token = pytest.mark.skipif(
    not os.environ.get('GALAXY_TEST_GOOGLE_DRIVE_ACCESS_TOKEN')
    and os.environ.get('GALAXY_TEST_GOOGLE_DRIVE_REFRESH_TOKEN')
    and os.environ.get('GALAXY_TEST_GOOGLE_DRIVE_CLIENT_ID')
    and os.environ.get('GALAXY_TEST_GOOGLE_DRIVE_CLIENT_SECRET'),
    reason="GALAXY_TEST_GOOGLE_DRIVE_ACCESS_TOKEN not set"
)


@skip_if_no_google_drive_access_token
def test_file_source():
    user_context = user_context_fixture()
    file_sources = _configured_file_sources()
    file_source_pair = file_sources.get_file_source_path("gxfiles://test1")

    assert file_source_pair.path == "/"
    file_source = file_source_pair.file_source
    res = file_source.list("/", recursive=True, user_context=user_context)
    a_file = find_file_a(res)
    assert a_file

    assert_realizes_as(file_sources, "gxfiles://test1/a", "a\n", user_context=user_context)


def _configured_file_sources(conf_file=FILE_SOURCES_CONF):
    file_sources_config = ConfiguredFileSourcesConfig()
    return ConfiguredFileSources(file_sources_config, conf_file=conf_file)
