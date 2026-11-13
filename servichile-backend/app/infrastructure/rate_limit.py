import threading
import time
from typing import Protocol

class RateLimiter(Protocol):

    def allow(self, key: str, limit: int, window_s: int=60) -> bool:
        ...

class RedisRateLimiter:

    def __init__(self, url: str) -> None:
        import redis
        self._redis = redis.Redis.from_url(url)

    def allow(self, key: str, limit: int, window_s: int=60) -> bool:
        bucket = f'rl:{key}:{int(time.time() // window_s)}'
        pipe = self._redis.pipeline()
        pipe.incr(bucket)
        pipe.expire(bucket, window_s)
        count, _ = pipe.execute()
        return int(count) <= limit

class MemoryRateLimiter:

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_s: int=60) -> bool:
        window = int(time.time() // window_s)
        bucket = f'{key}:{window}'
        with self._lock:
            self._counts = {k: v for k, v in self._counts.items() if k.endswith(f':{window}')}
            self._counts[bucket] = self._counts.get(bucket, 0) + 1
            return self._counts[bucket] <= limit

def build_rate_limiter(redis_url: str | None) -> RateLimiter:
    return RedisRateLimiter(redis_url) if redis_url else MemoryRateLimiter()
