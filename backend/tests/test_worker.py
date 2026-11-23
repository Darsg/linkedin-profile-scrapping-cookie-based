import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import JobStatus, ScrapeJob
from app.providers.base import ProviderNeedsAttention, ScrapedProfile
from app.providers.mock_provider import MockProvider
from app.services.scrape_service import RetryLater, ScrapeService
from app.utils.linkedin_url import ProfileRef
from tests.conftest import InMemoryQueue


async def _submit(session: AsyncSession, slug: str) -> tuple[ScrapeService, ScrapeJob]:
    service = ScrapeService(session, get_settings())
    job = await service.submit(f"https://www.linkedin.com/in/{slug}", InMemoryQueue())
    return service, job


async def test_missing_profile_fails_without_retry(session: AsyncSession) -> None:
    service, job = await _submit(session, "not-found")
    await service.execute(job.id, MockProvider(), attempt=1)
    assert job.status == JobStatus.FAILED
    assert job.error == "Profile does not exist"
    assert job.profile_id is None and job.finished_at is not None


async def test_transient_error_retries_with_backoff_then_gives_up(session: AsyncSession) -> None:
    service, job = await _submit(session, "flaky")
    max_tries = get_settings().job_max_tries

    delays = []
    for attempt in range(1, max_tries):
        with pytest.raises(RetryLater) as retry:
            await service.execute(job.id, MockProvider(), attempt=attempt)
        delays.append(retry.value.delay_seconds)
        assert job.status == JobStatus.QUEUED and job.finished_at is None
    assert delays == sorted(delays) and len(set(delays)) == len(delays)  # growing backoff

    await service.execute(job.id, MockProvider(), attempt=max_tries)
    assert job.status == JobStatus.FAILED
    assert job.attempts == max_tries and "Gave up" in (job.error or "")


async def test_needs_attention_is_terminal(session: AsyncSession) -> None:
    class LoggedOut(MockProvider):
        async def fetch(self, ref: ProfileRef) -> ScrapedProfile:
            raise ProviderNeedsAttention("Run `make login`")

    service, job = await _submit(session, "someone")
    await service.execute(job.id, LoggedOut(), attempt=1)
    assert (job.status, job.error) == (JobStatus.NEEDS_ATTENTION, "Run `make login`")

    # A duplicate delivery must not run the provider again.
    await service.execute(job.id, MockProvider(), attempt=2)
    assert job.status == JobStatus.NEEDS_ATTENTION and job.attempts == 1


async def test_provider_bug_is_recorded_not_raised(session: AsyncSession) -> None:
    class Broken(MockProvider):
        async def fetch(self, ref: ProfileRef) -> ScrapedProfile:
            raise KeyError("selector")

    service, job = await _submit(session, "someone")
    await service.execute(job.id, Broken(), attempt=1)
    assert job.status == JobStatus.FAILED and "KeyError" in (job.error or "")


async def test_unknown_job_id_is_ignored(session: AsyncSession) -> None:
    await ScrapeService(session, get_settings()).execute(uuid.uuid4(), MockProvider(), attempt=1)
