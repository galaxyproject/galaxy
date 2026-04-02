from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket


class ChatExecutionStreamsManager:
    """Track and broadcast DA execution follow-up streams by exchange id."""

    _active_streams: dict[int, set[WebSocket]] = {}
    _lock = asyncio.Lock()

    async def register(self, exchange_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            self._active_streams.setdefault(exchange_id, set()).add(websocket)

    async def remove(self, exchange_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._active_streams.get(exchange_id)
            if connections and websocket in connections:
                connections.remove(websocket)
                if not connections:
                    self._active_streams.pop(exchange_id, None)

    async def broadcast_exec_followup(self, exchange_id: int, message: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._active_streams.get(exchange_id, set()))
        if not targets:
            return

        stale: list[WebSocket] = []
        for websocket in targets:
            try:
                await websocket.send_json(message)
            except Exception:
                stale.append(websocket)

        if stale:
            async with self._lock:
                connections = self._active_streams.get(exchange_id)
                if connections:
                    for websocket in stale:
                        connections.discard(websocket)
                    if not connections:
                        self._active_streams.pop(exchange_id, None)
