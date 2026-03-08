"""Cover letter API: create, list, get."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db, async_session_factory
from app.models.cover_letter import CoverLetter
from app.models.opportunity import Opportunity
from app.models.profile import UserProfile
from app.models.run import Run
from app.schemas.cover_letter import CoverLetterCreate, CoverLetterRead

router = APIRouter(tags=["cover-letters"])


def _cl_to_read(cl: CoverLetter) -> CoverLetterRead:
    evidence_ids: list[str] = []
    if cl.evidence_ids_json:
        try:
            evidence_ids = json.loads(cl.evidence_ids_json)
        except (json.JSONDecodeError, TypeError):
            pass
    return CoverLetterRead(
        id=cl.id,
        profile_id=cl.profile_id,
        opportunity_id=cl.opportunity_id,
        run_id=cl.run_id,
        content=cl.content,
        evidence_ids=evidence_ids,
        created_at=cl.created_at,
    )


async def _generate_cover_letter(
    run_id: str,
    profile_id: str,
    cover_letter_id: str,
    cv_content: str,
    jd_text: str,
    opportunity: dict,
    opportunity_id: str | None,
) -> None:
    """Background task: run the cover letter LangGraph pipeline and persist result."""
    from app.engine.policy_engine import PolicyEngine
    from app.engine.audit_writer import AuditWriter, AuditEvent
    from app.graphs.cover_letter import build_cover_letter_graph

    try:
        async with async_session_factory() as session:
            run = await session.get(Run, run_id)
            if run:
                run.status = "running"
                run.started_at = datetime.now(timezone.utc)
                await session.commit()

        policy_engine = PolicyEngine(settings.policy_dir)
        audit_writer = AuditWriter(
            artifacts_dir=settings.artifacts_dir, policy_engine=policy_engine
        )

        audit_writer.append(
            run_id,
            AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="agent_start",
                agent="cover_letter_pipeline",
                data={"profile_id": profile_id, "opportunity_id": opportunity_id},
            ),
        )

        graph = build_cover_letter_graph(
            policy_engine=policy_engine, audit_writer=audit_writer
        )
        compiled = graph.compile()

        initial_state = {
            "profile_id": profile_id,
            "cv_content": cv_content,
            "jd_text": jd_text,
            "opportunity": opportunity,
            "run_id": run_id,
            "errors": [],
            "audit_events": [],
        }

        result = await asyncio.to_thread(compiled.invoke, initial_state)

        verifier_status = result.get("verifier_report", {}).get(
            "overall_status", "unknown"
        )
        content = result.get("cover_letter_content", "")
        evidence_items = result.get("evidence_items", [])
        evidence_ids = [e["id"] for e in evidence_items]

        async with async_session_factory() as session:
            # Update cover letter record
            cl = await session.get(CoverLetter, cover_letter_id)
            if cl:
                cl.content = content
                cl.evidence_ids_json = json.dumps(evidence_ids)

            # Update run record
            run = await session.get(Run, run_id)
            if run:
                run.status = "completed"
                run.finished_at = datetime.now(timezone.utc)
                run.verifier_status = verifier_status
                run.audit_path = str(settings.artifacts_dir / "runs" / run_id)

            await session.commit()

    except Exception:
        async with async_session_factory() as session:
            run = await session.get(Run, run_id)
            if run:
                run.status = "failed"
                run.finished_at = datetime.now(timezone.utc)
                await session.commit()


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@router.post(
    "/profiles/{profile_id}/cover-letters",
    response_model=CoverLetterRead,
    status_code=201,
)
async def create_cover_letter(
    profile_id: str,
    body: CoverLetterCreate,
    db: AsyncSession = Depends(get_db),
) -> CoverLetterRead:
    """Generate a cover letter from an opportunity or raw JD text."""
    profile = await db.get(UserProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    if not body.opportunity_id and not body.jd_text:
        raise HTTPException(
            status_code=422,
            detail="Either opportunity_id or jd_text must be provided",
        )

    # Resolve opportunity details
    opportunity: dict = {}
    jd_text = body.jd_text or ""
    opportunity_id = body.opportunity_id

    if opportunity_id:
        opp = await db.get(Opportunity, opportunity_id)
        if opp is None or opp.profile_id != profile_id:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        opportunity = {
            "title": opp.title,
            "source": opp.source,
            "url": opp.url,
            "description": opp.description,
            "opportunity_type": opp.opportunity_type,
        }
        if not jd_text:
            jd_text = opp.description or opp.title

    cv_content = ""
    if profile.cv_path:
        try:
            with open(profile.cv_path, encoding="utf-8") as f:
                cv_content = f.read()
        except (OSError, UnicodeDecodeError):
            cv_content = ""
    if not cv_content and profile.skills:
        cv_content = profile.skills

    # Create run record
    run = Run(profile_id=profile_id, mode="cover_letter", status="pending")
    db.add(run)
    await db.flush()

    # Create cover letter record (content filled after pipeline runs)
    cl = CoverLetter(
        profile_id=profile_id,
        opportunity_id=opportunity_id,
        run_id=run.id,
        content="",
    )
    db.add(cl)
    await db.commit()
    await db.refresh(cl)
    await db.refresh(run)

    # Launch pipeline in background
    asyncio.create_task(
        _generate_cover_letter(
            run_id=run.id,
            profile_id=profile_id,
            cover_letter_id=cl.id,
            cv_content=cv_content,
            jd_text=jd_text,
            opportunity=opportunity,
            opportunity_id=opportunity_id,
        )
    )

    return _cl_to_read(cl)


@router.get(
    "/profiles/{profile_id}/cover-letters",
    response_model=list[CoverLetterRead],
)
async def list_cover_letters(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[CoverLetterRead]:
    """List all cover letters for a profile."""
    result = await db.execute(
        select(CoverLetter)
        .where(CoverLetter.profile_id == profile_id)
        .order_by(CoverLetter.created_at.desc())
    )
    return [_cl_to_read(cl) for cl in result.scalars().all()]


@router.get(
    "/profiles/{profile_id}/cover-letters/{letter_id}",
    response_model=CoverLetterRead,
)
async def get_cover_letter(
    profile_id: str,
    letter_id: str,
    db: AsyncSession = Depends(get_db),
) -> CoverLetterRead:
    """Get a single cover letter with evidence refs."""
    cl = await db.get(CoverLetter, letter_id)
    if cl is None or cl.profile_id != profile_id:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    return _cl_to_read(cl)
