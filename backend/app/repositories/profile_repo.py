import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, insert, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Activity, ContactInfo, Education, Experience, Profile
from app.providers.base import ScrapedProfile

_CHILD_TABLES = (ContactInfo, Experience, Education, Activity)


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, profile_id: uuid.UUID) -> Profile | None:
        stmt = (
            select(Profile)
            .where(Profile.id == profile_id)
            .options(
                selectinload(Profile.contacts),
                selectinload(Profile.experiences),
                selectinload(Profile.educations),
                selectinload(Profile.activities),
            )
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_public_id(self, public_id: str) -> Profile | None:
        stmt = select(Profile).where(Profile.public_id == public_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list(self, q: str | None, limit: int, offset: int) -> tuple[list[Profile], int]:
        stmt = select(Profile)
        if q:
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Profile.full_name.ilike(pattern),
                    Profile.headline.ilike(pattern),
                    Profile.public_id.ilike(pattern),
                )
            )
        total = await self._session.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = await self._session.scalars(
            stmt.order_by(Profile.last_scraped_at.desc()).limit(limit).offset(offset)
        )
        return list(rows), int(total or 0)

    async def delete(self, profile_id: uuid.UUID) -> bool:
        result = await self._session.execute(delete(Profile).where(Profile.id == profile_id))
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def upsert(self, data: ScrapedProfile, provider: str) -> uuid.UUID:
        """Insert or update the profile keyed on `public_id`, and replace its child
        rows. Runs inside the caller's transaction, so a profile is never half-written.

        ON CONFLICT makes this safe when two workers scrape the same profile at once.
        """
        values = {
            "url": data.url,
            "full_name": data.full_name,
            "headline": data.headline,
            "location": data.location,
            "about": data.about,
            "photo_url": data.photo_url,
            "source_provider": provider,
            "raw": data.raw,
            "last_scraped_at": datetime.now(UTC),
        }
        stmt = (
            pg_insert(Profile)
            .values(id=uuid.uuid4(), public_id=data.public_id, **values)
            .on_conflict_do_update(
                index_elements=[Profile.public_id], set_={**values, "updated_at": func.now()}
            )
            .returning(Profile.id)
        )
        profile_id: uuid.UUID = (await self._session.execute(stmt)).scalar_one()

        for table in _CHILD_TABLES:
            await self._session.execute(delete(table).where(table.profile_id == profile_id))

        def rows(items: list, positioned: bool = True) -> list[dict]:  # type: ignore[type-arg]
            out = []
            for index, item in enumerate(items):
                row = {"id": uuid.uuid4(), "profile_id": profile_id, **item.model_dump()}
                if positioned:
                    row["position"] = index
                out.append(row)
            return out

        # De-duplicate contacts: (profile, type, value) is unique.
        contacts = list({(c.type, c.value): c for c in data.contacts}.values())
        for table, payload in (
            (ContactInfo, rows(contacts, positioned=False)),
            (Experience, rows(data.experiences)),
            (Education, rows(data.educations)),
            (Activity, rows(data.activities)),
        ):
            if payload:
                await self._session.execute(insert(table), payload)
        return profile_id
