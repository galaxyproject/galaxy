import os
import shutil
import sqlite3
import tempfile

import pytest
from whoosh import index

import tool_shed.webapp.model.mapping as ts_mapping
from tool_shed.util.shed_index import build_index
from tool_shed.webapp.model import RepositoryMetadata

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


@pytest.fixture
def shed_fixture(tmp_path):
    """Per-test mutable copy of the toolshed_community_files fixture."""
    dst = tmp_path / "community"
    shutil.copytree(COMMUNITY_FILES_DIR, str(dst))
    sqlite_path = dst / "database" / "community.sqlite"
    return {
        "root": str(dst),
        "sqlite_path": str(sqlite_path),
        "dburi": f"sqlite:///{sqlite_path}",
        "file_path": str(dst / "database" / "community_files"),
    }


def _build(shed_fixture, whoosh_index_dir):
    return build_index(
        whoosh_index_dir,
        shed_fixture["file_path"],
        shed_fixture["root"],
        "repos/",
        shed_fixture["dburi"],
    )


def test_push_triggers_reindex(shed_fixture, whoosh_index_dir):
    """End-to-end: an ORM write to RepositoryMetadata fires the after_update
    listener, bumps Repository.update_time, and the next build_index re-indexes
    the repo with the new full_last_updated. This is the regression for
    galaxyproject/infrastructure-playbook#60.
    """
    _build(shed_fixture, whoosh_index_dir)
    idx = index.open_dir(whoosh_index_dir)
    with idx.searcher() as searcher:
        before_full = searcher.document(id="1")["full_last_updated"]

    model_mapping = ts_mapping.init(shed_fixture["dburi"], engine_options={}, create_tables=False)
    session = model_mapping.session
    metadata_row = session.get(RepositoryMetadata, 1)
    metadata_row.changeset_revision = "fa1afe1" * 5
    session.add(metadata_row)
    session.commit()

    repos_indexed, _ = _build(shed_fixture, whoosh_index_dir)
    assert repos_indexed == 1
    idx = index.open_dir(whoosh_index_dir)
    with idx.searcher() as searcher:
        after_full = searcher.document(id="1")["full_last_updated"]
    assert after_full != before_full


def test_index_self_heals(shed_fixture, whoosh_index_dir):
    """A deleted repo is GC'd from the index, and a single repo with a broken
    hgweb config entry doesn't abort indexing of every other repo.
    """
    # Insert a 2nd repo with no .hg dir and no hgweb.config entry. It will
    # sort first under update_time DESC; without the resilience fix it would
    # halt the whole iteration via `return None` from the generator.
    conn = sqlite3.connect(shed_fixture["sqlite_path"])
    try:
        conn.execute(
            "INSERT INTO repository (id, name, type, deleted, deprecated, user_id, "
            "private, times_downloaded, create_time, update_time) "
            "VALUES (2, 'ghost_repo', 'unrestricted', 0, 0, 1, 0, 0, "
            "'2026-04-01 00:00:00', '2026-04-01 00:00:00')"
        )
        conn.execute(
            "INSERT INTO repository_metadata (id, repository_id, downloadable, "
            "metadata, create_time, update_time) "
            "VALUES (2, 2, 1, ?, '2026-04-01 00:00:00', '2026-04-01 00:00:00')",
            (b"{}",),
        )
        conn.commit()
    finally:
        conn.close()

    _build(shed_fixture, whoosh_index_dir)
    # Repo 1 (real) still got indexed; repo 2 (ghost) was skipped.
    idx = index.open_dir(whoosh_index_dir)
    with idx.searcher() as searcher:
        assert searcher.document(id="1") is not None
        assert searcher.document(id="2") is None

    # Now delete repo 1 in the DB. Next build_index should GC it from the index.
    conn = sqlite3.connect(shed_fixture["sqlite_path"])
    try:
        conn.execute("UPDATE repository SET deleted = 1 WHERE id = 1")
        conn.commit()
    finally:
        conn.close()

    _build(shed_fixture, whoosh_index_dir)
    assert index.open_dir(whoosh_index_dir).doc_count() == 0
