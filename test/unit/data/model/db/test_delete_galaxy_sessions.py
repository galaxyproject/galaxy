"""Run the cleanup command against real disposable databases, without mocks."""

import json
import os
import shutil
import subprocess
import sys
from datetime import (
    date,
    datetime,
    timedelta,
)
from uuid import uuid4

import pytest
from sqlalchemy import (
    create_engine,
    select,
    text,
    update,
)
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from galaxy import model as m
from galaxy.model.database_utils import DbUrl
from galaxy.model.scripts import delete_galaxy_sessions as cleanup
from galaxy.model.unittest_utils.model_testing_utils import create_and_drop_database

CUTOFF = datetime(2026, 1, 15)
OLD = CUTOFF - timedelta(days=60)


@pytest.fixture(scope="module", params=["sqlite", "postgresql"])
def db_url(request, tmp_path_factory):
    if request.param == "sqlite":
        yield f"sqlite:///{tmp_path_factory.mktemp('session-cleanup') / 'test.sqlite'}"
        return
    database_url = os.environ.get("GALAXY_TEST_SESSION_CLEANUP_DATABASE_URL")
    if not database_url:
        pytest.skip("set GALAXY_TEST_SESSION_CLEANUP_DATABASE_URL to a disposable PostgreSQL service")
    url = make_url(database_url)
    assert url.get_backend_name() == "postgresql"
    url = url.set(database=f"galaxytest_session_cleanup_{uuid4().hex}")
    with create_and_drop_database(DbUrl(url.render_as_string(hide_password=False))):
        yield url


@pytest.fixture(scope="module")
def engine(db_url):
    engine = create_engine(db_url)
    yield engine
    engine.dispose()


