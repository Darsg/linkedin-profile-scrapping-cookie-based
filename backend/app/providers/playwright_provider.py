"""Browser provider: reads profiles through *your own* logged-in LinkedIn session.

How it behaves, on purpose:
  * It never logs in. `scripts/linkedin_login.py` opens a visible browser where you
    sign in by hand; the session is kept in a local, git-ignored profile directory.
  * One profile at a time, with a minimum gap and a daily cap (see `Pacer`).
  * If LinkedIn shows a login wall, checkpoint or verification challenge it stops and
    marks the job `needs_attention`. It does not try to get around them.
"""

import asyncio
import contextlib
from pathlib import Path

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeout

from app.providers.base import (
    ProfileNotFound,
    ProviderNeedsAttention,
    ProviderTransientError,
    ScrapedProfile,
)
from app.providers.linkedin import parsers
from app.providers.linkedin.pacing import Pacer
from app.utils.linkedin_url import ProfileRef

_BLOCKED_PATHS = ("/login", "/uas/login", "/authwall", "/checkpoint", "/signup")
_NAV_TIMEOUT_MS = 30_000


class PlaywrightProvider:
    name = "playwright"

    def __init__(
        self,
        user_data_dir: Path,
        pacer: Pacer,
        headless: bool = True,
        channel: str | None = None,
        max_activities: int = 10,
    ) -> None:
        self._user_data_dir = user_data_dir
        self._pacer = pacer
        self._headless = headless
        self._channel = channel
        self._max_activities = max_activities
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._lock = asyncio.Lock()  # one page at a time per browser session

    async def _ensure_context(self) -> BrowserContext:
        if self._context is None:
            if not self._user_data_dir.exists():
                raise ProviderNeedsAttention(
                    "No LinkedIn session found. Run `make login` and sign in once."
                )
            self._playwright = await async_playwright().start()
            self._context = await self._playwright.chromium.launch_persistent_context(
                str(self._user_data_dir),
                headless=self._headless,
                channel=self._channel,
                viewport={"width": 1280, "height": 900},
            )
            self._context.set_default_timeout(_NAV_TIMEOUT_MS)
        return self._context

    async def fetch(self, ref: ProfileRef) -> ScrapedProfile:
        async with self._lock:
            await self._pacer.wait_turn()
            try:
                context = await self._ensure_context()
                page = await context.new_page()
            except PlaywrightError as exc:
                raise ProviderTransientError(f"Could not start the browser: {exc}") from exc
            try:
                return await self._scrape(page, ref)
            except PlaywrightTimeout as exc:
                raise ProviderTransientError(f"Timed out loading LinkedIn: {exc}") from exc
            except PlaywrightError as exc:
                raise ProviderTransientError(f"Browser error: {exc}") from exc
            finally:
                await page.close()

    async def _scrape(self, page: Page, ref: ProfileRef) -> ScrapedProfile:
        base = ref.url.rstrip("/")

        # About is mounted a moment after the top card; wait for it rather than scroll,
        # because the page is a virtual list that unmounts sections scrolled out of view.
        main_html = await self._open(
            page,
            f"{base}/",
            wait_for="main h2, main h1",
            then_wait_for='main [data-testid="expandable-text-box"], #about',
        )
        top = parsers.parse_top_card(main_html)
        if not top["full_name"]:
            raise ProviderTransientError("Profile page loaded but no name was found")

        contact_html = await self._open(
            page,
            f"{base}/overlay/contact-info/",
            wait_for='[data-testid="dialog-content"], section.pv-contact-info__contact-type',
        )
        experience_html = await self._open(page, f"{base}/details/experience/", scroll=True)
        education_html = await self._open(page, f"{base}/details/education/", scroll=True)
        activity_html = await self._open(page, f"{base}/recent-activity/all/", scroll=True)

        return ScrapedProfile(
            public_id=ref.public_id,
            url=ref.url,
            full_name=top["full_name"],
            headline=top["headline"],
            location=top["location"],
            about=top["about"],
            photo_url=top["photo_url"],
            contacts=parsers.parse_contact_info(contact_html),
            experiences=parsers.parse_experiences(experience_html),
            educations=parsers.parse_educations(education_html),
            activities=parsers.parse_activities(activity_html, limit=self._max_activities),
            raw={"source": "playwright", "top_card": top},
        )

    async def _open(
        self,
        page: Page,
        url: str,
        wait_for: str | None = None,
        scroll: bool = False,
        then_wait_for: str | None = None,
    ) -> str:
        response = await page.goto(url, wait_until="domcontentloaded")
        self._check_blocked(page)
        if (response is not None and response.status == 404) or "/404" in page.url:
            raise ProfileNotFound("LinkedIn says this profile does not exist")

        if wait_for:
            try:
                await page.wait_for_selector(wait_for, timeout=10_000)
            except PlaywrightTimeout:
                self._check_blocked(page)  # optional sections may simply be absent
        else:
            await page.wait_for_timeout(2_000)

        if then_wait_for:  # optional content: carry on if it never shows up
            with contextlib.suppress(PlaywrightTimeout):
                await page.wait_for_selector(then_wait_for, timeout=8_000)

        if scroll:  # these pages load their lists lazily as you scroll
            for _ in range(3):
                await page.mouse.wheel(0, 2_000)
                await page.wait_for_timeout(1_200)
        self._check_blocked(page)
        return await page.content()

    @staticmethod
    def _check_blocked(page: Page) -> None:
        path = page.url.split("linkedin.com", 1)[-1]
        if any(path.startswith(blocked) for blocked in _BLOCKED_PATHS):
            raise ProviderNeedsAttention(
                "LinkedIn asked for a login or verification. Run `make login`, sign in or "
                "complete the check yourself in the browser window, then retry the job."
            )

    async def close(self) -> None:
        if self._context is not None:
            await self._context.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self._context = self._playwright = None
