"""
Rate limiting via Redis — implementeret som FastAPI Depends.
Bruger INCR/EXPIRE pipeline: ingen ekstra pakker, kompatibel med FastAPI.
"""
from __future__ import annotations

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status

from app.config import settings


async def _get_redis() -> aioredis.Redis:  # type: ignore[override]
    client: aioredis.Redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


def make_rate_limiter(max_calls: int, window_seconds: int):
    """
    Returnerer en FastAPI-dependency der begrænser til max_calls per window_seconds pr. IP.
    Brug som: _rl: None = Depends(make_rate_limiter(10, 60))
    """
    async def _check(
        request: Request,
        redis: aioredis.Redis = Depends(_get_redis),
    ) -> None:
        ip = request.client.host if request.client else "unknown"
        key = f"rl:{request.url.path}:{ip}"
        pipe = redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        results = await pipe.execute()
        count: int = results[0]
        if count > max_calls:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="For mange forsøg — prøv igen om lidt.",
            )
    return _check
