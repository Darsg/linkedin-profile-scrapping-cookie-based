from datetime import date

import httpx
import pytest

from app.providers.api_provider import ApifyProvider, map_item
from app.providers.base import ProfileNotFound, ProviderNeedsAttention, ProviderTransientError
from app.utils.linkedin_url import parse_profile_url

REF = parse_profile_url("https://www.linkedin.com/in/asha-verma/")

ITEM = {
    "firstName": "Asha",
    "lastName": "Verma",
    "headline": "Staff Engineer",
    "addressWithCountry": "Pune, India",
    "about": "Builds data platforms.",
    "email": "asha@example.com",
    "mobileNumber": "+91 98000 00000",
    "websites": ["https://asha.example.dev"],
    "experiences": [
        {"title": "Staff Engineer", "companyName": "Northwind Labs", "jobStartedOn": "Jan 2022",
         "jobStillWorking": True},
        {"title": "Engineer", "subtitle": "Acme", "caption": "Oct 2016 - Jun 2019 · 2 yrs"},
        {"position": "Intern", "company": {"name": "Globex"},
         "startDate": {"year": 2015, "month": 6}, "endDate": {"year": 2015, "month": 8}},
    ],
    "educations": [{"title": "Example Institute", "subtitle": "BTech", "caption": "2012 - 2016"}],
    "posts": [{"text": "Hello", "postUrl": "https://lnkd.in/x", "numLikes": "1,200",
               "numComments": 4, "postedAtISO": "2026-11-01T00:00:00Z"}],
}  # fmt: skip


def test_map_item_handles_common_field_spellings() -> None:
    profile = map_item(REF, ITEM)
    assert profile.full_name == "Asha Verma"
    assert profile.location == "Pune, India"
    assert {(c.type, c.value) for c in profile.contacts} == {
        ("email", "asha@example.com"),
        ("phone", "+91 98000 00000"),
        ("website", "https://asha.example.dev"),
    }
    current, past, intern = profile.experiences
    assert (current.company, current.start_date, current.is_current) == (
        "Northwind Labs", date(2022, 1, 1), True,
    )  # fmt: skip
    assert (past.company, past.start_date, past.end_date, past.is_current) == (
        "Acme", date(2016, 10, 1), date(2019, 6, 1), False,
    )  # fmt: skip
    assert (intern.title, intern.company, intern.start_date, intern.end_date) == (
        "Intern", "Globex", date(2015, 6, 1), date(2015, 8, 1),
    )  # fmt: skip
    assert (profile.educations[0].school, profile.educations[0].end_year) == (
        "Example Institute", 2016,
    )  # fmt: skip
    assert profile.activities[0].reactions_count == 1200
    assert profile.raw == ITEM


def _provider(handler: httpx.MockTransport) -> ApifyProvider:
    client = httpx.AsyncClient(transport=handler, base_url="https://api.apify.com/v2")
    return ApifyProvider(token="t", actor_id="someone/actor", client=client)


async def test_fetch_sends_url_and_maps_first_item() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = request.content
        return httpx.Response(200, json=[ITEM])

    profile = await _provider(httpx.MockTransport(handler)).fetch(REF)
    assert seen["path"] == "/v2/acts/someone~actor/run-sync-get-dataset-items"
    assert b"https://www.linkedin.com/in/asha-verma/" in seen["body"]  # type: ignore[operator]
    assert profile.full_name == "Asha Verma"


@pytest.mark.parametrize(
    ("status", "body", "error"),
    [
        (200, [], ProfileNotFound),
        (401, {}, ProviderNeedsAttention),
        (429, {}, ProviderTransientError),
        (503, {}, ProviderTransientError),
    ],
)
async def test_fetch_error_mapping(status: int, body: object, error: type[Exception]) -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(status, json=body))
    with pytest.raises(error):
        await _provider(transport).fetch(REF)
