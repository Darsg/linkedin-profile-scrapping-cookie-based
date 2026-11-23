import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models import JobStatus
from app.schemas.common import ORMModel


class ScrapeJobCreate(BaseModel):
    url: str = Field(
        min_length=1, max_length=500, examples=["https://www.linkedin.com/in/someone/"]
    )
    force: bool = Field(default=False, description="Re-scrape even if a fresh copy is stored")


class ScrapeJobOut(ORMModel):
    id: uuid.UUID
    input_url: str
    public_id: str
    provider: str
    status: JobStatus
    attempts: int
    from_cache: bool
    error: str | None
    profile_id: uuid.UUID | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
