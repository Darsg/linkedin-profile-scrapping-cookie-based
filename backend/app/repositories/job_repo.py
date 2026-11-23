import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ScrapeJob


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, job: ScrapeJob) -> None:
        self._session.add(job)

    async def get(self, job_id: uuid.UUID, for_update: bool = False) -> ScrapeJob | None:
        stmt = select(ScrapeJob).where(ScrapeJob.id == job_id)
        if for_update:
            stmt = stmt.with_for_update()
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list(
        self, status: str | None, limit: int, offset: int
    ) -> tuple[list[ScrapeJob], int]:
        stmt = select(ScrapeJob)
        if status:
            stmt = stmt.where(ScrapeJob.status == status)
        total = await self._session.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = await self._session.scalars(
            stmt.order_by(ScrapeJob.created_at.desc()).limit(limit).offset(offset)
        )
        return list(rows), int(total or 0)
