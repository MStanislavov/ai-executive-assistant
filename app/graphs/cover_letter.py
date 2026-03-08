"""LangGraph cover letter pipeline: cover_letter_agent -> verifier -> audit_writer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.cover_letter_agent import CoverLetterAgent
from app.engine.audit_writer import AuditEvent, AuditWriter
from app.engine.policy_engine import PolicyEngine
from app.engine.verifier import verify
from app.graphs.state import CoverLetterState


# ------------------------------------------------------------------
# Wrapper nodes
# ------------------------------------------------------------------


def _make_verifier_node(policy_engine: PolicyEngine | None = None):
    """Return a graph node that runs the deterministic verifier."""

    def verifier_node(state: CoverLetterState) -> dict[str, Any]:
        claims = state.get("claims", [])
        evidence_items = state.get("evidence_items", [])
        audit_events = state.get("audit_events", [])

        evidence_map = {e["id"]: e for e in evidence_items}

        report = verify(
            opportunities=[],
            claims=claims,
            evidence_map=evidence_map,
            audit_events=audit_events,
            policy_engine=policy_engine,
            safe_degradation=False,
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

    def audit_node(state: CoverLetterState) -> dict[str, Any]:
        if audit_writer is None:
            return {}

        run_id = state.get("run_id", "unknown")

        audit_writer.append(
            run_id,
            AuditEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type="output",
                agent="cover_letter_pipeline",
                data={
                    "has_content": bool(state.get("cover_letter_content")),
                    "claim_count": len(state.get("claims", [])),
                    "evidence_count": len(state.get("evidence_items", [])),
                    "verifier_status": state.get("verifier_report", {}).get(
                        "overall_status", "unknown"
                    ),
                },
            ),
        )

        audit_writer.create_run_bundle(
            run_id=run_id,
            profile_hash=state.get("profile_id", "unknown"),
            policy_version_hash="",
            verifier_report=state.get("verifier_report", {}),
            final_artifacts={
                "cover_letter": state.get("cover_letter_content", ""),
            },
        )

        return {}

    return audit_node


# ------------------------------------------------------------------
# Graph builder
# ------------------------------------------------------------------


def build_cover_letter_graph(
    policy_engine: PolicyEngine | None = None,
    audit_writer: AuditWriter | None = None,
) -> StateGraph:
    """Construct the cover letter pipeline StateGraph.

    Nodes: cover_letter_agent -> verifier -> audit_writer
    Simple linear pipeline — no fan-out or conditional routing needed.
    """
    graph = StateGraph(CoverLetterState)

    graph.add_node("cover_letter_agent", CoverLetterAgent())
    graph.add_node("verifier", _make_verifier_node(policy_engine))
    graph.add_node("audit_writer", _make_audit_node(audit_writer))

    graph.set_entry_point("cover_letter_agent")
    graph.add_edge("cover_letter_agent", "verifier")
    graph.add_edge("verifier", "audit_writer")
    graph.add_edge("audit_writer", END)

    return graph
