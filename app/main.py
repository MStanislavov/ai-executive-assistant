from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import profiles, runs, audit, opportunities, cover_letters, policies
from app.db import engine, Base
from app.pages import dashboard, profile_pages, run_pages, opportunity_pages, cover_letter_pages, policy_pages

# Import all models so Base.metadata knows about them
import app.models


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="AI Executive Assistant Network", lifespan=lifespan)

# Static files and templates
static_dir = Path(__file__).parent.parent / "static"
templates_dir = Path(__file__).parent.parent / "templates"
static_dir.mkdir(parents=True, exist_ok=True)
templates_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# JSON API routers
app.include_router(profiles.router, prefix="/api")
app.include_router(runs.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(opportunities.router, prefix="/api")
app.include_router(cover_letters.router, prefix="/api")
app.include_router(policies.router, prefix="/api")

# HTML page routers
app.include_router(dashboard.router)
app.include_router(profile_pages.router)
app.include_router(run_pages.router)
app.include_router(opportunity_pages.router)
app.include_router(cover_letter_pages.router)
app.include_router(policy_pages.router)


if __name__ == "__main__":
    import uvicorn

    from app.config import settings as _settings

    uvicorn.run(
        "app.main:app",
        host=_settings.app_host,
        port=_settings.app_port,
        reload=_settings.app_reload,
    )
