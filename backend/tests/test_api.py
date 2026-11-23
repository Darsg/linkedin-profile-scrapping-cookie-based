import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.providers.mock_provider import MockProvider
from app.services.scrape_service import ScrapeService
from tests.conftest import InMemoryQueue

API = "/api/v1"
URL = "https://www.linkedin.com/in/jane-doe-123/"


async def _run(session: AsyncSession, job_id: str) -> None:
    """What the worker does for one job."""
    await ScrapeService(session, get_settings()).execute(
        uuid.UUID(job_id), MockProvider(), attempt=1
    )


async def test_health(client: AsyncClient) -> None:
    response = await client.get(f"{API}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": True, "queue": True, "provider": "mock"}


async def test_submit_queues_job(client: AsyncClient, queue: InMemoryQueue) -> None:
    response = await client.post(f"{API}/scrape-jobs", json={"url": "linkedin.com/in/Jane-Doe-123"})
    assert response.status_code == 202
    job = response.json()
    assert (job["status"], job["public_id"], job["profile_id"]) == ("queued", "jane-doe-123", None)
    assert queue.enqueued == [(uuid.UUID(job["id"]), "mock")]


async def test_invalid_url_is_rejected_and_nothing_queued(
    client: AsyncClient, queue: InMemoryQueue
) -> None:
    response = await client.post(f"{API}/scrape-jobs", json={"url": "https://example.com/in/x"})
    assert response.status_code == 422
    assert queue.enqueued == []
    assert (await client.get(f"{API}/scrape-jobs")).json()["total"] == 0


async def test_full_flow_then_cache_then_force(
    client: AsyncClient, queue: InMemoryQueue, session: AsyncSession
) -> None:
    job = (await client.post(f"{API}/scrape-jobs", json={"url": URL})).json()
    await _run(session, job["id"])

    done = (await client.get(f"{API}/scrape-jobs/{job['id']}")).json()
    assert (done["status"], done["attempts"], done["from_cache"]) == ("succeeded", 1, False)

    profile = (await client.get(f"{API}/profiles/{done['profile_id']}")).json()
    assert profile["full_name"] == "Jane Doe"
    assert len(profile["experiences"]) == 2 and profile["experiences"][0]["is_current"]
    assert {c["type"] for c in profile["contacts"]} == {"email", "website"}
    assert len(profile["educations"]) == 1 and len(profile["activities"]) == 2

    # Same profile again: served from the stored copy, no new queue entry.
    cached = (await client.post(f"{API}/scrape-jobs", json={"url": URL})).json()
    assert (cached["status"], cached["from_cache"]) == ("succeeded", True)
    assert cached["profile_id"] == done["profile_id"]
    assert len(queue.enqueued) == 1

    # force=true re-scrapes and still leaves exactly one profile row.
    forced = (await client.post(f"{API}/scrape-jobs", json={"url": URL, "force": True})).json()
    assert forced["status"] == "queued" and len(queue.enqueued) == 2
    await _run(session, forced["id"])
    listing = (await client.get(f"{API}/profiles")).json()
    assert listing["total"] == 1
    again = (await client.get(f"{API}/profiles/{done['profile_id']}")).json()
    assert len(again["experiences"]) == 2  # children replaced, not duplicated


async def test_search_refresh_delete(
    client: AsyncClient, queue: InMemoryQueue, session: AsyncSession
) -> None:
    for slug in ("jane-doe-123", "ravi-kumar"):
        job = (
            await client.post(
                f"{API}/scrape-jobs", json={"url": f"https://www.linkedin.com/in/{slug}"}
            )
        ).json()
        await _run(session, job["id"])

    found = (await client.get(f"{API}/profiles", params={"q": "ravi"})).json()
    assert [p["public_id"] for p in found["items"]] == ["ravi-kumar"]
    profile_id = found["items"][0]["id"]

    refresh = await client.post(f"{API}/profiles/{profile_id}/refresh")
    assert refresh.status_code == 202 and refresh.json()["status"] == "queued"

    assert (await client.delete(f"{API}/profiles/{profile_id}")).status_code == 204
    assert (await client.get(f"{API}/profiles/{profile_id}")).status_code == 404
    assert (await client.get(f"{API}/profiles")).json()["total"] == 1
    # Job history survives, with the profile link cleared.
    jobs = (await client.get(f"{API}/scrape-jobs", params={"status": "succeeded"})).json()
    assert jobs["total"] == 2
    assert sum(j["profile_id"] is None for j in jobs["items"]) == 1


async def test_unknown_ids_return_404(client: AsyncClient) -> None:
    missing = uuid.uuid4()
    assert (await client.get(f"{API}/scrape-jobs/{missing}")).status_code == 404
    assert (await client.get(f"{API}/profiles/{missing}")).status_code == 404
    assert (await client.delete(f"{API}/profiles/{missing}")).status_code == 404
