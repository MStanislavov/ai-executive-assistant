"""Cover letter business logic: generation, resolution, persistence."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import async_session_factory
from app.engine.audit_writer import AuditEvent, AuditWriter
from app.engine.policy_engine import PolicyEngine
from app.graphs.cover_letter import build_cover_letter_graph
from app.models.cover_letter import CoverLetter
from app.models.job_opportunity import JobOpportunity
from app.models.profile import UserProfile
from app.models.run import Run
from app.schemas.cover_letter import CoverLetterCreate, CoverLetterRead
from app.sse import event_manager

# Prevent background tasks from being garbage-collected
_background_tasks: set[asyncio.Task] = set()


def cl_to_read(cl: CoverLetter) -> CoverLetterRead:
    return CoverLetterRead(
        id=cl.id,
        profile_id=cl.profile_id,
        job_opportunity_id=cl.job_opportunity_id,
        run_id=cl.run_id,
        content=cl.content,
        created_at=cl.created_at,
    )


async def resolve_job_opportunity(
    db: AsyncSession,
    job_opportunity_id: str | None,
    profile_id: str,
    jd_text: str,
) -> tuple[dict, str]:
    """Resolve job opportunity details and JD text from a job opportunity ID.

    Raises LookupError if job_opportunity_id is given but not found.
    """
    job_opportunity: dict = {}
    if not job_opportunity_id:
        return job_opportunity, jd_text
    job = await db.get(JobOpportunity, job_opportunity_id)
    if job is None or job.profile_id != profile_id:
        raise LookupError("Job opportunity not found")
    job_opportunity = {
        "title": job.title,
        "company": job.company,
        "url": job.url,
        "description": job.description,
    }
    if not jd_text:
        jd_text = job.description or job.title
    return job_opportunity, jd_text


async def read_cv_content(profile: UserProfile) -> str:
    """Read CV content from file path or fall back to skills."""
    if profile.cv_path:
        try:
            return await asyncio.to_thread(
                Path(profile.cv_path).read_text, "utf-8"
            )
        except (OSError, UnicodeDecodeError):
            pass
    return profile.skills or ""


async def generate_cover_letter(
    run_id: str,
    profile_id: str,
    cover_letter_id: str,
    cv_content: str,
    jd_text: str,
    job_opportunity: dict,
    job_opportunity_id: str | None,
) -> None:
    """Background task: run the cover letter LangGraph pipeline and persist result."""
    try:
        async with async_session_factory() as session:
            run = await session.get(Run, run_id)
            if run:
                run.status = "running"
                run.started_at = datetime.now(timezone.utc)
                await session.commit()

        await event_manager.publish(run_id, {
            "type": "run_started",
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

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
                data={"profile_id": profile_id, "job_opportunity_id": job_opportunity_id},
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
            "job_opportunity": job_opportunity,
            "run_id": run_id,
            "errors": [],
            "audit_events": [],
        }

        result = await asyncio.to_thread(compiled.invoke, initial_state)
        content = result.get("cover_letter_content", "")

        async with async_session_factory() as session:
            cl = await session.get(CoverLetter, cover_letter_id)
            if cl:
                cl.content = content

            run = await session.get(Run, run_id)
            if run:
                run.status = "completed"
                run.finished_at = datetime.now(timezone.utc)
                run.audit_path = str(settings.artifacts_dir / "runs" / run_id)

            await session.commit()

        await event_manager.publish(run_id, {
            "type": "run_finished",
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    except Exception:
        async with async_session_factory() as session:
            run = await session.get(Run, run_id)
            if run:
                run.status = "failed"
                run.finished_at = datetime.now(timezone.utc)
                await session.commit()

        await event_manager.publish(run_id, {
            "type": "run_failed",
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    finally:
        await event_manager.close(run_id)


async def create_cover_letter(
    db: AsyncSession, profile_id: str, body: CoverLetterCreate
) -> CoverLetterRead:
    """Create a cover letter and launch background generation.

    Raises LookupError if profile/job not found, ValueError if missing input.
    """
    profile = await db.get(UserProfile, profile_id)
    if profile is None:
        raise LookupError("Profile not found")

    if not body.job_opportunity_id and not body.jd_text:
        raise ValueError("Either job_opportunity_id or jd_text must be provided")

    jd_text = body.jd_text or ""
    job_opportunity, jd_text = await resolve_job_opportunity(
        db, body.job_opportunity_id, profile_id, jd_text
    )
    cv_content = await read_cv_content(profile)

    # Create run record
    run = Run(profile_id=profile_id, mode="cover_letter", status="pending")
    db.add(run)
    await db.flush()

    # Create cover letter record (content filled after pipeline runs)
    cl = CoverLetter(
        profile_id=profile_id,
        job_opportunity_id=body.job_opportunity_id,
        run_id=run.id,
        content="",
    )
    db.add(cl)
    await db.commit()
    await db.refresh(cl)
    await db.refresh(run)

    # Launch pipeline in background
    task = asyncio.create_task(
        generate_cover_letter(
            run_id=run.id,
            profile_id=profile_id,
            cover_letter_id=cl.id,
            cv_content=cv_content,
            jd_text=jd_text,
            job_opportunity=job_opportunity,
            job_opportunity_id=body.job_opportunity_id,
        )
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return cl_to_read(cl)


async def list_cover_letters(
    db: AsyncSession, profile_id: str
) -> list[CoverLetterRead]:
    """List all cover letters for a profile."""
    result = await db.execute(
        select(CoverLetter)
        .where(CoverLetter.profile_id == profile_id)
        .order_by(CoverLetter.created_at.desc())
    )
    return [cl_to_read(cl) for cl in result.scalars().all()]


async def get_cover_letter(
    db: AsyncSession, profile_id: str, letter_id: str
) -> CoverLetterRead | None:
    """Return CoverLetterRead or None if not found."""
    cl = await db.get(CoverLetter, letter_id)
    if cl is None or cl.profile_id != profile_id:
        return None
    return cl_to_read(cl)
