import os

import pytest

from ._util import assert_simple_file_realize

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "onedata_file_sources_conf.yml")

skip_if_no_onedata_access_token = pytest.mark.skipif(
    not os.environ.get("GALAXY_TEST_ONEDATA_PROVIDER_HOST") or not os.environ.get("GALAXY_TEST_ONEDATA_ACCESS_TOKEN"),
    reason="GALAXY_TEST_ONEDATA_PROVIDER_HOST and GALAXY_TEST_ONEDATA_ACCESS_TOKEN not set",
)


@skip_if_no_onedata_access_token
@pytest.mark.asyncio
async def test_file_source():
    await assert_simple_file_realize(FILE_SOURCES_CONF)
