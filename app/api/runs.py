"""Run lifecycle API: create, list, get, stream, cancel."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.db import get_db, async_session_factory
from app.models.run import Run
from app.models.profile import UserProfile
from app.schemas.run import RunCreate, RunRead
from app.sse import event_manager

router = APIRouter(tags=["runs"])

# In-memory store for background tasks (for cancellation)
_running_tasks: dict[str, asyncio.Task] = {}


def _run_to_read(run: Run) -> RunRead:
    return RunRead(
        id=run.id,
        profile_id=run.profile_id,
        mode=run.mode,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        verifier_status=run.verifier_status,
        audit_path=run.audit_path,
    )


async def _execute_run(run_id: str, profile_id: str, mode: str) -> None:
    """Background task that executes the LangGraph pipeline."""
    from app.engine.policy_engine import PolicyEngine
    from app.engine.audit_writer import AuditWriter, AuditEvent
    from app.graphs.daily import build_daily_graph
    from app.graphs.weekly import build_weekly_graph
    from app.graphs.cover_letter import build_cover_letter_graph

    try:
        async with async_session_factory() as session:
            run = await session.get(Run, run_id)
            if run is None:
                return
            run.status = "running"
            run.started_at = datetime.now(timezone.utc)
            await session.commit()

        await event_manager.publish(run_id, {
            "type": "run_started",
            "run_id": run_id,
            "mode": mode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Build and run graph
        policy_engine = PolicyEngine(settings.policy_dir)
        audit_writer = AuditWriter(
            artifacts_dir=settings.artifacts_dir, policy_engine=policy_engine
        )

        audit_writer.append(
            run_id,
            AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="agent_start",
                agent="daily_pipeline",
                data={"mode": mode, "profile_id": profile_id},
            ),
        )

        if mode == "daily":
            graph = build_daily_graph(
                policy_engine=policy_engine, audit_writer=audit_writer
            )
        elif mode == "weekly":
            graph = build_weekly_graph(
                policy_engine=policy_engine, audit_writer=audit_writer
            )
        elif mode == "cover_letter":
            graph = build_cover_letter_graph(
                policy_engine=policy_engine, audit_writer=audit_writer
            )
        else:
            graph = build_daily_graph(
                policy_engine=policy_engine, audit_writer=audit_writer
            )

        compiled = graph.compile()

        initial_state = {
            "profile_id": profile_id,
            "profile_targets": [],
            "source_config": {},
            "run_id": run_id,
            "errors": [],
            "safe_degradation": False,
            "audit_events": [],
        }

        result = await asyncio.to_thread(compiled.invoke, initial_state)

        verifier_status = result.get("verifier_report", {}).get(
            "overall_status", "unknown"
        )

        async with async_session_factory() as session:
            run = await session.get(Run, run_id)
            if run:
                run.status = "completed"
                run.finished_at = datetime.now(timezone.utc)
                run.verifier_status = verifier_status
                run.audit_path = str(settings.artifacts_dir / "runs" / run_id)
                await session.commit()

        await event_manager.publish(run_id, {
            "type": "run_finished",
            "run_id": run_id,
            "status": "completed",
            "verifier_status": verifier_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    except asyncio.CancelledError:
        async with async_session_factory() as session:
            run = await session.get(Run, run_id)
            if run:
                run.status = "cancelled"
                run.finished_at = datetime.now(timezone.utc)
                await session.commit()
        await event_manager.publish(run_id, {
            "type": "run_cancelled",
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    except Exception as exc:
        async with async_session_factory() as session:
            run = await session.get(Run, run_id)
            if run:
                run.status = "failed"
                run.finished_at = datetime.now(timezone.utc)
                await session.commit()
        await event_manager.publish(run_id, {
            "type": "run_failed",
            "run_id": run_id,
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    finally:
        await event_manager.close(run_id)
        _running_tasks.pop(run_id, None)


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@router.post("/profiles/{profile_id}/runs", response_model=RunRead, status_code=201)
async def create_run(
    profile_id: str,
    body: RunCreate,
    db: AsyncSession = Depends(get_db),
) -> RunRead:
    """Create a new run and launch the pipeline in the background."""
    profile = await db.get(UserProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    run = Run(
        profile_id=profile_id,
        mode=body.mode,
        status="pending",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    task = asyncio.create_task(
        _execute_run(run.id, profile_id, body.mode)
    )
    _running_tasks[run.id] = task

    return _run_to_read(run)


@router.get("/profiles/{profile_id}/runs", response_model=list[RunRead])
async def list_runs(
    profile_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[RunRead]:
    """List all runs for a profile, most recent first."""
    result = await db.execute(
        select(Run)
        .where(Run.profile_id == profile_id)
        .order_by(Run.created_at.desc())
    )
    runs = result.scalars().all()
    return [_run_to_read(r) for r in runs]


@router.get("/profiles/{profile_id}/runs/{run_id}", response_model=RunRead)
async def get_run(
    profile_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> RunRead:
    """Get details of a single run."""
    run = await db.get(Run, run_id)
    if run is None or run.profile_id != profile_id:
        raise HTTPException(status_code=404, detail="Run not found")
    return _run_to_read(run)


@router.get("/profiles/{profile_id}/runs/{run_id}/stream")
async def stream_run(profile_id: str, run_id: str):
    """SSE stream of run progress events."""
    return EventSourceResponse(event_manager.event_stream(run_id))


@router.post("/profiles/{profile_id}/runs/{run_id}/cancel")
async def cancel_run(
    profile_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running task."""
    run = await db.get(Run, run_id)
    if run is None or run.profile_id != profile_id:
        raise HTTPException(status_code=404, detail="Run not found")

    task = _running_tasks.get(run_id)
    if task is None or task.done():
        raise HTTPException(status_code=409, detail="Run is not currently executing")

    task.cancel()
    return {"detail": "Cancellation requested", "run_id": run_id}
