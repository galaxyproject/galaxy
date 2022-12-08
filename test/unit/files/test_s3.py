import os

import pytest

from ._util import assert_simple_file_realize

pytest.importorskip("s3fs")

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "s3_file_sources_conf.yml")


def test_file_source():
    assert_simple_file_realize(
        FILE_SOURCES_CONF,
        recursive=False,
        filename="data_use_policies.txt",
        contents="DATA USE POLICIES",
        contains=True,
    )
