import os

import pytest

from ._util import (
    assert_realizes_contains,
    configured_file_sources,
    find,
    list_dir,
    list_root,
    user_context_fixture,
)

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
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    root = list_root(file_sources, "gxfiles://test1", recursive=False, user_context=user_context)
    assert find(root, class_="Directory", name="iris")
    iris = list_dir(file_sources, "gxfiles://test1/iris", recursive=False, user_context=user_context)
    assert find(iris, class_="File", name="iris.csv")
    assert_realizes_contains(file_sources, "gxfiles://test1/iris/iris.csv", "Iris-setosa", user_context=user_context)
