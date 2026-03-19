"""Unified pipeline logging helpers.

All pipeline-internal logs use DEBUG level, so they only appear when
the caller (or root logger) is configured at DEBUG.  Warnings (e.g.,
safe degradation, verifier errors) use WARNING.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from contextlib import contextmanager
from typing import Any, Generator

from app.agents.base import AgentProtocol

logger = logging.getLogger("app.graphs.pipeline")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


@contextmanager
def _timed() -> Generator[dict[str, float], None, None]:
    ctx: dict[str, float] = {"start": time.monotonic()}
    yield ctx
    ctx["elapsed"] = time.monotonic() - ctx["start"]


def _rid(state: dict[str, Any]) -> str:
    return state.get("run_id", "?")


def node_start(pipeline: str, state: dict[str, Any], node: str, **kw: Any) -> None:
    extra = " ".join(f"{k}={v}" for k, v in kw.items())
    logger.debug("[%s:%s] %s -> start %s", pipeline, _rid(state), node, extra)


def node_end(pipeline: str, state: dict[str, Any], node: str, elapsed: float, **kw: Any) -> None:
    extra = " ".join(f"{k}={v}" for k, v in kw.items())
    logger.debug("[%s:%s] %s -> done %.2fs %s", pipeline, _rid(state), node, elapsed, extra)


def agent_result(
    pipeline: str, state: dict[str, Any], agent_name: str, elapsed: float, **kw: Any
) -> None:
    extra = " ".join(f"{k}={v}" for k, v in kw.items())
    logger.debug("[%s:%s]   %s returned %.2fs %s", pipeline, _rid(state), agent_name, elapsed, extra)


def route(pipeline: str, state: dict[str, Any], dest: str, **kw: Any) -> None:
    extra = " ".join(f"{k}={v}" for k, v in kw.items())
    logger.debug("[%s:%s] route -> %s %s", pipeline, _rid(state), dest, extra)


def warn(pipeline: str, state: dict[str, Any], msg: str) -> None:
    logger.warning("[%s:%s] %s", pipeline, _rid(state), msg)


# ------------------------------------------------------------------
# Shared async agent caller
# ------------------------------------------------------------------


async def call_agent(agent: AgentProtocol, state: dict[str, Any]) -> dict[str, Any]:
    """Call an agent, running sync agents in a thread to avoid blocking the event loop."""
    if asyncio.iscoroutinefunction(getattr(agent, "__call__", agent)):
        return await agent(state)
    return await asyncio.to_thread(agent, state)


async def call_agent_logged(
    pipeline: str,
    agent: AgentProtocol,
    state: dict[str, Any],
    result_key: str,
) -> dict[str, Any]:
    """Call an agent with timing and debug logging.

    *result_key* is the state key to count items from (e.g. "raw_job_listings").
    """
    name = getattr(agent, "agent_name", type(agent).__name__)
    with _timed() as t:
        result = await call_agent(agent, state)
    agent_result(pipeline, state, name, t["elapsed"], items=len(result.get(result_key, [])))
    return result
