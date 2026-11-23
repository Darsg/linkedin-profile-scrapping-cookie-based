"""Third-party data API provider (Apify actor, synchronous run endpoint).

Apify has several LinkedIn-profile actors and their output field names differ,
so `map_item` accepts the common spellings instead of one exact schema. The
untouched item is stored in `raw`, so a mapping gap can be fixed without paying
for another run.
"""

from typing import Any

import httpx

from app.providers.base import (
    ProfileNotFound,
    ProviderNeedsAttention,
    ProviderTransientError,
    ScrapedActivity,
    ScrapedContact,
    ScrapedEducation,
    ScrapedExperience,
    ScrapedProfile,
)
from app.utils.dates import (
    parse_date_range,
    parse_datetime,
    parse_month_year,
    parse_year_range,
)
from app.utils.linkedin_url import ProfileRef

APIFY_BASE = "https://api.apify.com/v2"


def _first(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        value = _first(value, "text", "name", "title", "url", "linkedinText")
    text = str(value).strip() if value is not None else ""
    return text or None


def _int(value: Any) -> int | None:
    try:
        return int(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _date(value: Any) -> Any:
    """Dates come as 'Jan 2020', '2020', or {'year': 2020, 'month': 1}."""
    if isinstance(value, dict):
        year = _int(value.get("year"))
        if year is None:
            return parse_month_year(_str(value.get("text")))
        month = value.get("month")
        month_text = f"{month} " if isinstance(month, str) else ""
        parsed = parse_month_year(f"{month_text}{year}")
        if parsed and isinstance(month, int) and 1 <= month <= 12:
            parsed = parsed.replace(month=month)
        return parsed
    return parse_month_year(_str(value))


def _map_experience(item: dict[str, Any]) -> ScrapedExperience:
    start = _date(_first(item, "startDate", "jobStartedOn", "starts_at", "startedOn"))
    end_raw = _first(item, "endDate", "jobEndedOn", "ends_at", "endedOn")
    end = _date(end_raw)
    is_current = bool(_first(item, "jobStillWorking", "isCurrent", "current"))
    period = _str(_first(item, "period", "duration", "caption", "dateRange"))
    if start is None and period:
        start, end, is_current = parse_date_range(period)
    if isinstance(end_raw, str) and "present" in end_raw.lower():
        is_current, end = True, None
    return ScrapedExperience(
        title=_str(_first(item, "title", "position", "jobTitle")),
        company=_str(_first(item, "companyName", "company", "subtitle")),
        employment_type=_str(_first(item, "employmentType", "employment_type")),
        location=_str(_first(item, "location", "jobLocation")),
        start_date=start,
        end_date=end,
        is_current=is_current or (start is not None and end is None and end_raw is None),
        description=_str(_first(item, "description", "jobDescription")),
    )


def _map_education(item: dict[str, Any]) -> ScrapedEducation:
    start_year, end_year = parse_year_range(
        _str(_first(item, "period", "caption", "dateRange", "duration"))
    )
    start = _date(_first(item, "startDate", "starts_at"))
    end = _date(_first(item, "endDate", "ends_at"))
    return ScrapedEducation(
        school=_str(_first(item, "schoolName", "school", "title", "institution")),
        degree=_str(_first(item, "degree", "degreeName", "subtitle")),
        field_of_study=_str(_first(item, "fieldOfStudy", "field_of_study", "field")),
        start_year=start.year if start else start_year,
        end_year=end.year if end else end_year,
        description=_str(_first(item, "description")),
    )


def _map_activity(item: dict[str, Any]) -> ScrapedActivity:
    kind = (_str(_first(item, "type", "kind", "postType")) or "post").lower()
    return ScrapedActivity(
        kind=kind if kind in {"post", "repost", "comment", "article"} else "post",
        text=_str(_first(item, "text", "postText", "content", "title")),
        url=_str(_first(item, "url", "postUrl", "postLink", "link")),
        posted_at=parse_datetime(
            _first(item, "postedAt", "postedAtISO", "postedAtTimestamp", "publishedAt", "date")
        ),
        reactions_count=_int(_first(item, "numLikes", "likesCount", "reactionsCount", "likes")),
        comments_count=_int(_first(item, "numComments", "commentsCount", "comments")),
    )


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def map_item(ref: ProfileRef, item: dict[str, Any]) -> ScrapedProfile:
    """Translate one actor dataset item into the normalized profile."""
    full_name = _str(_first(item, "fullName", "name"))
    if not full_name:
        parts = [_str(item.get("firstName")), _str(item.get("lastName"))]
        full_name = " ".join(p for p in parts if p) or None

    contacts: list[ScrapedContact] = []
    for kind, keys in {
        "email": ("email", "emailAddress"),
        "phone": ("mobileNumber", "phone", "phoneNumber"),
        "twitter": ("twitter", "twitterHandle"),
    }.items():
        value = _str(_first(item, *keys))
        if value:
            contacts.append(ScrapedContact(type=kind, value=value))
    websites = _first(item, "websites", "website", "companyWebsite")
    for site in websites if isinstance(websites, list) else [websites]:
        value = _str(site)
        if value:
            contacts.append(ScrapedContact(type="website", value=value))

    return ScrapedProfile(
        public_id=ref.public_id,
        url=ref.url,
        full_name=full_name,
        headline=_str(_first(item, "headline", "occupation")),
        location=_str(_first(item, "addressWithCountry", "location", "geoLocationName", "city")),
        about=_str(_first(item, "about", "summary")),
        photo_url=_str(
            _first(item, "profilePicHighQuality", "profilePic", "profilePicture", "photoUrl")
        ),
        contacts=contacts,
        experiences=[
            _map_experience(e)
            for e in _dicts(_first(item, "experiences", "experience", "positions"))
        ],
        educations=[_map_education(e) for e in _dicts(_first(item, "educations", "education"))],
        activities=[
            _map_activity(a)
            for a in _dicts(_first(item, "posts", "updates", "activities", "recentPosts"))
        ],
        raw=item,
    )


class ApifyProvider:
    name = "api"

    def __init__(
        self,
        token: str,
        actor_id: str,
        input_field: str = "profileUrls",
        timeout_seconds: float = 180.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._actor_id = actor_id.replace("/", "~")
        self._input_field = input_field
        self._client = client or httpx.AsyncClient(
            base_url=APIFY_BASE,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout_seconds,
        )

    async def fetch(self, ref: ProfileRef) -> ScrapedProfile:
        try:
            response = await self._client.post(
                f"/acts/{self._actor_id}/run-sync-get-dataset-items",
                json={self._input_field: [ref.url]},
            )
        except httpx.HTTPError as exc:
            raise ProviderTransientError(f"Data API request failed: {exc!r}") from exc

        if response.status_code in (401, 403):
            raise ProviderNeedsAttention("Data API rejected the token (check APIFY_TOKEN)")
        if response.status_code == 402:
            raise ProviderNeedsAttention("Data API account is out of credit")
        if response.status_code == 404:
            raise ProviderNeedsAttention("Data API actor not found (check APIFY_ACTOR_ID)")
        if response.status_code == 429 or response.status_code >= 500:
            raise ProviderTransientError(f"Data API returned {response.status_code}")
        if response.status_code >= 400:
            raise ProviderNeedsAttention(
                f"Data API rejected the request ({response.status_code}): {response.text[:300]}"
            )

        items = _dicts(response.json())
        if not items:
            raise ProfileNotFound("Data API returned no data for this profile")
        return map_item(ref, items[0])

    async def close(self) -> None:
        await self._client.aclose()
