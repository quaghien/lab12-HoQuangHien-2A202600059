import time
from uuid import uuid4

import redis
from fastapi import HTTPException, status

from app.config import settings


def check_rate_limit(r: redis.Redis, user_id: str) -> None:
    now = int(time.time())
    key = f"rate_limit:{user_id}"
    window_start = now - 60

    r.zremrangebyscore(key, 0, window_start)
    current_count = r.zcard(key)
    if current_count >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({settings.rate_limit_per_minute} req/min)",
            headers={"Retry-After": "60"},
        )

    member = f"{now}-{uuid4().hex[:8]}"
    r.zadd(key, {member: now})
    r.expire(key, 61)
