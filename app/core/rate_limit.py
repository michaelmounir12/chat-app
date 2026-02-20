from typing import Optional
from uuid import UUID
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.db.redis_client import get_redis
import time


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/health") or request.url.path.startswith("/docs"):
            return await call_next(request)

        client_id = self._get_client_id(request)
        redis = await get_redis()

        minute_key = f"rate_limit:minute:{client_id}"
        hour_key = f"rate_limit:hour:{client_id}"

        current_minute = int(time.time() / 60)
        current_hour = int(time.time() / 3600)

        minute_count = await redis.get(f"{minute_key}:{current_minute}")
        hour_count = await redis.get(f"{hour_key}:{current_hour}")

        if minute_count and int(minute_count) >= self.requests_per_minute:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded: {self.requests_per_minute} requests per minute",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )

        if hour_count and int(hour_count) >= self.requests_per_hour:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded: {self.requests_per_hour} requests per hour",
                    "retry_after": 3600
                },
                headers={"Retry-After": "3600"}
            )

        pipe = redis.pipeline()
        pipe.incr(f"{minute_key}:{current_minute}")
        pipe.expire(f"{minute_key}:{current_minute}", 120)
        pipe.incr(f"{hour_key}:{current_hour}")
        pipe.expire(f"{hour_key}:{current_hour}", 7200)
        await pipe.execute()

        response = await call_next(request)
        return response

    def _get_client_id(self, request: Request) -> str:
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"
        return f"ip:{request.client.host if request.client else 'unknown'}"


class RateLimiter:
    @staticmethod
    async def check_rate_limit(
        key: str,
        limit: int,
        window_seconds: int,
        redis=None
    ) -> tuple[bool, Optional[int]]:
        if redis is None:
            redis = await get_redis()
        
        current_window = int(time.time() / window_seconds)
        rate_key = f"rate_limit:{key}:{current_window}"
        
        count = await redis.incr(rate_key)
        await redis.expire(rate_key, window_seconds + 10)
        
        if count > limit:
            retry_after = window_seconds - (int(time.time()) % window_seconds)
            return False, retry_after
        
        return True, None

    @staticmethod
    async def check_user_rate_limit(
        user_id: UUID,
        action: str,
        limit: int,
        window_seconds: int
    ) -> tuple[bool, Optional[int]]:
        key = f"user:{user_id}:{action}"
        return await RateLimiter.check_rate_limit(key, limit, window_seconds)
