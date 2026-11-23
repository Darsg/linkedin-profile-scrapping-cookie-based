import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import (
    LimitQuery,
    OffsetQuery,
    ProfileRepoDep,
    QueueDep,
    ScrapeServiceDep,
    SessionDep,
)
from app.schemas.common import Page
from app.schemas.job import ScrapeJobOut
from app.schemas.profile import ProfileDetail, ProfileSummary

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("", response_model=Page[ProfileSummary])
async def list_profiles(
    profiles: ProfileRepoDep,
    q: str | None = None,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
) -> Page[ProfileSummary]:
    rows, total = await profiles.list(q, limit, offset)
    return Page(
        items=[ProfileSummary.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{profile_id}", response_model=ProfileDetail)
async def get_profile(profile_id: uuid.UUID, profiles: ProfileRepoDep) -> ProfileDetail:
    profile = await profiles.get(profile_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")
    return ProfileDetail.model_validate(profile)


@router.post(
    "/{profile_id}/refresh", response_model=ScrapeJobOut, status_code=status.HTTP_202_ACCEPTED
)
async def refresh_profile(
    profile_id: uuid.UUID, profiles: ProfileRepoDep, service: ScrapeServiceDep, queue: QueueDep
) -> ScrapeJobOut:
    """Queue a forced re-scrape of a stored profile."""
    profile = await profiles.get(profile_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")
    job = await service.submit(profile.url, queue, force=True)
    return ScrapeJobOut.model_validate(job)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: uuid.UUID, profiles: ProfileRepoDep, session: SessionDep
) -> Response:
    """Remove a profile and everything stored about it."""
    if not await profiles.delete(profile_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
