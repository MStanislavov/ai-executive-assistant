"""Audit API: audit trail, verifier report, replay, and diff endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal

from app.config import settings
from app.engine.audit_writer import AuditWriter
from app.engine.diff import DiffEngine
from app.engine.replay import ReplayEngine

router = APIRouter(tags=["audit"])


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------


class ReplayRequest(BaseModel):
    mode: Literal["strict", "refresh"]


class ReplayResponse(BaseModel):
    run_id: str
    replay_mode: str
    original_run_id: str
    result: dict
    verifier_report: dict
    drift: list


class DiffResponse(BaseModel):
    run_a: str
    run_b: str
    additions: list
    removals: list
    changes: list
    summary: dict


# ------------------------------------------------------------------
# Existing endpoints
# ------------------------------------------------------------------


@router.get("/profiles/{profile_id}/runs/{run_id}/audit")
async def get_audit_trail(profile_id: str, run_id: str):
    """Return the full audit event log for a run."""
    writer = AuditWriter(artifacts_dir=settings.artifacts_dir)
    events = writer.read_log(run_id)
    return {"run_id": run_id, "events": events}


@router.get("/profiles/{profile_id}/runs/{run_id}/verifier-report")
async def get_verifier_report(profile_id: str, run_id: str):
    """Return the verifier report from the run bundle."""
    writer = AuditWriter(artifacts_dir=settings.artifacts_dir)
    bundle = writer.read_bundle(run_id)
    if bundle is None:
        raise HTTPException(
            status_code=404, detail="No audit bundle found for this run"
        )
    return bundle.get("verifier_report", {})


# ------------------------------------------------------------------
# Replay endpoint
# ------------------------------------------------------------------


@router.post(
    "/profiles/{profile_id}/runs/{run_id}/replay",
    response_model=ReplayResponse,
)
async def replay_run(profile_id: str, run_id: str, body: ReplayRequest):
    """Replay a previous run in strict or refresh mode.

    - **strict**: re-use stored tool responses (no network calls).
    - **refresh**: re-execute the graph live and compare for drift.

    In Phase 1 (mock agents) both modes produce identical results.
    """
    writer = AuditWriter(artifacts_dir=settings.artifacts_dir)
    replay_engine = ReplayEngine(audit_writer=writer)

    new_run_id = str(uuid.uuid4())

    try:
        if body.mode == "strict":
            result = replay_engine.replay_strict(
                original_run_id=run_id,
                new_run_id=new_run_id,
            )
        else:
            # Refresh mode: in Phase 1 mock agents produce the same data,
            # so we load the original artifacts as the "fresh" result and
            # compare.  When real agents are wired up, this path will
            # execute the graph instead.
            bundle = writer.read_bundle(run_id)
            if bundle is None:
                raise HTTPException(
                    status_code=404,
                    detail="No audit bundle found for this run",
                )
            new_result = bundle.get("final_artifacts", {})
            result = replay_engine.replay_refresh(
                original_run_id=run_id,
                new_run_id=new_run_id,
                new_result=new_result,
            )

        # Persist the replay bundle
        writer.create_run_bundle(
            run_id=new_run_id,
            profile_hash=profile_id,
            policy_version_hash="",
            verifier_report=result.get("verifier_report", {}),
            final_artifacts=result.get("result", {}),
        )

        return result

    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ------------------------------------------------------------------
# Diff endpoint
# ------------------------------------------------------------------


@router.get(
    "/profiles/{profile_id}/runs/{run_id}/diff/{other_run_id}",
    response_model=DiffResponse,
)
async def diff_runs(profile_id: str, run_id: str, other_run_id: str):
    """Return a structured diff between two runs."""
    writer = AuditWriter(artifacts_dir=settings.artifacts_dir)
    diff_engine = DiffEngine(audit_writer=writer)

    try:
        return diff_engine.diff_runs(run_id, other_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
