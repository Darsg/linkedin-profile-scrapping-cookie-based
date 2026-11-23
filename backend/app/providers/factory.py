from redis.asyncio import Redis

from app.core.config import Settings
from app.providers.base import ProfileProvider


class ProviderConfigError(RuntimeError):
    pass


def build_provider(settings: Settings, redis: Redis | None = None) -> ProfileProvider:
    """Create the provider selected by PROVIDER. Imports are local so a worker only
    loads what it uses (e.g. no Playwright import for the API provider)."""
    if settings.provider == "mock":
        from app.providers.mock_provider import MockProvider

        return MockProvider(delay_seconds=settings.mock_delay_seconds)

    if settings.provider == "api":
        from app.providers.api_provider import ApifyProvider

        if not settings.apify_token or not settings.apify_actor_id:
            raise ProviderConfigError("PROVIDER=api needs APIFY_TOKEN and APIFY_ACTOR_ID")
        return ApifyProvider(
            token=settings.apify_token,
            actor_id=settings.apify_actor_id,
            input_field=settings.apify_input_field,
            timeout_seconds=settings.apify_timeout_seconds,
        )

    if settings.provider == "playwright":
        from app.providers.linkedin.pacing import Pacer
        from app.providers.playwright_provider import PlaywrightProvider

        return PlaywrightProvider(
            user_data_dir=settings.playwright_user_data_dir,
            headless=settings.playwright_headless,
            channel=settings.playwright_channel,
            max_activities=settings.playwright_max_activities,
            pacer=Pacer(
                redis=redis,
                min_delay_seconds=settings.playwright_min_delay_seconds,
                daily_cap=settings.playwright_daily_cap,
            ),
        )

    raise ProviderConfigError(f"Unknown provider {settings.provider!r}")
