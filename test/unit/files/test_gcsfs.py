import os

import pytest

from ._util import assert_simple_file_realize

try:
    from fs_gcsfs import GCSFS
except ImportError:
    GCSFS = None

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "gcsfs_file_sources_conf.yml")


skip_if_no_gcsfs_libs = pytest.mark.skipif(
    not GCSFS, reason="Required lib to run gcs file source test: fs_gcsfs is not available"
)


@skip_if_no_gcsfs_libs
def test_file_source():
    assert_simple_file_realize(
        FILE_SOURCES_CONF, recursive=False, filename="README", contents="1000genomes", contains=True
    )
