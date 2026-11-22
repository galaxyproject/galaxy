import asyncio
import json

from galaxy.managers.sse import SSEConnectionManager
from galaxy.queue_worker import (
    invocation_update,
    job_update,
)
from galaxy.security.idencoding import IdEncodingHelper


class App:
    def __init__(self) -> None:
        self.sse_manager = SSEConnectionManager()
        self.security = IdEncodingHelper(id_secret="sse-entity-updates")

    def __getitem__(self, cls):
        assert cls is SSEConnectionManager
        return self.sse_manager


def _connect(app: App, user_id: int | None = None, session_id: int | None = None) -> asyncio.Queue:
    queue = app.sse_manager.connect(user_id, session_id)
    queue.get_nowait()  # ready
    return queue


async def _received(queue: asyncio.Queue) -> list[dict]:
    await asyncio.sleep(0)  # run the call_soon_threadsafe puts
    events = []
    while not queue.empty():
        event = queue.get_nowait()
        events.append({"event": event.event, **json.loads(event.data)})
    return events


def _job(job_id, state="ok", user_id=None, session_id=None, history_id=None) -> dict:
    return {"job_id": job_id, "state": state, "user_id": user_id, "session_id": session_id, "history_id": history_id}


async def test_owner_subscribed_to_own_history_gets_one_event_and_viewers_get_its_items():
    app = App()
    encode = app.security.encode_id
    owner = _connect(app, user_id=1)
    viewer = _connect(app, user_id=2)
    app.sse_manager.subscribe_user_viewer(1, encode(10))
    app.sse_manager.subscribe_user_viewer(2, encode(10))

    job_update(app, updates=[_job(5, user_id=1, history_id=10), _job(6, user_id=1, history_id=11)])

    assert await _received(owner) == [
        {"event": "job_update", "jobs": [{"id": encode(5), "state": "ok"}, {"id": encode(6), "state": "ok"}]}
    ]
    assert await _received(viewer) == [{"event": "job_update", "jobs": [{"id": encode(5), "state": "ok"}]}]


async def test_anonymous_job_is_pushed_to_its_session():
    app = App()
    anonymous = _connect(app, session_id=7)
    other = _connect(app, session_id=8)

    job_update(app, updates=[_job(5, state="running", session_id=7)])

    assert await _received(anonymous) == [
        {"event": "job_update", "jobs": [{"id": app.security.encode_id(5), "state": "running"}]}
    ]
    assert await _received(other) == []


async def test_resync_reaches_users_sessions_and_history_viewers():
    app = App()
    user = _connect(app, user_id=1)
    anonymous = _connect(app, session_id=7)
    viewer = _connect(app, user_id=2)
    app.sse_manager.subscribe_user_viewer(2, app.security.encode_id(10))

    job_update(app, updates=[], resync_user_ids=[1], resync_session_ids=[7], resync_history_ids=[10])

    for queue in (user, anonymous, viewer):
        assert await _received(queue) == [{"event": "job_update", "resync": True}]


async def test_invocation_update_reaches_owner_and_viewers():
    app = App()
    encode = app.security.encode_id
    owner = _connect(app, user_id=1)
    viewer = _connect(app, user_id=2)
    app.sse_manager.subscribe_user_viewer(2, encode(10))

    invocation_update(app, updates=[{"user_id": 1, "history_id": 10, "invocation_id": 3, "state": "ready"}])

    expected = [{"event": "invocation_update", "invocations": [{"id": encode(3), "state": "ready"}]}]
    assert await _received(owner) == expected
    assert await _received(viewer) == expected
