import os
import shutil
import tempfile
from datetime import (
    datetime,
    timedelta,
)

import pytest
from whoosh import index

from tool_shed.util.shed_index import (
    build_index,
    get_repositories_for_indexing,
)
from tool_shed.webapp.model import (
    RepositoryMetadata,
    User,
)
from ._util import (
    random_name,
    repository_fixture,
    TestToolShedApp,
)

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


def test_get_repositories_for_indexing_orders_by_last_revision_create_time(shed_app: TestToolShedApp, new_user: User):
    # Regression test: the incremental fast path in build_index breaks out of
    # the loop as soon as it sees an already-indexed repo whose stored
    # full_last_updated matches Repository.last_updated_time. That requires the
    # ORDER BY to track last_updated_time, not Repository.update_time (which
    # is bumped by unrelated row changes such as times_downloaded).
    session = shed_app.model.session
    repo_a = repository_fixture(shed_app, new_user, random_name())
    repo_b = repository_fixture(shed_app, new_user, random_name())

    base = datetime(2026, 1, 1, 12, 0, 0)
    rm_a = RepositoryMetadata(repository_id=repo_a.id, changeset_revision="a", downloadable=True)
    rm_b = RepositoryMetadata(repository_id=repo_b.id, changeset_revision="b", downloadable=True)
    rm_a.create_time = base
    rm_a.update_time = base
    rm_b.create_time = base + timedelta(hours=1)
    rm_b.update_time = base + timedelta(hours=1)
    session.add_all([rm_a, rm_b])
    # Make repo_a's row look "recently updated" — under the old ORDER BY this
    # surfaced repo_a first even though repo_b has the newer downloadable
    # revision.
    repo_a.update_time = base + timedelta(days=1)
    repo_b.update_time = base
    session.flush()

    ids = [r.id for r in get_repositories_for_indexing(session)]
    assert ids.index(repo_b.id) < ids.index(repo_a.id)
