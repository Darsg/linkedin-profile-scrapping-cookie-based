"""Keeps the browser provider slow and bounded.

State lives in Redis so the limits hold across worker restarts and across
several worker processes. Without Redis (unit tests) it falls back to memory.
"""

import asyncio
import time
from datetime import UTC, datetime

from redis.asyncio import Redis

from app.providers.base import ProviderNeedsAttention

_LAST_KEY = "linkedin:pacer:last_fetch"
_COUNT_KEY = "linkedin:pacer:count:{day}"


class Pacer:
    def __init__(self, redis: Redis | None, min_delay_seconds: float, daily_cap: int) -> None:
        self._redis = redis
        self._min_delay = min_delay_seconds
        self._daily_cap = daily_cap
        self._mem_last = 0.0
        self._mem_count: dict[str, int] = {}

    async def wait_turn(self) -> None:
        """Block until the minimum gap since the last profile has passed, and
        refuse outright once today's cap is reached."""
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        count = await self._increment(day)
        if count > self._daily_cap:
            raise ProviderNeedsAttention(
                f"Daily cap of {self._daily_cap} profiles reached for the browser provider. "
                "It resets at 00:00 UTC."
            )
        wait = self._min_delay - (time.time() - await self._last())
        if wait > 0:
            await asyncio.sleep(wait)
        await self._touch()

    async def _increment(self, day: str) -> int:
        if self._redis is None:
            self._mem_count[day] = self._mem_count.get(day, 0) + 1
            return self._mem_count[day]
        key = _COUNT_KEY.format(day=day)
        count = int(await self._redis.incr(key))
        if count == 1:
            await self._redis.expire(key, 60 * 60 * 48)
        return count

    async def _last(self) -> float:
        if self._redis is None:
            return self._mem_last
        value = await self._redis.get(_LAST_KEY)
        return float(value) if value else 0.0

    async def _touch(self) -> None:
        if self._redis is None:
            self._mem_last = time.time()
        else:
            await self._redis.set(_LAST_KEY, time.time())