@pytest.fixture
def cli(engine, tmp_path):
    config = tmp_path / "galaxy.yml"
    config.write_text(
        f"galaxy:\n  database_connection: {json.dumps(engine.url.render_as_string(hide_password=False))}\n"
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("GALAXY_CONFIG_")}
    executable = shutil.which("galaxy-delete-sessions", path=os.path.dirname(sys.executable))
    command = [executable] if executable else [sys.executable, cleanup.__file__]

    def invoke(*args, expected_code=0):
        result = subprocess.run(
            [*command, "--config", str(config), "--updated", "2026-01-15", "--pause", "0", "--batch-size", "2", *args],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == expected_code, result.stdout + result.stderr
        return dict(item.split("=", 1) for item in result.stdout.splitlines()[-1].split())

    return invoke


def test_cleanup_command(cli, session, make_user, make_history, make_galaxy_session, make_job):
    user, history = make_user(), make_history()
    stale = make_galaxy_session(user=user, update_time=OLD)
    newest = make_galaxy_session(user=user, update_time=OLD)  # Higher ID wins the tie.
    undated = make_galaxy_session(user=user, update_time=OLD)
    current = make_galaxy_session(current_history=history, update_time=OLD)
    associated = make_galaxy_session(update_time=OLD)
    unowned = make_galaxy_session(update_time=OLD)
    plain = make_galaxy_session(update_time=OLD)
    owned = make_galaxy_session(update_time=OLD)
    extra = make_galaxy_session(update_time=OLD)
    at_cutoff = make_galaxy_session(update_time=CUTOFF)
    recent = make_galaxy_session(update_time=CUTOFF + timedelta(days=1))
    jobs = [make_job(), make_job()]
    jobs[0].session_id = unowned.id
    jobs[1].session_id, jobs[1].user_id = owned.id, user.id
    session.add_all(
        [
            m.GalaxySessionToHistoryAssociation(associated, history),
            m.Event(session_id=plain.id),
            m.UserAction(action="test", params="test", session_id=plain.id),
        ]
    )
    session.execute(update(m.GalaxySession).where(m.GalaxySession.id == undated.id).values(update_time=None))
    protected = {stale.id, newest.id, undated.id, current.id, associated.id, unowned.id, at_cutoff.id, recent.id}
    final = {newest.id, undated.id, at_cutoff.id, recent.id}
    session.commit()
    assert user.current_galaxy_session.id == newest.id
    tables = [
        m.GalaxySession.__table__,
        m.History.__table__,
        m.GalaxySessionToHistoryAssociation.__table__,
        m.Job.__table__,
        m.Event.__table__,
        m.UserAction.__table__,
    ]

    def snapshot():
        return [list(session.execute(select(t).order_by(t.c.id))) for t in tables]

    before = snapshot()
    session.commit()
    policy = ["--anonymous-only", "--preserve-anonymous-histories", "--preserve-sessions-with-jobs"]
    preview = cli(*policy, "--dry-run")
    assert (preview["status"], preview["would_delete"], preview["deleted"]) == ("complete", "3", "0")
    assert snapshot() == before
    session.commit()

    # Three fully protected pages must not stop the scan; the fourth commits two deletes.
    limited = cli(*policy, "--max-batches", "4")
    assert (limited["status"], limited["scanned"], limited["deleted"]) == ("limited", "8", "2")
    assert set(session.scalars(select(m.GalaxySession.id))) == protected | {extra.id}
    late_id = make_galaxy_session(update_time=OLD).id
    session.commit()
    resumed = cli(*policy, "--after-id", limited["after_id"], "--through-id", limited["through_id"])
    assert (resumed["status"], resumed["deleted"]) == ("complete", "1")
    assert set(session.scalars(select(m.GalaxySession.id))) == protected | {late_id}
    session.expire_all()
    assert jobs[1].session_id is None and jobs[0].session_id == unowned.id
    session.commit()

    # Default policy also removes linked anonymous sessions and the user's older session.
    result = cli()
    assert (result["status"], result["deleted"]) == ("complete", "5")
    assert set(session.scalars(select(m.GalaxySession.id))) == final
    session.expire_all()
    assert user.current_galaxy_session.id == newest.id
    assert session.scalar(select(m.GalaxySessionToHistoryAssociation.id)) is None
    for column, count in ((m.Job.session_id, 2), (m.Event.session_id, 1), (m.UserAction.session_id, 1)):
        assert list(session.scalars(select(column))) == [None] * count
    assert session.scalar(select(m.History.id)) == history.id


def test_refreshed_session_is_rechecked(engine, session, make_galaxy_session):
    row_id = make_galaxy_session(update_time=OLD).id
    session.commit()
    predicate = cleanup._eligibility(False, False)
    with engine.begin() as conn:
        ids = cleanup._eligible_ids(conn, [row_id], predicate, CUTOFF)
    assert ids == [row_id]
    session.execute(update(m.GalaxySession).where(m.GalaxySession.id == row_id).values(update_time=CUTOFF))
    session.commit()
    with engine.begin() as conn:
        assert cleanup._delete_batch(conn, ids, predicate, CUTOFF) == 0


def test_postgres_transaction_guards(engine, session, make_galaxy_session, cli):
    if engine.dialect.name != "postgresql":
        pytest.skip("PostgreSQL-specific read-only and timeout behavior")
    with pytest.raises(DBAPIError) as error:
        with cleanup._transaction(engine, True, 50, 25) as conn:
            assert conn.scalar(text("SHOW transaction_read_only")) == "on"
            assert conn.scalar(text("SHOW lock_timeout")) == "25ms"
            conn.execute(text("INSERT INTO galaxy_session DEFAULT VALUES"))
    assert (getattr(error.value.orig, "sqlstate", None) or getattr(error.value.orig, "pgcode", None)) == "25006"
    with pytest.raises(DBAPIError) as error:
        with cleanup._transaction(engine, False, 50, 25) as conn:
            assert conn.scalar(text("SHOW transaction_read_only")) == "off"
            conn.execute(text("SELECT pg_sleep(1)"))
    assert (getattr(error.value.orig, "sqlstate", None) or getattr(error.value.orig, "pgcode", None)) == "57014"
    ids = [make_galaxy_session(update_time=OLD).id for _ in range(2)]
    session.commit()
    with engine.begin() as blocker:
        blocker.execute(text("SELECT id FROM galaxy_session WHERE id = :id FOR UPDATE"), {"id": ids[1]})
        result = cli("--batch-size", "1", "--lock-timeout", "50", expected_code=1)
    assert (result["status"], result["deleted"], result["after_id"]) == ("failed", "1", str(ids[0]))
    assert set(session.scalars(select(m.GalaxySession.id))) == {ids[1]}


def test_default_cutoff():
    assert cleanup._get_default_max_update_time(date(2026, 3, 31)) == date(2026, 3, 1)
