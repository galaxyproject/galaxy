"""Unit tests for :meth:`galaxy.managers.sse.SSEConnectionManager.stream`.

The focus here is the database-connection lifecycle contract: an SSE stream is
long-lived (it can stay open for hours) but only touches the database while it
is being opened. The ``release_db_session`` callback must therefore run exactly
once, before the keepalive loop starts polling, so the request-scoped pooled DB
connection is returned instead of being pinned for the life of the connection.
See ``SSEConnectionManager.stream`` for the production rationale.
"""

from galaxy.managers.sse import (
    SSEConnectionManager,
    SSEEvent,
)


class FakeSession:
    """Stand-in for the request-scoped SQLAlchemy ``Session``.

    ``close`` returns the pooled connection in production; here it records that
    the connection was released and treats a second close as a contract
    violation (double-release of a checked-in connection is a latent bug).
    """

    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        if self.closed:
            raise AssertionError("session closed more than once")
        self.closed = True


async def _drain(gen):
    return [chunk async for chunk in gen]


async def test_release_db_session_called_before_loop():
    """The release callback fires before the first disconnect poll."""
    manager = SSEConnectionManager()
    released_before_first_poll = []

    session = FakeSession()

    async def is_disconnected():
        # Record the release state the first time the loop polls us, then break.
        released_before_first_poll.append(session.closed)
        return True

    await _drain(manager.stream(is_disconnected, user_id=1, release_db_session=session.close))

    assert released_before_first_poll == [True]
    assert session.closed is True


async def test_release_db_session_released_once_with_catch_up():
    """Catch-up priming does not change the single, pre-loop release.

    Asserts the effect (the session is closed exactly once) via the fake's own
    double-close guard rather than counting calls.
    """
    manager = SSEConnectionManager()
    session = FakeSession()

    async def is_disconnected():
        return True

    catch_up = SSEEvent(event="notification_status", data="{}")
    await _drain(
        manager.stream(
            is_disconnected,
            user_id=1,
            release_db_session=session.close,
            catch_up=catch_up,
        )
    )

    assert session.closed is True


async def test_stream_disconnect_cleans_up_connection():
    """The finally block unregisters the connection when the client leaves."""
    manager = SSEConnectionManager()

    async def is_disconnected():
        return True

    await _drain(manager.stream(is_disconnected, user_id=1, release_db_session=lambda: None))

    assert manager.total_connections == 0
