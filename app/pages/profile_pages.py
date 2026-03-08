"""Profile detail page: edit form with HTMX."""

import json
from pathlib import Path

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.profile import UserProfile

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


def _parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


@router.get("/profiles/{profile_id}")
async def profile_page(profile_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    profile = await db.get(UserProfile, profile_id)
    if profile is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Profile not found")

    # Get all profiles for the sidebar switcher
    all_profiles = (
        await db.execute(select(UserProfile).order_by(UserProfile.created_at))
    ).scalars().all()

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "profile": profile,
        "profiles": all_profiles,
        "targets": _parse_json_list(profile.targets),
        "constraints": _parse_json_list(profile.constraints),
        "skills": _parse_json_list(profile.skills),
    })
