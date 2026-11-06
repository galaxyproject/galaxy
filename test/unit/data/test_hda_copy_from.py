import os
import threading
import time
from collections.abc import Iterator

import pytest
from sqlalchemy import (
    Engine,
    text,
)
from sqlalchemy.orm import Session

from galaxy import model
from galaxy.model.unittest_utils.model_testing_utils import (  # noqa: F401 - url is a fixture we have to import explicitly
    create_and_drop_database,
    disposing_engine,
    url,
)
from .test_galaxy_mapping import MockObjectStore

# GALAXY_TEST_DBURI='postgresql://postgres:postgres@localhost:5432/postgres'
DB_URI = os.environ.get("GALAXY_TEST_DBURI", "")

IS_POSTGRES = DB_URI.startswith("postgres")

skip_unless_postgres = pytest.mark.skipif(
    not IS_POSTGRES, reason="needs concurrent transactions, set GALAXY_TEST_DBURI to a postgres URL"
)


class NoFilesObjectStore(MockObjectStore):
    def exists(self, *args, **kwds):
        return False

    def delete(self, *args, **kwds):
        return True


@pytest.fixture(scope="module")
def tmp_directory(tmp_path_factory) -> str:
    return str(tmp_path_factory.mktemp("copy_from"))


@pytest.fixture(scope="module")
def engine(url) -> Iterator[Engine]:  # noqa: F811
    object_store = model.Dataset.object_store
    with create_and_drop_database(url), disposing_engine(url) as engine:
        model.mapper_registry.metadata.create_all(engine)
        model.setup_global_object_store_for_models(NoFilesObjectStore())  # type: ignore[arg-type]
        try:
            yield engine
        finally:
            model.Dataset.object_store = object_store


def _session(engine: Engine) -> Session:
    """Session configured like production's, see galaxy.model.base."""
    return Session(engine, autoflush=False)


def _new_hda(session: Session, history: model.History, state: str) -> model.HistoryDatasetAssociation:
    hda = model.HistoryDatasetAssociation(
        history=history, extension="txt", create_dataset=True, sa_session=session, flush=False
    )
    hda.dataset.state = state
    session.add(hda)
    return hda


def _source_and_cached(engine: Engine, source_state: str) -> tuple[int, int]:
    with _session(engine) as session:
        history = model.History(name="job cache copy race")
        session.add(history)
        source = _new_hda(session, history, source_state)
        cached = _new_hda(session, history, model.Dataset.states.OK)
        session.commit()
        return source.id, cached.id


@pytest.fixture
def queued_and_cached(engine: Engine) -> tuple[int, int]:
    return _source_and_cached(engine, model.Dataset.states.QUEUED)


def _wait_until_blocked(engine: Engine, thread: threading.Thread) -> None:
    deadline = time.monotonic() + 30
    with engine.connect() as conn:
        while time.monotonic() < deadline:
            waiting = conn.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock'"
                )
            ).scalar()
            if waiting or not thread.is_alive():
                return
            # pg_stat_activity is a snapshot taken once per transaction
            conn.commit()
            time.sleep(0.05)
    raise AssertionError("thread neither finished nor blocked on a lock")


def _run_in_thread(target) -> tuple[threading.Thread, list[Exception]]:
    errors: list[Exception] = []

    def run():
        try:
            target()
        except Exception as e:
            errors.append(e)

    thread = threading.Thread(target=run)
    thread.start()
    return thread, errors


def _assert_copy_on_cached_dataset(engine: Engine, copy_id: int, cached_id: int) -> None:
    with _session(engine) as session:
        copy = session.get(model.HistoryDatasetAssociation, copy_id)
        cached = session.get(model.HistoryDatasetAssociation, cached_id)
        assert copy and cached
        assert copy.dataset_id == cached.dataset_id
        assert copy.state == model.Dataset.states.OK


def test_copy_from_keeps_visibility_of_copies(engine, queued_and_cached):
    queued_id, cached_id = queued_and_cached
    with _session(engine) as session:
        output = session.get(model.HistoryDatasetAssociation, queued_id)
        cached = session.get(model.HistoryDatasetAssociation, cached_id)
        assert output and cached
        element = output.copy(flush=False)
        element.visible = False
        session.commit()
        output.copy_from(cached, include_metadata=True)
        session.commit()
        assert output.visible
        assert not element.visible
        assert element.dataset_id == cached.dataset_id


@skip_unless_postgres
def test_copy_committed_after_swap_starts_follows_swap(engine, queued_and_cached):
    queued_id, cached_id = queued_and_cached
    with _session(engine) as copier:
        source = copier.get(model.HistoryDatasetAssociation, queued_id)
        assert source
        copy = source.copy(flush=False)

        def swap():
            with _session(engine) as runner:
                output = runner.get(model.HistoryDatasetAssociation, queued_id)
                cached = runner.get(model.HistoryDatasetAssociation, cached_id)
                assert output and cached
                output.copy_from(cached, include_metadata=True)
                runner.commit()

        thread, errors = _run_in_thread(swap)
        _wait_until_blocked(engine, thread)
        copier.commit()
        copy_id = copy.id
    thread.join(30)
    assert not thread.is_alive()
    assert not errors, errors
    _assert_copy_on_cached_dataset(engine, copy_id, cached_id)


@skip_unless_postgres
@pytest.mark.parametrize("source_state", [model.Dataset.states.QUEUED, model.Dataset.states.PAUSED])
def test_copy_of_stale_source_after_swap_locked_follows_swap(engine, source_state):
    queued_id, cached_id = _source_and_cached(engine, source_state)
    copy_ids: list[int] = []
    with _session(engine) as copier:
        stale_source = copier.get(model.HistoryDatasetAssociation, queued_id)
        assert stale_source
        assert stale_source.state == source_state
        stale_source.name = "renamed by copier"
        with _session(engine) as runner:
            output = runner.get(model.HistoryDatasetAssociation, queued_id)
            cached = runner.get(model.HistoryDatasetAssociation, cached_id)
            assert output and cached
            output.copy_from(cached, include_metadata=True)
            runner.flush()

            def make_copy():
                copy = stale_source.copy(flush=False)
                copier.commit()
                copy_ids.append(copy.id)

            thread, errors = _run_in_thread(make_copy)
            _wait_until_blocked(engine, thread)
            runner.commit()
        thread.join(30)
    assert not thread.is_alive()
    assert not errors, errors
    _assert_copy_on_cached_dataset(engine, copy_ids[0], cached_id)
    with _session(engine) as session:
        source = session.get(model.HistoryDatasetAssociation, queued_id)
        copy = session.get(model.HistoryDatasetAssociation, copy_ids[0])
        assert source and copy
        assert source.name == copy.name == "renamed by copier"


@skip_unless_postgres
def test_open_copy_does_not_block_updates_of_source(engine, queued_and_cached):
    queued_id, _ = queued_and_cached
    with _session(engine) as copier:
        source = copier.get(model.HistoryDatasetAssociation, queued_id)
        assert source
        source.copy(flush=False)

        def update_source():
            with _session(engine) as other:
                output = other.get(model.HistoryDatasetAssociation, queued_id)
                assert output
                output.info = "job finished"
                other.commit()

        thread, errors = _run_in_thread(update_source)
        _wait_until_blocked(engine, thread)
        assert not thread.is_alive(), "update waited on the copier's lock"
    thread.join(30)
    assert not errors, errors
