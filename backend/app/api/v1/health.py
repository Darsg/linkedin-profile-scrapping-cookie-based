from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import QueueDep, SessionDep, SettingsDep

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str
    database: bool
    queue: bool
    provider: str


@router.get("/health", response_model=Health)
async def health(
    session: SessionDep, queue: QueueDep, settings: SettingsDep, response: Response
) -> Health:
    try:
        await session.execute(text("SELECT 1"))
        database = True
    except Exception:
        database = False
    try:
        queue_ok = await queue.ping()
    except Exception:
        queue_ok = False

    healthy = database and queue_ok
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return Health(
        status="ok" if healthy else "degraded",
        database=database,
        queue=queue_ok,
        provider=settings.provider,
    )
