from typing import Annotated

from fastapi import Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import get_session
from app.core.queue import JobQueue
from app.repositories.job_repo import JobRepository
from app.repositories.profile_repo import ProfileRepository
from app.services.scrape_service import ScrapeService


def get_queue(request: Request) -> JobQueue:
    return request.app.state.queue  # type: ignore[no-any-return]


SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
QueueDep = Annotated[JobQueue, Depends(get_queue)]


def get_scrape_service(session: SessionDep, settings: SettingsDep) -> ScrapeService:
    return ScrapeService(session, settings)


def get_profile_repo(session: SessionDep) -> ProfileRepository:
    return ProfileRepository(session)


def get_job_repo(session: SessionDep) -> JobRepository:
    return JobRepository(session)


ScrapeServiceDep = Annotated[ScrapeService, Depends(get_scrape_service)]
ProfileRepoDep = Annotated[ProfileRepository, Depends(get_profile_repo)]
JobRepoDep = Annotated[JobRepository, Depends(get_job_repo)]

LimitQuery = Annotated[int, Query(ge=1, le=100)]
OffsetQuery = Annotated[int, Query(ge=0)]
