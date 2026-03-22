"""
SSE event stream endpoint — live UI updates.
Frontend lytter og kalder React Query invalidateQueries() ved events.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_optional_user
from app.models.user import User
from app.services.sse_manager import sse_manager

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/events")
async def event_stream(
    user: User | None = Depends(get_optional_user),
) -> EventSourceResponse:
    """
    SSE stream. Sender events ved: price_change, check_complete, ai_job_done.
    Gæster modtager events men ser kun non-auth data.
    Keepalive sendes hvert 25s for at holde forbindelsen aktiv.
    """
    user_id = user.id if user else None

    async def generator():
        async for chunk in sse_manager.stream(user_id):
            yield chunk

    return EventSourceResponse(generator())
