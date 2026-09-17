"""Unit tests for :meth:`galaxy.managers.sse.SSEConnectionManager.stream`.

The DB-connection release for SSE now lives in
:class:`galaxy.webapps.base.api.GalaxyStreamingResponse` (covered by
``test/unit/webapps/base/test_streaming_response.py``). These tests just cover
the manager's own lifecycle contract: a connection is registered on entry and
cleaned up in the ``finally`` block when the client disconnects.
"""

from galaxy.managers.sse import SSEConnectionManager


async def _drain(gen):
    return [chunk async for chunk in gen]


async def test_stream_disconnect_cleans_up_connection():
    """The finally block unregisters the connection when the client leaves."""
    manager = SSEConnectionManager()

    async def is_disconnected():
        return True

    await _drain(manager.stream(is_disconnected, user_id=1))

    assert manager.total_connections == 0
