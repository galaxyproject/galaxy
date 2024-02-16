import os
import shutil
import tarfile
import tempfile
from collections import namedtuple
from io import BytesIO

import pytest
import requests
from whoosh import index

from tool_shed.util.shed_index import build_index

URL = "https://github.com/mvdbeek/toolshed-test-data/blob/master/toolshed_community_files.tgz?raw=true"


@pytest.fixture
def whoosh_index_dir():
    try:
        whoosh_index_dir = tempfile.mkdtemp(suffix="_whoosh_index_test")
        yield whoosh_index_dir
    finally:
        shutil.rmtree(whoosh_index_dir)


@pytest.fixture(scope="module")
def community_file_dir():
    extracted_archive_dir = tempfile.mkdtemp()
    b = BytesIO(requests.get(URL).content)
    tarfile.open(fileobj=b, mode="r:gz").extractall(extracted_archive_dir)
    try:
        yield extracted_archive_dir
    finally:
        shutil.rmtree(extracted_archive_dir)


@pytest.fixture()
def community_file_structure(community_file_dir):
    community = namedtuple("community", "file_path hgweb_config_dir dburi")
    return community(
        file_path=os.path.join(community_file_dir, "database", "community_files"),
        hgweb_config_dir=community_file_dir,
        dburi="sqlite:///%s" % os.path.join(community_file_dir, "database", "community.sqlite"),
    )


def test_build_index(whoosh_index_dir, community_file_structure):
    repos_indexed, tools_indexed = build_index(
        whoosh_index_dir,
        community_file_structure.file_path,
        community_file_structure.hgweb_config_dir,
        community_file_structure.dburi,
    )
    assert repos_indexed == 1
    assert tools_indexed == 1
    idx = index.open_dir(whoosh_index_dir)
    assert idx.doc_count() == 1
    repos_indexed, tools_indexed = build_index(
        whoosh_index_dir,
        community_file_structure.file_path,
        community_file_structure.hgweb_config_dir,
        community_file_structure.dburi,
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
        community_file_structure.file_path,
        community_file_structure.hgweb_config_dir,
        community_file_structure.dburi,
    )
    assert repos_indexed == 1
    assert tools_indexed == 1
