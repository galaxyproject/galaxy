import os
import shutil
import tempfile

import pytest
from whoosh import index

from tool_shed.util.shed_index import build_index

COMMUNITY_FILES_DIR = os.path.join(os.path.dirname(__file__), "data", "toolshed_community_files")


@pytest.fixture
def whoosh_index_dir():
    try:
        whoosh_index_dir = tempfile.mkdtemp(suffix="_whoosh_index_test")
        yield whoosh_index_dir
    finally:
        shutil.rmtree(whoosh_index_dir)


COMMUNITY_FILE_PATH = os.path.join(COMMUNITY_FILES_DIR, "database", "community_files")
COMMUNITY_DBURI = "sqlite:///{}".format(os.path.join(COMMUNITY_FILES_DIR, "database", "community.sqlite"))


def test_build_index(whoosh_index_dir):
    repos_indexed, tools_indexed = build_index(
        whoosh_index_dir,
        COMMUNITY_FILE_PATH,
        COMMUNITY_FILES_DIR,
        "repos/",
        COMMUNITY_DBURI,
    )
    assert repos_indexed == 1
    assert tools_indexed == 1
    idx = index.open_dir(whoosh_index_dir)
    assert idx.doc_count() == 1
    repos_indexed, tools_indexed = build_index(
        whoosh_index_dir,
        COMMUNITY_FILE_PATH,
        COMMUNITY_FILES_DIR,
        "repos/",
        COMMUNITY_DBURI,
    )
    assert repos_indexed == 0
    assert tools_indexed == 0
    idx = index.open_dir(whoosh_index_dir)
    assert idx.doc_count() == 1
    writer = idx.writer()
    writer.delete_by_term("id", 1)
    writer.commit()
    idx = index.open_dir(whoosh_index_dir)
    assert idx.doc_count() == 0
    repos_indexed, tools_indexed = build_index(
        whoosh_index_dir,
        COMMUNITY_FILE_PATH,
        COMMUNITY_FILES_DIR,
        "repos/",
        COMMUNITY_DBURI,
    )
    assert repos_indexed == 1
    assert tools_indexed == 1
