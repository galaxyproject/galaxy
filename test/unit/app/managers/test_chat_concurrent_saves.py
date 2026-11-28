import os
import threading
import time
from collections.abc import Iterator
from typing import cast

import pytest
from sqlalchemy import (
    Engine,
    event,
    text,
)
from sqlalchemy.orm import Session

from galaxy import model
from galaxy.managers.chat import ChatManager
from galaxy.managers.context import ProvidesUserContext
from galaxy.model.unittest_utils.model_testing_utils import (  # noqa: F401 - url is a fixture we have to import explicitly
    create_and_drop_database,
    disposing_engine,
    url,
)

# GALAXY_TEST_DBURI='postgresql://postgres:postgres@localhost:5432/postgres'
skip_unless_postgres = pytest.mark.skipif(
    not os.environ.get("GALAXY_TEST_DBURI", "").startswith("postgres"),
    reason="needs concurrent transactions, set GALAXY_TEST_DBURI to a postgres URL",
)


class Trans:
    def __init__(self, session: Session, user: model.User):
        self.sa_session = session
        self.user = user


@pytest.fixture(scope="module")
def tmp_directory(tmp_path_factory) -> str:
    return str(tmp_path_factory.mktemp("chat_saves"))


@pytest.fixture(scope="module")
def engine(url) -> Iterator[Engine]:  # noqa: F811
    with create_and_drop_database(url), disposing_engine(url) as engine:
        model.mapper_registry.metadata.create_all(engine)
        yield engine


def _trans(session: Session, user_id: int) -> ProvidesUserContext:
    user = session.get(model.User, user_id)
    assert user
    return cast(ProvidesUserContext, Trans(session, user))


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


@skip_unless_postgres
@pytest.mark.filterwarnings("ignore:DELETE statement on table:sqlalchemy.exc.SAWarning")
def test_concurrent_saves_keep_document_and_messages_together(engine):
    with Session(engine, autoflush=False) as session:
        user = model.User(email="chat@example.org", password="password")
        session.add(user)
        session.commit()
        user_id = user.id
        saved = ChatManager().save_document_chat(_trans(session, user_id), "olit", [("q0", "r0")], {"v": 0})
        exchange_id = saved.id

    flushed = threading.Event()
    release = threading.Event()

    def save(tag: str, session: Session):
        trans = _trans(session, user_id)
        turns = [(f"{tag} q1", "r1"), (f"{tag} q2", "r2")]
        ChatManager().save_document_chat(trans, "olit", turns, {"v": tag}, exchange_id=exchange_id)

    with Session(engine, autoflush=False) as first, Session(engine, autoflush=False) as second:

        def hold(session, context):
            flushed.set()
            release.wait(30)

        event.listen(first, "after_flush", hold)
        first_thread, first_errors = _run_in_thread(lambda: save("A", first))
        assert flushed.wait(30)
        second_thread, second_errors = _run_in_thread(lambda: save("B", second))
        _wait_until_blocked(engine, second_thread)
        release.set()
        first_thread.join(30)
        second_thread.join(30)

    assert not first_thread.is_alive() and not second_thread.is_alive()
    assert not first_errors and not second_errors, first_errors + second_errors
    with Session(engine) as session:
        exchange = session.get(model.ChatExchange, exchange_id)
        assert exchange
        assert exchange.document == {"v": "B"}
        assert sorted(message.message for message in exchange.messages) == [
            '{"query": "B q1", "response": "r1", "agent_type": "olit"}',
            '{"query": "B q2", "response": "r2", "agent_type": "olit"}',
        ]
