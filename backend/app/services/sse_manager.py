"""
SSEManager — Server-Sent Events til live UI-opdateringer.

Design:
  - Én asyncio.Queue pr. aktiv SSE-forbindelse
  - Events indeholder kun type + minimal data → frontend kalder invalidateQueries()
  - Keepalive-kommentar hvert 25s for at undgå nginx proxy-timeout
  - Ingen data accumulation — events er ephemeral

Brug fra services:
  await sse_manager.broadcast({"type": "price_change", "data": {"watchId": str(id)}})

Frontend lytter med EventSource('/api/v2/events') og invaliderer React Query caches.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import AsyncGenerator

import structlog

logger = structlog.get_logger(__name__)

_KEEPALIVE_INTERVAL = 25.0  # sekunder


class SSEManager:
    def __init__(self) -> None:
        # user_id → set af aktive queues for den bruger
        self._queues: dict[str | None, set[asyncio.Queue]] = {}

    def subscribe(self, user_id: uuid.UUID | None) -> asyncio.Queue:
        key = str(user_id) if user_id else "guest"
        q: asyncio.Queue = asyncio.Queue(maxsize=50)
        self._queues.setdefault(key, set()).add(q)
        logger.debug("sse_subscribe", user_id=key, connections=len(self._queues[key]))
        return q

    def unsubscribe(self, user_id: uuid.UUID | None, queue: asyncio.Queue) -> None:
        key = str(user_id) if user_id else "guest"
        queues = self._queues.get(key, set())
        queues.discard(queue)
        if not queues:
            self._queues.pop(key, None)
        logger.debug("sse_unsubscribe", user_id=key)

    async def broadcast(self, event: dict) -> None:
        """Send event til alle aktive forbindelser."""
        if not self._queues:
            return
        payload = json.dumps(event, default=str)
        for queues in list(self._queues.values()):
            for q in list(queues):
                try:
                    q.put_nowait(payload)
                except asyncio.QueueFull:
                    # Lad langsom klient droppe events frem for at blokere
                    pass

    async def broadcast_to_user(self, user_id: uuid.UUID, event: dict) -> None:
        """Send kun til en specifik bruger."""
        key = str(user_id)
        queues = self._queues.get(key, set())
        if not queues:
            return
        payload = json.dumps(event, default=str)
        for q in list(queues):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    async def stream(self, user_id: uuid.UUID | None) -> AsyncGenerator[str, None]:
        """
        Async generator til FastAPI SSE endpoint.

        Brug:
          from sse_starlette.sse import EventSourceResponse
          return EventSourceResponse(sse_manager.stream(user.id))
        """
        q = self.subscribe(user_id)
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=_KEEPALIVE_INTERVAL)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive — forhindrer proxy-timeout
                    yield ": keepalive\n\n"
        finally:
            self.unsubscribe(user_id, q)


# Global singleton
sse_manager = SSEManager()
