"""Job queue abstraction.

The API only knows `JobQueue`; the arq/Redis implementation can be swapped
(tests use an in-memory one) without touching services or routers.
"""

import uuid
from typing import Protocol

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import get_settings

TASK_NAME = "run_scrape_job"


def queue_name(provider: str) -> str:
    """One queue per provider, so slow browser jobs never block fast API jobs."""
    return f"scrape:{provider}"


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


class JobQueue(Protocol):
    async def enqueue(self, job_id: uuid.UUID, provider: str) -> None: ...

    async def ping(self) -> bool: ...


class ArqJobQueue:
    def __init__(self, pool: ArqRedis) -> None:
        self._pool = pool

    @classmethod
    async def connect(cls) -> "ArqJobQueue":
        return cls(await create_pool(redis_settings()))

    async def enqueue(self, job_id: uuid.UUID, provider: str) -> None:
        # _job_id makes the enqueue idempotent: the same DB job is never queued twice.
        await self._pool.enqueue_job(
            TASK_NAME, str(job_id), _job_id=str(job_id), _queue_name=queue_name(provider)
        )

    async def ping(self) -> bool:
        return bool(await self._pool.ping())

    async def close(self) -> None:
        await self._pool.aclose()
