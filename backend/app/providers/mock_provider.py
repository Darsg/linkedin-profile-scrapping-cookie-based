"""Offline provider that returns clearly-fake sample data.

Used for tests and for demoing the full pipeline without touching LinkedIn.
The slug `not-found` simulates a missing profile, `flaky` a transient failure.
"""

import asyncio
import hashlib
from datetime import UTC, date, datetime, timedelta

from app.providers.base import (
    ProfileNotFound,
    ProviderTransientError,
    ScrapedActivity,
    ScrapedContact,
    ScrapedEducation,
    ScrapedExperience,
    ScrapedProfile,
)
from app.utils.linkedin_url import ProfileRef

_COMPANIES = ["Northwind Labs", "Acme Robotics", "Globex Cloud", "Initech Data", "Umbrella AI"]
_TITLES = ["Software Engineer", "Senior Engineer", "Staff Engineer", "Engineering Manager"]
_SCHOOLS = ["Example State University", "Sample Institute of Technology", "Demo College"]
_CITIES = ["Bengaluru, India", "Berlin, Germany", "Austin, Texas", "Toronto, Canada"]


class MockProvider:
    name = "mock"

    def __init__(self, delay_seconds: float = 0.0) -> None:
        self._delay = delay_seconds

    async def fetch(self, ref: ProfileRef) -> ScrapedProfile:
        if self._delay:
            await asyncio.sleep(self._delay)
        if ref.public_id == "not-found":
            raise ProfileNotFound("Profile does not exist")
        if ref.public_id == "flaky":
            raise ProviderTransientError("Simulated network failure")

        seed = int(hashlib.sha256(ref.public_id.encode()).hexdigest(), 16)

        def pick(options: list[str], offset: int = 0) -> str:
            return options[(seed + offset) % len(options)]

        name = " ".join(p.capitalize() for p in ref.public_id.replace("_", "-").split("-") if p)
        name = "".join(c for c in name if not c.isdigit()).strip() or "Sample Person"
        now = datetime.now(UTC)
        start_year = 2012 + seed % 5

        return ScrapedProfile(
            public_id=ref.public_id,
            url=ref.url,
            full_name=name,
            headline=f"{pick(_TITLES, 2)} at {pick(_COMPANIES)} (sample data)",
            location=pick(_CITIES),
            about=(
                "This is generated sample data from the mock provider. "
                "Switch PROVIDER to 'playwright' or 'api' to fetch real profiles."
            ),
            contacts=[
                ScrapedContact(type="email", value=f"{ref.public_id}@example.com"),
                ScrapedContact(type="website", value=f"https://example.com/{ref.public_id}"),
            ],
            experiences=[
                ScrapedExperience(
                    title=pick(_TITLES, 2),
                    company=pick(_COMPANIES),
                    employment_type="Full-time",
                    location=pick(_CITIES),
                    start_date=date(start_year + 8, 3, 1),
                    is_current=True,
                    description="Leads platform work for the data ingestion pipeline.",
                ),
                ScrapedExperience(
                    title=pick(_TITLES, 1),
                    company=pick(_COMPANIES, 1),
                    employment_type="Full-time",
                    location=pick(_CITIES, 1),
                    start_date=date(start_year + 4, 7, 1),
                    end_date=date(start_year + 8, 2, 1),
                    description="Built internal tooling and public APIs.",
                ),
            ],
            educations=[
                ScrapedEducation(
                    school=pick(_SCHOOLS),
                    degree="Bachelor of Technology",
                    field_of_study="Computer Science",
                    start_year=start_year,
                    end_year=start_year + 4,
                )
            ],
            activities=[
                ScrapedActivity(
                    kind="post",
                    text="Excited to share what our team shipped this quarter (sample post).",
                    url=f"https://www.linkedin.com/feed/update/urn:li:activity:{seed % 10**19}/",
                    posted_at=now - timedelta(days=3),
                    reactions_count=120 + seed % 200,
                    comments_count=seed % 30,
                ),
                ScrapedActivity(
                    kind="repost",
                    text="Great read on scaling job queues (sample repost).",
                    posted_at=now - timedelta(days=12),
                    reactions_count=seed % 60,
                    comments_count=seed % 7,
                ),
            ],
            raw={"source": "mock"},
        )

    async def close(self) -> None:
        return None
