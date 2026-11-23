"""One-time manual LinkedIn sign-in for the playwright provider.

    cd backend && uv run python -m scripts.linkedin_login      (or: make login)

Opens a visible browser on the LinkedIn login page. You type your own
credentials (and any 2FA / verification) in that window. Nothing is read or
stored by this script except the browser profile directory, which keeps your
session cookies locally in `backend/.linkedin-session/` (git-ignored).
Delete that directory to sign out.
"""

import asyncio

from playwright.async_api import async_playwright

from app.core.config import get_settings

LOGIN_URL = "https://www.linkedin.com/login"
WAIT_MINUTES = 10


async def main() -> None:
    settings = get_settings()
    settings.playwright_user_data_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            str(settings.playwright_user_data_dir),
            headless=False,
            channel=settings.playwright_channel,
            viewport={"width": 1280, "height": 900},
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(LOGIN_URL)
        print(f"Sign in to LinkedIn in the browser window (waiting up to {WAIT_MINUTES} min)...")
        try:
            await page.wait_for_url("**/feed/**", timeout=WAIT_MINUTES * 60 * 1000)
        except Exception:
            print("Did not reach the LinkedIn feed — session not confirmed. Run again to retry.")
        else:
            # Give the browser a moment to write the session cookies to disk.
            await page.wait_for_timeout(5_000)
            names = {c["name"] for c in await context.cookies("https://www.linkedin.com")}
            if "li_at" in names:
                print(f"Signed in. Session saved to {settings.playwright_user_data_dir}")
            else:
                print("Reached the feed but no session cookie was stored. Run again to retry.")
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
