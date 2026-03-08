"""Opportunities list page (stub, populated after Step 5)."""

from pathlib import Path

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.profile import UserProfile
from app.models.run import Artifact

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


@router.get("/profiles/{profile_id}/opportunities")
async def opportunities_page(profile_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    profile = await db.get(UserProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Fetch artifacts of type "opportunity" for this profile
    artifacts = (
        await db.execute(
            select(Artifact)
            .where(Artifact.profile_id == profile_id, Artifact.artifact_type == "opportunity")
            .order_by(Artifact.created_at.desc())
        )
    ).scalars().all()

    all_profiles = (
        await db.execute(select(UserProfile).order_by(UserProfile.created_at))
    ).scalars().all()

    return templates.TemplateResponse("opportunities.html", {
        "request": request,
        "profile": profile,
        "profiles": all_profiles,
        "opportunities": artifacts,
    })
