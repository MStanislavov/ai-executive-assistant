"""Dashboard page: profile cards and recent runs."""

import json
from pathlib import Path

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.profile import UserProfile
from app.models.run import Run

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


def _parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


@router.get("/")
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    profiles = (
        await db.execute(select(UserProfile).order_by(UserProfile.created_at))
    ).scalars().all()

    recent_runs = (
        await db.execute(select(Run).order_by(Run.created_at.desc()).limit(10))
    ).scalars().all()

    # Build a profile name lookup for the runs table
    profile_names = {p.id: p.name for p in profiles}

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "profiles": profiles,
        "recent_runs": recent_runs,
        "profile_names": profile_names,
        "parse_json_list": _parse_json_list,
    })
