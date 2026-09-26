import os

import pytest

from ._util import (
    configured_file_sources,
    list_root,
    user_context_fixture,
)

try:
    from gcsfs import GCSFileSystem
except ImportError:
    GCSFileSystem = None

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "gcsfs_file_sources_conf.yml")


skip_if_no_gcsfs_libs = pytest.mark.skipif(
    not GCSFileSystem, reason="Required lib to run gcs file source test: gcsfs is not available"
)


@skip_if_no_gcsfs_libs
def test_file_source():
    """Test that we can list files from a public GCS bucket with anonymous access."""
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    res = list_root(file_sources, "gxfiles://test1", recursive=False, user_context=user_context)
    # Verify we got some results from the public bucket
    assert len(res) > 0, "Expected to find files/directories in the public GCS bucket"
