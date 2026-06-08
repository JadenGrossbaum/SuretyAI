from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.config import get_settings
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _ = app
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version='0.1.0',
        description=(
            'Backend foundation for surety bond lead intake. '
            'This system collects preliminary information for human review only.'
        ),
        lifespan=lifespan,
    )
    app.include_router(health_router)
    return app


app = create_app()
