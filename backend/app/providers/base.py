"""The contract every data source implements.

Providers know how to *fetch* a profile and return it as a normalized
`ScrapedProfile`. They never touch the database or the queue.
"""

from datetime import date, datetime
from typing import Any, Protocol

from pydantic import BaseModel, Field

from app.utils.linkedin_url import ProfileRef

# --- normalized result ------------------------------------------------------


class ScrapedContact(BaseModel):
    type: str
    value: str


class ScrapedExperience(BaseModel):
    title: str | None = None
    company: str | None = None
    employment_type: str | None = None
    location: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool = False
    description: str | None = None


class ScrapedEducation(BaseModel):
    school: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    description: str | None = None


class ScrapedActivity(BaseModel):
    kind: str = "post"
    text: str | None = None
    url: str | None = None
    posted_at: datetime | None = None
    reactions_count: int | None = None
    comments_count: int | None = None


class ScrapedProfile(BaseModel):
    public_id: str
    url: str
    full_name: str | None = None
    headline: str | None = None
    location: str | None = None
    about: str | None = None
    photo_url: str | None = None
    contacts: list[ScrapedContact] = Field(default_factory=list)
    experiences: list[ScrapedExperience] = Field(default_factory=list)
    educations: list[ScrapedEducation] = Field(default_factory=list)
    activities: list[ScrapedActivity] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


# --- errors -----------------------------------------------------------------


class ProviderError(Exception):
    """Base class. The worker decides what to do from the subclass."""


class ProfileNotFound(ProviderError):
    """The profile does not exist or is not visible. Permanent — do not retry."""


class ProviderNeedsAttention(ProviderError):
    """A human must act (log in again, solve a verification, fix an API key, wait for
    the daily cap to reset). Permanent for this job — do not retry automatically."""


class ProviderTransientError(ProviderError):
    """Network hiccup, timeout, 429/5xx. Safe to retry with backoff."""


# --- contract ---------------------------------------------------------------


class ProfileProvider(Protocol):
    name: str

    async def fetch(self, ref: ProfileRef) -> ScrapedProfile: ...

    async def close(self) -> None: ...
