from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import health, profiles, scrape_jobs
from app.core.config import get_settings
from app.core.db import get_engine
from app.core.logging import configure_logging
from app.core.queue import ArqJobQueue


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Tests inject their own queue before startup.
    owns_queue = getattr(app.state, "queue", None) is None
    if owns_queue:
        app.state.queue = await ArqJobQueue.connect()
    yield
    if owns_queue:
        await app.state.queue.close()
    await get_engine().dispose()


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title="LinkedIn Profile Scraper", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(health.router)
    v1.include_router(scrape_jobs.router)
    v1.include_router(profiles.router)
    app.include_router(v1)
    return app


app = create_app()
