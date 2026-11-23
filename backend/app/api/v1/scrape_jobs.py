import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import JobRepoDep, LimitQuery, OffsetQuery, QueueDep, ScrapeServiceDep
from app.models import JobStatus
from app.schemas.common import Page
from app.schemas.job import ScrapeJobCreate, ScrapeJobOut
from app.utils.linkedin_url import InvalidProfileUrl

router = APIRouter(prefix="/scrape-jobs", tags=["scrape-jobs"])


@router.post("", response_model=ScrapeJobOut, status_code=status.HTTP_202_ACCEPTED)
async def create_scrape_job(
    body: ScrapeJobCreate, service: ScrapeServiceDep, queue: QueueDep
) -> ScrapeJobOut:
    """Queue a scrape for a LinkedIn profile URL. Poll the returned job for its status."""
    try:
        job = await service.submit(body.url, queue, force=body.force)
    except InvalidProfileUrl as exc:
        raise HTTPException(422, str(exc)) from exc
    return ScrapeJobOut.model_validate(job)


@router.get("", response_model=Page[ScrapeJobOut])
async def list_scrape_jobs(
    jobs: JobRepoDep,
    status_filter: Annotated[JobStatus | None, Query(alias="status")] = None,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
) -> Page[ScrapeJobOut]:
    rows, total = await jobs.list(status_filter.value if status_filter else None, limit, offset)
    return Page(
        items=[ScrapeJobOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{job_id}", response_model=ScrapeJobOut)
async def get_scrape_job(job_id: uuid.UUID, jobs: JobRepoDep) -> ScrapeJobOut:
    job = await jobs.get(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return ScrapeJobOut.model_validate(job)
