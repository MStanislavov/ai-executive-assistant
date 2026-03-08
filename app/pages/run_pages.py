"""Run list and detail pages."""

import json
from pathlib import Path

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.engine.audit_writer import AuditWriter
from app.models.profile import UserProfile
from app.models.run import Run

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "templates"))


@router.get("/profiles/{profile_id}/runs")
async def runs_list_page(profile_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    profile = await db.get(UserProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    runs = (
        await db.execute(
            select(Run)
            .where(Run.profile_id == profile_id)
            .order_by(Run.created_at.desc())
        )
    ).scalars().all()

    all_profiles = (
        await db.execute(select(UserProfile).order_by(UserProfile.created_at))
    ).scalars().all()

    return templates.TemplateResponse("runs_list.html", {
        "request": request,
        "profile": profile,
        "profiles": all_profiles,
        "runs": runs,
    })


@router.get("/profiles/{profile_id}/runs/{run_id}")
async def run_detail_page(
    profile_id: str,
    run_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    profile = await db.get(UserProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    run = await db.get(Run, run_id)
    if run is None or run.profile_id != profile_id:
        raise HTTPException(status_code=404, detail="Run not found")

    # Load audit events and verifier report
    writer = AuditWriter(artifacts_dir=settings.artifacts_dir)
    audit_events = writer.read_log(run_id)
    bundle = writer.read_bundle(run_id)
    verifier_report = bundle.get("verifier_report", {}) if bundle else {}

    all_profiles = (
        await db.execute(select(UserProfile).order_by(UserProfile.created_at))
    ).scalars().all()

    return templates.TemplateResponse("run_detail.html", {
        "request": request,
        "profile": profile,
        "profiles": all_profiles,
        "run": run,
        "audit_events": audit_events,
        "verifier_report": verifier_report,
        "bundle": bundle,
    })
