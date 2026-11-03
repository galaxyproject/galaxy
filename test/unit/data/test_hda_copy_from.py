import os
import threading
import time
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import (
    create_engine,
    Engine,
    text,
)
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from galaxy import model
from galaxy.datatypes.registry import Registry
from galaxy.model.database_utils import DbUrl
from galaxy.model.unittest_utils.model_testing_utils import create_and_drop_database
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
def engine(tmp_path_factory) -> Iterator[Engine]:
    database = f"gxtest_{uuid.uuid4().hex}"
    if IS_POSTGRES:
        url = DbUrl(make_url(DB_URI).set(database=database).render_as_string(hide_password=False))
    else:
        url = DbUrl(f"sqlite:///{tmp_path_factory.mktemp('copy_from') / database}")
    with create_and_drop_database(url):
        engine = create_engine(url)
        model.mapper_registry.metadata.create_all(engine)
        model.setup_global_object_store_for_models(NoFilesObjectStore())  # type: ignore[arg-type]
        datatypes_registry = Registry()
        datatypes_registry.load_datatypes()
        model.set_datatypes_registry(datatypes_registry)
        try:
            yield engine
        finally:
            engine.dispose()


def _new_hda(session: Session, history: model.History, state: str) -> model.HistoryDatasetAssociation:
    hda = model.HistoryDatasetAssociation(
        history=history, extension="txt", create_dataset=True, sa_session=session, flush=False
    )
    hda.dataset.state = state
    session.add(hda)
    return hda


@pytest.fixture
def queued_and_cached(engine: Engine) -> tuple[int, int]:
    with Session(engine) as session:
        history = model.History(name="job cache copy race")
        session.add(history)
        queued = _new_hda(session, history, model.Dataset.states.QUEUED)
        cached = _new_hda(session, history, model.Dataset.states.OK)
        session.commit()
        return queued.id, cached.id


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
    with Session(engine) as session:
        copy = session.get(model.HistoryDatasetAssociation, copy_id)
        cached = session.get(model.HistoryDatasetAssociation, cached_id)
        assert copy and cached
        assert copy.dataset_id == cached.dataset_id
        assert copy.state == model.Dataset.states.OK


@skip_unless_postgres
def test_copy_committed_after_swap_starts_follows_swap(engine, queued_and_cached):
    queued_id, cached_id = queued_and_cached
    with Session(engine) as copier:
        source = copier.get(model.HistoryDatasetAssociation, queued_id)
        assert source
        copy = source.copy(flush=False)

        def swap():
            with Session(engine) as runner:
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
def test_copy_of_stale_source_after_swap_locked_follows_swap(engine, queued_and_cached):
    queued_id, cached_id = queued_and_cached
    copy_ids: list[int] = []
    with Session(engine) as copier:
        stale_source = copier.get(model.HistoryDatasetAssociation, queued_id)
        assert stale_source
        assert stale_source.state == model.Dataset.states.QUEUED
        with Session(engine) as runner:
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
