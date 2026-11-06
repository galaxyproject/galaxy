import threading

import pytest
from sqlalchemy import (
    create_engine,
    text,
)
from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
)

from galaxy.model.user_quota_updates import (
    queue_user_quota_update,
    send_user_quota_updates_on_commit,
    UserQuotaUpdateBatcher,
    UserQuotaUpdates,
)


@pytest.fixture
def sent() -> list[UserQuotaUpdates]:
    return []


def new_session(send) -> scoped_session:
    session = scoped_session(sessionmaker(bind=create_engine("sqlite:///:memory:")))
    send_user_quota_updates_on_commit(session, send)
    return session


@pytest.fixture
def session(sent):
    session = new_session(sent.append)
    yield session
    session.remove()


def test_sends_queued_updates_only_after_commit(session, sent):
    session.execute(text("SELECT 1"))
    queue_user_quota_update(session, [1, 2])
    queue_user_quota_update(session, [2, 3], broadcast=True)
    assert sent == []

    session.commit()

    assert sent == [UserQuotaUpdates(user_ids={1, 2, 3}, broadcast=True)]


def test_sends_each_update_once(session, sent):
    session.execute(text("SELECT 1"))
    queue_user_quota_update(session, [1])
    session.commit()
    session.execute(text("SELECT 1"))
    session.commit()

    assert sent == [UserQuotaUpdates(user_ids={1})]


def test_discards_updates_on_rollback(session, sent):
    session.execute(text("SELECT 1"))
    queue_user_quota_update(session, [1])
    session.rollback()
    session.execute(text("SELECT 1"))
    session.commit()

    assert sent == []


def test_ignores_empty_update(session, sent):
    session.execute(text("SELECT 1"))
    queue_user_quota_update(session, [])
    session.commit()

    assert sent == []


def test_failing_sender_does_not_fail_commit():
    attempts: list[UserQuotaUpdates] = []

    def fail(updates: UserQuotaUpdates) -> None:
        attempts.append(updates)
        raise RuntimeError("broker down")

    session = new_session(fail)
    session.execute(text("SELECT 1"))
    queue_user_quota_update(session, [1])

    session.commit()

    assert attempts == [UserQuotaUpdates(user_ids={1})]
    session.remove()


def test_batcher_sends_updates_added_within_the_interval_together(sent):
    # Long enough that only the explicit flush sends
    batcher = UserQuotaUpdateBatcher(sent.append, interval=60)
    batcher.add(UserQuotaUpdates(user_ids={1}))
    batcher.add(UserQuotaUpdates(user_ids={2}, broadcast=True))
    assert sent == []

    batcher.flush()
    batcher.flush()

    assert sent == [UserQuotaUpdates(user_ids={1, 2}, broadcast=True)]


def test_batcher_sends_after_the_interval():
    delivered = threading.Event()
    sent: list[UserQuotaUpdates] = []

    def send(updates: UserQuotaUpdates) -> None:
        sent.append(updates)
        delivered.set()

    batcher = UserQuotaUpdateBatcher(send, interval=0.01)
    batcher.add(UserQuotaUpdates(user_ids={1}))

    assert delivered.wait(timeout=5)
    assert sent == [UserQuotaUpdates(user_ids={1})]


def test_batcher_survives_a_failing_sender():
    attempts: list[UserQuotaUpdates] = []

    def fail(updates: UserQuotaUpdates) -> None:
        attempts.append(updates)
        raise RuntimeError("broker down")

    batcher = UserQuotaUpdateBatcher(fail, interval=60)
    batcher.add(UserQuotaUpdates(user_ids={1}))
    batcher.flush()
    batcher.add(UserQuotaUpdates(user_ids={2}))
    batcher.flush()

    assert attempts == [UserQuotaUpdates(user_ids={1}), UserQuotaUpdates(user_ids={2})]
