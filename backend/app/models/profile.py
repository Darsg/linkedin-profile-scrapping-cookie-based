import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Timestamps, UUIDPrimaryKey


def _profile_fk() -> Mapped[uuid.UUID]:
    return mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), index=True)


class Profile(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "profiles"

    public_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    url: Mapped[str] = mapped_column(String(500))
    full_name: Mapped[str | None] = mapped_column(String(300), index=True)
    headline: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(300))
    about: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(Text)
    source_provider: Mapped[str] = mapped_column(String(30))
    # Untouched provider payload, so parsing can be fixed without re-scraping.
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    last_scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    contacts: Mapped[list["ContactInfo"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="ContactInfo.type"
    )
    experiences: Mapped[list["Experience"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="Experience.position"
    )
    educations: Mapped[list["Education"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="Education.position"
    )
    activities: Mapped[list["Activity"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="Activity.position"
    )


class ContactInfo(UUIDPrimaryKey, Base):
    __tablename__ = "contact_infos"
    __table_args__ = (UniqueConstraint("profile_id", "type", "value"),)

    profile_id: Mapped[uuid.UUID] = _profile_fk()
    type: Mapped[str] = mapped_column(String(30))  # email, phone, website, twitter, ...
    value: Mapped[str] = mapped_column(String(500))


class Experience(UUIDPrimaryKey, Base):
    __tablename__ = "experiences"

    profile_id: Mapped[uuid.UUID] = _profile_fk()
    position: Mapped[int] = mapped_column(Integer)  # order as shown on the profile
    title: Mapped[str | None] = mapped_column(String(300))
    company: Mapped[str | None] = mapped_column(String(300))
    employment_type: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(300))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(default=False)
    description: Mapped[str | None] = mapped_column(Text)


class Education(UUIDPrimaryKey, Base):
    __tablename__ = "educations"

    profile_id: Mapped[uuid.UUID] = _profile_fk()
    position: Mapped[int] = mapped_column(Integer)
    school: Mapped[str | None] = mapped_column(String(300))
    degree: Mapped[str | None] = mapped_column(String(300))
    field_of_study: Mapped[str | None] = mapped_column(String(300))
    start_year: Mapped[int | None] = mapped_column(Integer)
    end_year: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)


class Activity(UUIDPrimaryKey, Base):
    __tablename__ = "activities"

    profile_id: Mapped[uuid.UUID] = _profile_fk()
    position: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(30))  # post, repost, comment, article
    text: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reactions_count: Mapped[int | None] = mapped_column(Integer)
    comments_count: Mapped[int | None] = mapped_column(Integer)
