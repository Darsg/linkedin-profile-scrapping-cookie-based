"""Use cases around scrape jobs: submitting one (API side) and executing one (worker side)."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.queue import JobQueue
from app.models import JobStatus, ScrapeJob
from app.providers.base import (
    ProfileNotFound,
    ProfileProvider,
    ProviderNeedsAttention,
    ProviderTransientError,
)
from app.repositories.job_repo import JobRepository
from app.repositories.profile_repo import ProfileRepository
from app.utils.linkedin_url import ProfileRef, parse_profile_url

log = get_logger(__name__)


class RetryLater(Exception):
    """Raised by `execute` when the job should be retried after `delay_seconds`."""

    def __init__(self, delay_seconds: int, reason: str) -> None:
        super().__init__(reason)
        self.delay_seconds = delay_seconds


class ScrapeService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._jobs = JobRepository(session)
        self._profiles = ProfileRepository(session)

    # --- API side -----------------------------------------------------------

    async def submit(self, url: str, queue: JobQueue, force: bool = False) -> ScrapeJob:
        """Create a job for a profile URL. Raises InvalidProfileUrl on bad input.

        If we already hold a fresh copy of the profile the job completes
        immediately from the stored data, unless `force` is set.
        """
        ref = parse_profile_url(url)
        job = ScrapeJob(
            id=uuid.uuid4(),
            input_url=url.strip(),
            public_id=ref.public_id,
            provider=self._settings.provider,
            status=JobStatus.QUEUED.value,
        )

        if not force:
            existing = await self._profiles.get_by_public_id(ref.public_id)
            ttl = timedelta(hours=self._settings.profile_ttl_hours)
            if existing and datetime.now(UTC) - existing.last_scraped_at < ttl:
                now = datetime.now(UTC)
                job.status = JobStatus.SUCCEEDED.value
                job.from_cache = True
                job.profile_id = existing.id
                job.provider = existing.source_provider
                job.started_at = job.finished_at = now
                self._jobs.add(job)
                await self._session.commit()
                return job

        self._jobs.add(job)
        # Commit before enqueueing so the worker can never see a job id that is not in the DB.
        await self._session.commit()
        await queue.enqueue(job.id, job.provider)
        return job

    # --- worker side --------------------------------------------------------

    async def execute(self, job_id: uuid.UUID, provider: ProfileProvider, attempt: int) -> None:
        """Run one job to completion. Raises RetryLater for retryable failures."""
        job = await self._jobs.get(job_id, for_update=True)
        if job is None:
            log.warning("job_missing", job_id=str(job_id))
            return
        if job.status in (JobStatus.SUCCEEDED.value, JobStatus.NEEDS_ATTENTION.value):
            return  # already finished (duplicate delivery)

        job.status = JobStatus.RUNNING.value
        job.attempts = attempt
        job.started_at = job.started_at or datetime.now(UTC)
        job.error = None
        await self._session.commit()

        ref = ProfileRef(public_id=job.public_id, url=parse_profile_url(job.input_url).url)
        try:
            scraped = await provider.fetch(ref)
        except ProviderTransientError as exc:
            if attempt < self._settings.job_max_tries:
                await self._finish(job, JobStatus.QUEUED, f"Attempt {attempt} failed: {exc}")
                raise RetryLater(delay_seconds=5 * 2**attempt, reason=str(exc)) from exc
            await self._finish(job, JobStatus.FAILED, f"Gave up after {attempt} attempts: {exc}")
            return
        except ProviderNeedsAttention as exc:
            await self._finish(job, JobStatus.NEEDS_ATTENTION, str(exc))
            return
        except ProfileNotFound as exc:
            await self._finish(job, JobStatus.FAILED, str(exc))
            return
        except Exception as exc:  # unexpected bug in a provider/parser: record it, don't loop
            log.exception("job_crashed", job_id=str(job_id))
            await self._finish(job, JobStatus.FAILED, f"Unexpected error: {exc!r}")
            return

        # Profile write and job completion commit together.
        job.profile_id = await self._profiles.upsert(scraped, provider.name)
        await self._finish(job, JobStatus.SUCCEEDED, None)
        log.info("job_succeeded", job_id=str(job_id), public_id=job.public_id)

    async def _finish(self, job: ScrapeJob, status: JobStatus, error: str | None) -> None:
        job.status = status.value
        job.error = error
        if status is not JobStatus.QUEUED:
            job.finished_at = datetime.now(UTC)
        await self._session.commit()
