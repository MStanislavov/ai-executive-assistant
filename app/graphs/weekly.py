"""LangGraph weekly pipeline: goal_extractor -> web_scrapers -> data_formatter -> ceo -> cfo -> audit."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.base import AgentProtocol
from app.agents.factory import AgentFactory
from app.engine.audit_writer import AuditEvent, AuditWriter
from app.engine.policy_engine import PolicyEngine
from app.graphs.log import call_agent, node_end, node_start, route, warn
from app.graphs.state import WeeklyState

_P = "weekly"


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


def _make_goal_extractor_node(
    agent: AgentProtocol,
    policy_engine: PolicyEngine | None = None,
    audit_writer: AuditWriter | None = None,
):
    async def goal_extractor_node(state: WeeklyState) -> dict[str, Any]:
        _check_tool(policy_engine, "goal_extractor", "llm_structured_output")
        node_start(_P, state, "goal_extractor")
        run_id = state.get("run_id", "unknown")
        if audit_writer:
            audit_writer.append(run_id, AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="agent_start", agent="goal_extractor",
            ))
        t0 = time.monotonic()
        result = await call_agent(agent, state)
        node_end(_P, state, "goal_extractor", time.monotonic() - t0)
        if audit_writer:
            audit_writer.append(run_id, AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="agent_end", agent="goal_extractor",
                data=result,
            ))
        return result

    return goal_extractor_node


def _make_fan_out_web_scrapers(
    scraper: AgentProtocol,
    policy_engine: PolicyEngine | None = None,
    audit_writer: AuditWriter | None = None,
):
    async def fan_out_web_scrapers(state: WeeklyState) -> dict[str, Any]:
        _check_tool(policy_engine, "web_scraper", "web_search")
        prompts = state.get("search_prompts", {})
        node_start(_P, state, "web_scrapers", prompts=len(prompts))
        run_id = state.get("run_id", "unknown")
        if audit_writer:
            audit_writer.append(run_id, AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="agent_start", agent="web_scrapers",
                data={"prompts": prompts},
            ))
        t0 = time.monotonic()

        categories = [
            ("job", "job_prompt"),
            ("cert", "cert_prompt"),
            ("event", "event_prompt"),
            ("group", "group_prompt"),
            ("trend", "trend_prompt"),
        ]

        async def _run_scraper(category: str, prompt_key: str) -> dict[str, Any]:
            search_state = {
                **state,
                "search_prompt": prompts.get(prompt_key, ""),
                "search_category": category,
            }
            return await call_agent(scraper, search_state)

        returns = await asyncio.gather(
            *[_run_scraper(cat, pk) for cat, pk in categories]
        )

        all_errors: list[str] = []
        results: dict[str, Any] = {}
        for (category, _), ret in zip(categories, returns):
            result_key = f"raw_{category}_results"
            results[result_key] = ret.get(result_key, [])
            all_errors.extend(ret.get("errors", []))

        node_end(
            _P, state, "web_scrapers", time.monotonic() - t0,
            jobs=len(results.get("raw_job_results", [])),
            certs=len(results.get("raw_cert_results", [])),
            events=len(results.get("raw_event_results", [])),
            groups=len(results.get("raw_group_results", [])),
            trends=len(results.get("raw_trend_results", [])),
        )
        if audit_writer:
            audit_writer.append(run_id, AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="agent_end", agent="web_scrapers",
                data=results,
            ))

        return {
            **results,
            "errors": state.get("errors", []) + all_errors,
        }

    return fan_out_web_scrapers


def _make_data_formatter_node(
    agent: AgentProtocol,
    policy_engine: PolicyEngine | None = None,
    audit_writer: AuditWriter | None = None,
):
    async def data_formatter_node(state: WeeklyState) -> dict[str, Any]:
        _check_tool(policy_engine, "data_formatter", "llm_structured_output")
        node_start(_P, state, "data_formatter")
        run_id = state.get("run_id", "unknown")
        if audit_writer:
            audit_writer.append(run_id, AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="agent_start", agent="data_formatter",
            ))
        t0 = time.monotonic()
        result = await call_agent(agent, state)
        node_end(
            _P, state, "data_formatter", time.monotonic() - t0,
            jobs=len(result.get("formatted_jobs", [])),
            certs=len(result.get("formatted_certifications", [])),
            courses=len(result.get("formatted_courses", [])),
            events=len(result.get("formatted_events", [])),
            groups=len(result.get("formatted_groups", [])),
            trends=len(result.get("formatted_trends", [])),
        )
        if audit_writer:
            audit_writer.append(run_id, AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="agent_end", agent="data_formatter",
                data=result,
            ))
        return result

    return data_formatter_node


def _make_ceo_node(
    ceo: AgentProtocol,
    policy_engine: PolicyEngine | None = None,
    audit_writer: AuditWriter | None = None,
):
    async def ceo_node(state: WeeklyState) -> dict[str, Any]:
        _check_tool(policy_engine, "ceo", "llm_structured_output")
        node_start(_P, state, "ceo")
        run_id = state.get("run_id", "unknown")
        if audit_writer:
            audit_writer.append(run_id, AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="agent_start", agent="ceo",
            ))
        t0 = time.monotonic()
        result = await call_agent(ceo, state)
        node_end(
            _P, state, "ceo", time.monotonic() - t0,
            recommendations=len(result.get("strategic_recommendations", [])),
        )
        if audit_writer:
            audit_writer.append(run_id, AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="agent_end", agent="ceo",
                data=result,
            ))
        return result

    return ceo_node


def _make_cfo_node(
    cfo: AgentProtocol,
    policy_engine: PolicyEngine | None = None,
    audit_writer: AuditWriter | None = None,
):
    async def cfo_node(state: WeeklyState) -> dict[str, Any]:
        _check_tool(policy_engine, "cfo", "llm_structured_output")
        node_start(_P, state, "cfo")
        run_id = state.get("run_id", "unknown")
        if audit_writer:
            audit_writer.append(run_id, AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="agent_start", agent="cfo",
            ))
        t0 = time.monotonic()
        result = await call_agent(cfo, state)
        node_end(
            _P, state, "cfo", time.monotonic() - t0,
            assessments=len(result.get("risk_assessments", [])),
        )
        if audit_writer:
            audit_writer.append(run_id, AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="agent_end", agent="cfo",
                data=result,
            ))
        return result

    return cfo_node


def _make_audit_node(
    audit_writer: AuditWriter | None = None,
    policy_engine: PolicyEngine | None = None,
):
    def audit_node(state: WeeklyState) -> dict[str, Any]:
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
                agent="weekly_pipeline",
                data={
                    "job_count": len(state.get("formatted_jobs", [])),
                    "cert_count": len(state.get("formatted_certifications", [])),
                    "course_count": len(state.get("formatted_courses", [])),
                    "event_count": len(state.get("formatted_events", [])),
                    "group_count": len(state.get("formatted_groups", [])),
                    "trend_count": len(state.get("formatted_trends", [])),
                    "recommendation_count": len(state.get("strategic_recommendations", [])),
                    "assessment_count": len(state.get("risk_assessments", [])),
                },
            ),
        )
        audit_writer.create_run_bundle(
            run_id=run_id,
            profile_hash=state.get("profile_id", "unknown"),
            policy_version_hash=policy_hash,
            verifier_report={},
            final_artifacts={
                "jobs": state.get("formatted_jobs", []),
                "certifications": state.get("formatted_certifications", []),
                "courses": state.get("formatted_courses", []),
                "events": state.get("formatted_events", []),
                "groups": state.get("formatted_groups", []),
                "trends": state.get("formatted_trends", []),
                "strategic_recommendations": state.get("strategic_recommendations", []),
                "ceo_summary": state.get("ceo_summary", ""),
                "risk_assessments": state.get("risk_assessments", []),
                "cfo_summary": state.get("cfo_summary", ""),
            },
        )

        node_end(_P, state, "audit_writer", time.monotonic() - t0)
        return {}

    return audit_node


# ------------------------------------------------------------------
# Conditional routing
# ------------------------------------------------------------------


def _check_scraper_results(state: WeeklyState) -> str:
    raw_jobs = state.get("raw_job_results", [])
    raw_certs = state.get("raw_cert_results", [])
    raw_events = state.get("raw_event_results", [])
    raw_groups = state.get("raw_group_results", [])
    raw_trends = state.get("raw_trend_results", [])
    if not raw_jobs and not raw_certs and not raw_events and not raw_groups and not raw_trends:
        warn(_P, state, "all web scrapers returned empty, entering safe degradation")
        return "safe_degrade"
    route(
        _P, state, "data_formatter",
        jobs=len(raw_jobs), certs=len(raw_certs), events=len(raw_events),
        groups=len(raw_groups), trends=len(raw_trends),
    )
    return "format"


def _safe_degrade_node(state: WeeklyState) -> dict[str, Any]:
    warn(_P, state, "safe_degrade activated")
    return {
        "safe_degradation": True,
        "formatted_jobs": [],
        "formatted_certifications": [],
        "formatted_courses": [],
        "formatted_events": [],
        "formatted_groups": [],
        "formatted_trends": [],
        "errors": state.get("errors", [])
        + ["All web scrapers returned no results; safe degradation active"],
    }


# ------------------------------------------------------------------
# Graph builder
# ------------------------------------------------------------------


def build_weekly_graph(
    policy_engine: PolicyEngine | None = None,
    audit_writer: AuditWriter | None = None,
    agent_factory: AgentFactory | None = None,
) -> StateGraph:
    """Construct the weekly pipeline StateGraph."""
    if agent_factory is None:
        agent_factory = AgentFactory()

    goal_extractor = agent_factory.create_goal_extractor()
    web_scraper = agent_factory.create_web_scraper()
    data_formatter = agent_factory.create_data_formatter()
    ceo = agent_factory.create_ceo()
    cfo = agent_factory.create_cfo()

    graph = StateGraph(WeeklyState)

    graph.add_node("goal_extractor", _make_goal_extractor_node(goal_extractor, policy_engine, audit_writer))
    graph.add_node("web_scrapers", _make_fan_out_web_scrapers(web_scraper, policy_engine, audit_writer))
    graph.add_node("data_formatter", _make_data_formatter_node(data_formatter, policy_engine, audit_writer))
    graph.add_node("ceo", _make_ceo_node(ceo, policy_engine, audit_writer))
    graph.add_node("cfo", _make_cfo_node(cfo, policy_engine, audit_writer))
    graph.add_node("audit_writer", _make_audit_node(audit_writer, policy_engine))
    graph.add_node("safe_degrade", _safe_degrade_node)

    graph.set_entry_point("goal_extractor")
    graph.add_edge("goal_extractor", "web_scrapers")
    graph.add_conditional_edges(
        "web_scrapers",
        _check_scraper_results,
        {"format": "data_formatter", "safe_degrade": "safe_degrade"},
    )
    graph.add_edge("data_formatter", "ceo")
    graph.add_edge("safe_degrade", "ceo")
    graph.add_edge("ceo", "cfo")
    graph.add_edge("cfo", "audit_writer")
    graph.add_edge("audit_writer", END)

    return graph
