import logging
import threading
import time
from collections import deque
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

try:
    from redis.asyncio import Redis
except Exception:
    Redis = None

# In-memory sliding window limiter.
# Suitable for single-process deployment; use Redis for distributed setups.
class InMemoryWindowRateLimiter:
    def __init__(self, limit_per_minute: int):
        self.limit_per_minute = max(1, int(limit_per_minute))
        self.window_seconds = 60.0
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            queue = self._events.setdefault(key, deque())
            while queue and (now - queue[0]) > self.window_seconds:
                queue.popleft()
            if len(queue) >= self.limit_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Ark vision 调用过于频繁，请稍后再试",
                )
            queue.append(now)


class RedisWindowRateLimiter:
    """Distributed rate limiter based on Redis fixed window counters."""

    def __init__(
        self,
        limit: int,
        window_seconds: int,
        redis_url: str,
        key_prefix: str = "zhihuokeke",
    ):
        self.limit = max(1, int(limit))
        self.window_seconds = max(1, int(window_seconds))
        self.key_prefix = key_prefix
        self.redis_url = redis_url
        self._redis = Redis.from_url(redis_url, decode_responses=True) if Redis else None

    async def check(self, key: str) -> None:
        if self._redis is None:
            raise RuntimeError("redis client is not available")

        now_ts = int(time.time())
        bucket = now_ts // self.window_seconds
        redis_key = f"{self.key_prefix}:rl:{key}:{bucket}"
        try:
            count = await self._redis.incr(redis_key)
            if count == 1:
                await self._redis.expire(redis_key, self.window_seconds + 1)
            if int(count) > self.limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Ark vision 调用过于频繁，请稍后再试",
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise RuntimeError(f"redis rate limit check failed: {exc}")


class DistributedRateLimiter:
    """Redis-first limiter with in-memory fallback for single-node resilience."""

    def __init__(
        self,
        limit: int,
        window_seconds: int,
        use_redis: bool,
        redis_url: str,
        key_prefix: str = "zhihuokeke",
    ):
        self._memory_limiter = InMemoryWindowRateLimiter(limit)
        self._memory_limiter.window_seconds = float(window_seconds)
        self._redis_limiter = None
        if use_redis and redis_url:
            self._redis_limiter = RedisWindowRateLimiter(
                limit=limit,
                window_seconds=window_seconds,
                redis_url=redis_url,
                key_prefix=key_prefix,
            )

    async def check(self, key: str) -> None:
        if self._redis_limiter is not None:
            try:
                await self._redis_limiter.check(key)
                return
            except HTTPException:
                raise
            except Exception:
                logger.warning("Redis rate limiter unavailable, fallback to in-memory limiter", exc_info=True)

        self._memory_limiter.check(key)
