"""Unit tests for :meth:`galaxy.managers.sse.SSEConnectionManager.stream`.

The DB-connection release for SSE now lives in
:class:`galaxy.webapps.base.api.GalaxyStreamingResponse` (covered by
``test/unit/webapps/base/test_streaming_response.py``). These tests just cover
the manager's own lifecycle contract: a connection is registered on entry and
cleaned up in the ``finally`` block when the client disconnects.
"""

import asyncio

import pytest

from galaxy.managers.sse import (
    SSEConnectionManager,
    SSEEvent,
)


async def _drain(gen):
    return [chunk async for chunk in gen]


async def test_stream_disconnect_cleans_up_connection():
    """The finally block unregisters the connection when the client leaves."""
    manager = SSEConnectionManager()

    async def is_disconnected():
        return True

    await _drain(manager.stream(is_disconnected, user_id=1))

    assert manager.total_connections == 0


async def _never_disconnected():
    return False


async def _next_chunk(gen):
    return await asyncio.wait_for(gen.__anext__(), timeout=1)


async def test_begin_shutdown_ends_an_open_stream():
    manager = SSEConnectionManager()
    gen = manager.stream(_never_disconnected, user_id=1)
    assert (await _next_chunk(gen)).startswith("event: ready")
    pending = asyncio.ensure_future(_next_chunk(gen))
    await asyncio.sleep(0)  # let it block on the empty queue

    manager.begin_shutdown()

    with pytest.raises(StopAsyncIteration):
        await pending
    assert manager.total_connections == 0


async def test_begin_shutdown_ends_a_stream_whose_queue_is_full():
    manager = SSEConnectionManager()
    gen = manager.stream(_never_disconnected, user_id=1)
    assert (await _next_chunk(gen)).startswith("event: ready")
    for _ in range(64):
        manager.push_broadcast(SSEEvent(event="history_update", data="{}"))
    await asyncio.sleep(0)  # let the pushes land

    manager.begin_shutdown()

    with pytest.raises(StopAsyncIteration):
        await _next_chunk(gen)
    assert manager.total_connections == 0


async def test_stream_opened_after_begin_shutdown_ends_immediately():
    manager = SSEConnectionManager()
    manager.begin_shutdown()

    chunks = await asyncio.wait_for(_drain(manager.stream(_never_disconnected, user_id=1)), timeout=1)

    assert chunks == []
    assert manager.total_connections == 0
