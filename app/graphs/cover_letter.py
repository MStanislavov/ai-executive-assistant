"""LangGraph cover letter pipeline: cover_letter_agent -> audit_writer."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.base import AgentProtocol
from app.agents.factory import AgentFactory
from app.engine.audit_writer import AuditEvent, AuditWriter
from app.engine.policy_engine import PolicyEngine
from app.graphs.log import call_agent, node_end, node_start
from app.graphs.state import CoverLetterState

_P = "cover_letter"


# ------------------------------------------------------------------
# Policy helpers
# ------------------------------------------------------------------


def _check_tool(policy_engine: PolicyEngine | None, agent_name: str, tool: str) -> None:
    """Raise if the policy engine denies this tool for the agent."""
    if policy_engine is None:
        return
    if not policy_engine.is_tool_allowed(agent_name, tool):
        raise PermissionError(
            f"Policy violation: agent '{agent_name}' is not allowed tool '{tool}'"
        )


# ------------------------------------------------------------------
# Node factories
# ------------------------------------------------------------------


def _make_cover_letter_node(agent: AgentProtocol, policy_engine: PolicyEngine | None = None):
    async def cover_letter_node(state: CoverLetterState) -> dict[str, Any]:
        _check_tool(policy_engine, "cover_letter_agent", "llm_generate_text")
        node_start(_P, state, "cover_letter_agent")
        t0 = time.monotonic()
        result = await call_agent(agent, state)
        node_end(
            _P, state, "cover_letter_agent", time.monotonic() - t0,
            has_content=bool(result.get("cover_letter_content")),
        )
        return result

    return cover_letter_node


def _make_audit_node(
    audit_writer: AuditWriter | None = None,
    policy_engine: PolicyEngine | None = None,
):
    """Return a graph node that writes audit events and creates the run bundle."""

    def audit_node(state: CoverLetterState) -> dict[str, Any]:
        if audit_writer is None:
            node_start(_P, state, "audit_writer", skipped=True)
            return {}

        node_start(_P, state, "audit_writer")
        t0 = time.monotonic()

        run_id = state.get("run_id", "unknown")
        policy_hash = policy_engine.version.hash if policy_engine else ""

        audit_writer.append(
            run_id,
            AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="output",
                agent="cover_letter_pipeline",
                data={
                    "has_content": bool(state.get("cover_letter_content")),
                },
            ),
        )

        audit_writer.create_run_bundle(
            run_id=run_id,
            profile_hash=state.get("profile_id", "unknown"),
            policy_version_hash=policy_hash,
            verifier_report={},
            final_artifacts={
                "cover_letter": state.get("cover_letter_content", ""),
            },
        )

        node_end(_P, state, "audit_writer", time.monotonic() - t0)
        return {}

    return audit_node


# ------------------------------------------------------------------
# Graph builder
# ------------------------------------------------------------------


def build_cover_letter_graph(
    policy_engine: PolicyEngine | None = None,
    audit_writer: AuditWriter | None = None,
    agent_factory: AgentFactory | None = None,
) -> StateGraph:
    """Construct the cover letter pipeline StateGraph.

    Nodes: cover_letter_agent -> audit_writer
    """
    if agent_factory is None:
        agent_factory = AgentFactory()

    cover_letter_agent = agent_factory.create_cover_letter_agent()

    graph = StateGraph(CoverLetterState)

    graph.add_node("cover_letter_agent", _make_cover_letter_node(cover_letter_agent, policy_engine))
    graph.add_node("audit_writer", _make_audit_node(audit_writer, policy_engine))

    graph.set_entry_point("cover_letter_agent")
    graph.add_edge("cover_letter_agent", "audit_writer")
    graph.add_edge("audit_writer", END)

    return graph
