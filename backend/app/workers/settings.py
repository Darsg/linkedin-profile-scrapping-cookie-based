"""arq worker entry point:  uv run arq app.workers.settings.WorkerSettings

Each worker process serves the queue of the provider it is configured for.
Scale out by starting more processes; the browser queue stays at one job at a time.
"""

import uuid
from typing import Any, ClassVar

from arq import Retry
from arq.worker import func

from app.core.config import get_settings
from app.core.db import get_engine, get_sessionmaker
from app.core.logging import configure_logging, get_logger
from app.core.queue import TASK_NAME, queue_name, redis_settings
from app.providers.factory import build_provider
from app.services.scrape_service import RetryLater, ScrapeService

log = get_logger(__name__)
_settings = get_settings()


async def run_scrape_job(ctx: dict[str, Any], job_id: str) -> None:
    async with get_sessionmaker()() as session:
        service = ScrapeService(session, _settings)
        try:
            await service.execute(uuid.UUID(job_id), ctx["provider"], attempt=ctx["job_try"])
        except RetryLater as exc:
            raise Retry(defer=exc.delay_seconds) from exc


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging()
    ctx["provider"] = build_provider(_settings, redis=ctx["redis"])
    log.info("worker_started", provider=_settings.provider, queue=queue_name(_settings.provider))


async def shutdown(ctx: dict[str, Any]) -> None:
    await ctx["provider"].close()
    await get_engine().dispose()


class WorkerSettings:
    functions: ClassVar = [func(run_scrape_job, name=TASK_NAME)]
    redis_settings = redis_settings()
    queue_name = queue_name(_settings.provider)
    on_startup = startup
    on_shutdown = shutdown
    max_tries = _settings.job_max_tries
    job_timeout = _settings.job_timeout_seconds
    # One browser session must not be driven concurrently; API/mock jobs can fan out.
    max_jobs = 1 if _settings.provider == "playwright" else 10
