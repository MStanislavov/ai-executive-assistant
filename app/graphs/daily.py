"""LangGraph daily pipeline: all scouts -> extractors -> coordinator -> verifier -> audit."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.cert_scout_extractor import CertScoutExtractor
from app.agents.cert_scout_retriever import CertScoutRetriever
from app.agents.coordinator import Coordinator
from app.agents.job_scout_extractor import JobScoutExtractor
from app.agents.job_scout_retriever import JobScoutRetriever
from app.agents.trends_scout_extractor import TrendsScoutExtractor
from app.agents.trends_scout_retriever import TrendsScoutRetriever
from app.engine.audit_writer import AuditEvent, AuditWriter
from app.engine.policy_engine import PolicyEngine
from app.engine.verifier import verify
from app.graphs.state import DailyState


# ------------------------------------------------------------------
# Fan-out nodes: run all 3 scout types in one node each
# ------------------------------------------------------------------


def _fan_out_retrievers(state: DailyState) -> dict[str, Any]:
    """Run all three retrievers and merge their raw outputs."""
    job_ret = JobScoutRetriever()(state)
    cert_ret = CertScoutRetriever()(state)
    trends_ret = TrendsScoutRetriever()(state)
    return {
        "raw_job_listings": job_ret.get("raw_job_listings", []),
        "raw_cert_listings": cert_ret.get("raw_cert_listings", []),
        "raw_trends_data": trends_ret.get("raw_trends_data", []),
        "errors": state.get("errors", []),
    }


def _fan_out_extractors(state: DailyState) -> dict[str, Any]:
    """Run all three extractors and merge extracted opportunities + evidence."""
    job_ext = JobScoutExtractor()(state)
    cert_ext = CertScoutExtractor()(state)
    trends_ext = TrendsScoutExtractor()(state)

    all_opps = (
        job_ext.get("extracted_opportunities", [])
        + cert_ext.get("extracted_opportunities", [])
        + trends_ext.get("extracted_opportunities", [])
    )
    all_evidence = (
        job_ext.get("evidence_items", [])
        + cert_ext.get("evidence_items", [])
        + trends_ext.get("evidence_items", [])
    )
    return {
        "extracted_opportunities": all_opps,
        "evidence_items": all_evidence,
        "errors": state.get("errors", []),
    }


# ------------------------------------------------------------------
# Wrapper nodes for the verifier and audit writer
# ------------------------------------------------------------------


def _make_verifier_node(policy_engine: PolicyEngine | None = None):
    """Return a graph node that runs the deterministic verifier."""

    def verifier_node(state: DailyState) -> dict[str, Any]:
        opportunities = state.get("ranked_opportunities", [])
        claims = state.get("claims", [])
        evidence_items = state.get("evidence_items", [])
        audit_events = state.get("audit_events", [])
        safe_degradation = state.get("safe_degradation", False)

        evidence_map = {e["id"]: e for e in evidence_items}

        report = verify(
            opportunities=opportunities,
            claims=claims,
            evidence_map=evidence_map,
            audit_events=audit_events,
            policy_engine=policy_engine,
            safe_degradation=safe_degradation,
        )

        return {
            "verifier_report": {
                "overall_status": report.overall_status.value,
                "schema_valid": report.schema_valid,
                "evidence_coverage_ok": report.evidence_coverage_ok,
                "policy_compliant": report.policy_compliant,
                "dedup_ok": report.dedup_ok,
                "output_bounds_ok": report.output_bounds_ok,
                "errors": report.errors,
                "claim_results": [
                    {
                        "claim_text": cr.claim_text,
                        "status": cr.status.value,
                        "confidence": cr.confidence,
                        "confidence_ok": cr.confidence_ok,
                        "has_sufficient_evidence": cr.has_sufficient_evidence,
                    }
                    for cr in report.claim_results
                ],
            }
        }

    return verifier_node


def _make_audit_node(audit_writer: AuditWriter | None = None):
    """Return a graph node that writes audit events and creates the run bundle."""

    def audit_node(state: DailyState) -> dict[str, Any]:
        if audit_writer is None:
            return {}

        run_id = state.get("run_id", "unknown")

        # Write summary event
        audit_writer.append(
            run_id,
            AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="output",
                agent="daily_pipeline",
                data={
                    "summary": state.get("summary", ""),
                    "opportunity_count": len(state.get("ranked_opportunities", [])),
                    "verifier_status": state.get("verifier_report", {}).get(
                        "overall_status", "unknown"
                    ),
                },
            ),
        )

        # Create bundle
        audit_writer.create_run_bundle(
            run_id=run_id,
            profile_hash=state.get("profile_id", "unknown"),
            policy_version_hash="",  # filled by caller when policy engine available
            verifier_report=state.get("verifier_report", {}),
            final_artifacts={
                "opportunities": state.get("ranked_opportunities", []),
                "summary": state.get("summary", ""),
            },
        )

        return {}

    return audit_node


# ------------------------------------------------------------------
# Conditional routing
# ------------------------------------------------------------------


def _check_retrieval(state: DailyState) -> str:
    """After retrievers, route to extractors or mark safe degradation."""
    raw_jobs = state.get("raw_job_listings", [])
    raw_certs = state.get("raw_cert_listings", [])
    raw_trends = state.get("raw_trends_data", [])
    if not raw_jobs and not raw_certs and not raw_trends:
        return "safe_degrade"
    return "extract"


def _safe_degrade_node(state: DailyState) -> dict[str, Any]:
    """Mark safe degradation when retrieval yields nothing."""
    return {
        "safe_degradation": True,
        "extracted_opportunities": [],
        "evidence_items": [],
        "errors": state.get("errors", [])
        + ["All retrievals returned no results; safe degradation active"],
    }


# ------------------------------------------------------------------
# Graph builder
# ------------------------------------------------------------------


def build_daily_graph(
    policy_engine: PolicyEngine | None = None,
    audit_writer: AuditWriter | None = None,
) -> StateGraph:
    """Construct the daily pipeline StateGraph.

    Nodes: fan_out_retrievers -> fan_out_extractors -> coordinator -> verifier -> audit_writer
    With a conditional edge for safe degradation when all retrievals return empty.
    """
    graph = StateGraph(DailyState)

    # Register nodes
    graph.add_node("fan_out_retrievers", _fan_out_retrievers)
    graph.add_node("fan_out_extractors", _fan_out_extractors)
    graph.add_node("coordinator", Coordinator())
    graph.add_node("verifier", _make_verifier_node(policy_engine))
    graph.add_node("audit_writer", _make_audit_node(audit_writer))
    graph.add_node("safe_degrade", _safe_degrade_node)

    # Entry point
    graph.set_entry_point("fan_out_retrievers")

    # Conditional: retrievers -> extractors OR safe_degrade
    graph.add_conditional_edges(
        "fan_out_retrievers",
        _check_retrieval,
        {
            "extract": "fan_out_extractors",
            "safe_degrade": "safe_degrade",
        },
    )

    # Linear edges
    graph.add_edge("fan_out_extractors", "coordinator")
    graph.add_edge("safe_degrade", "coordinator")
    graph.add_edge("coordinator", "verifier")
    graph.add_edge("verifier", "audit_writer")
    graph.add_edge("audit_writer", END)

    return graph
