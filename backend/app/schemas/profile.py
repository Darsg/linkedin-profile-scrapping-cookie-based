import uuid
from datetime import date, datetime

from app.schemas.common import ORMModel


class ContactOut(ORMModel):
    type: str
    value: str


class ExperienceOut(ORMModel):
    title: str | None
    company: str | None
    employment_type: str | None
    location: str | None
    start_date: date | None
    end_date: date | None
    is_current: bool
    description: str | None


class EducationOut(ORMModel):
    school: str | None
    degree: str | None
    field_of_study: str | None
    start_year: int | None
    end_year: int | None
    description: str | None


class ActivityOut(ORMModel):
    kind: str
    text: str | None
    url: str | None
    posted_at: datetime | None
    reactions_count: int | None
    comments_count: int | None


class ProfileSummary(ORMModel):
    id: uuid.UUID
    public_id: str
    url: str
    full_name: str | None
    headline: str | None
    location: str | None
    photo_url: str | None
    source_provider: str
    last_scraped_at: datetime


class ProfileDetail(ProfileSummary):
    about: str | None
    contacts: list[ContactOut]
    experiences: list[ExperienceOut]
    educations: list[EducationOut]
    activities: list[ActivityOut]
