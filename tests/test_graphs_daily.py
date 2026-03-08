"""Tests for the daily LangGraph pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.audit_writer import AuditWriter
from app.engine.policy_engine import PolicyEngine
from app.graphs.daily import build_daily_graph


@pytest.fixture()
def policy_engine(tmp_path: Path) -> PolicyEngine:
    """Create a minimal policy dir and return a PolicyEngine."""
    import yaml

    tools = {
        "agents": {
            "job_scout_retriever": {
                "allowed_tools": ["web_search", "web_fetch", "rss_fetch"],
                "denied_tools": [],
            },
            "job_scout_extractor": {
                "allowed_tools": ["parse_html", "extract_json"],
                "denied_tools": ["web_search", "web_fetch"],
            },
            "cert_scout_retriever": {
                "allowed_tools": ["web_search", "web_fetch"],
                "denied_tools": [],
            },
            "cert_scout_extractor": {
                "allowed_tools": ["parse_html", "extract_json"],
                "denied_tools": ["web_search", "web_fetch"],
            },
            "trends_scout_retriever": {
                "allowed_tools": ["web_search", "web_fetch", "rss_fetch"],
                "denied_tools": [],
            },
            "trends_scout_extractor": {
                "allowed_tools": ["parse_html", "extract_json"],
                "denied_tools": ["web_search", "web_fetch"],
            },
            "coordinator": {
                "allowed_tools": ["merge_items", "rank_items"],
                "denied_tools": ["web_search", "web_fetch", "rss_fetch"],
            },
        }
    }
    budgets = {
        "agents": {
            "job_scout_retriever": {"max_steps": 5, "max_tokens": 4000},
            "coordinator": {"max_steps": 3, "max_tokens": 6000},
        },
        "global": {"max_run_duration_seconds": 300, "max_output_items": 50},
    }
    for name, data in [("tools", tools), ("budgets", budgets)]:
        (tmp_path / f"{name}.yaml").write_text(yaml.dump(data), encoding="utf-8")
    return PolicyEngine(tmp_path)


@pytest.fixture()
def audit_writer(tmp_path: Path) -> AuditWriter:
    return AuditWriter(artifacts_dir=tmp_path / "artifacts")


def _invoke_daily(**overrides):
    """Helper to invoke the daily graph with default inputs."""
    inputs = {
        "profile_id": "test-profile",
        "run_id": "test-run-001",
        "errors": [],
        "safe_degradation": False,
        "audit_events": [],
    }
    inputs.update(overrides)
    graph = build_daily_graph()
    compiled = graph.compile()
    return compiled.invoke(inputs)


class TestDailyGraphExecution:
    def test_full_pipeline_runs(self) -> None:
        result = _invoke_daily()
        assert "ranked_opportunities" in result
        assert "verifier_report" in result
        assert "summary" in result

    def test_produces_seven_opportunities(self) -> None:
        """3 jobs + 2 certs + 2 trends = 7 opportunities."""
        result = _invoke_daily()
        assert len(result["ranked_opportunities"]) == 7

    def test_all_opportunity_types_present(self) -> None:
        """All three scout types should produce opportunities."""
        result = _invoke_daily()
        types = {o["opportunity_type"] for o in result["ranked_opportunities"]}
        assert types == {"job", "cert", "trend"}

    def test_verifier_passes(self) -> None:
        result = _invoke_daily()
        assert result["verifier_report"]["overall_status"] == "pass"

    def test_evidence_items_created(self) -> None:
        result = _invoke_daily()
        assert len(result["evidence_items"]) == 7
        for ev in result["evidence_items"]:
            assert "id" in ev
            assert "url" in ev
            assert "content_hash" in ev

    def test_claims_generated(self) -> None:
        result = _invoke_daily()
        assert len(result["claims"]) == 7
        for claim in result["claims"]:
            assert claim["requires_evidence"] is True
            assert len(claim["evidence_ids"]) > 0
            assert claim["confidence"] > 0.7

    def test_with_policy_engine(self, policy_engine: PolicyEngine) -> None:
        graph = build_daily_graph(policy_engine=policy_engine)
        compiled = graph.compile()
        result = compiled.invoke({
            "profile_id": "p1",
            "run_id": "r1",
            "errors": [],
            "safe_degradation": False,
            "audit_events": [],
        })
        assert result["verifier_report"]["overall_status"] == "pass"

    def test_with_audit_writer(self, audit_writer: AuditWriter) -> None:
        graph = build_daily_graph(audit_writer=audit_writer)
        compiled = graph.compile()
        run_id = "test-audit-run"
        result = compiled.invoke({
            "profile_id": "p1",
            "run_id": run_id,
            "errors": [],
            "safe_degradation": False,
            "audit_events": [],
        })
        # Audit bundle should have been created
        bundle = audit_writer.read_bundle(run_id)
        assert bundle is not None
        assert bundle["verifier_report"]["overall_status"] == "pass"
        # Audit log should have events
        events = audit_writer.read_log(run_id)
        assert len(events) > 0

    def test_summary_contains_counts(self) -> None:
        result = _invoke_daily()
        assert "7" in result["summary"]
        assert "opportunities" in result["summary"].lower() or "sources" in result["summary"].lower()


class TestSafeDegradation:
    def test_empty_retrieval_triggers_degradation(self) -> None:
        """When all retrievers return empty, safe degradation activates."""
        from app.graphs.state import DailyState
        from langgraph.graph import END, StateGraph
        from app.graphs.daily import (
            _check_retrieval,
            _safe_degrade_node,
            _make_verifier_node,
            _make_audit_node,
        )
        from app.agents.coordinator import Coordinator

        def _empty_retrievers(state):
            return {
                "raw_job_listings": [],
                "raw_cert_listings": [],
                "raw_trends_data": [],
                "errors": state.get("errors", []),
            }

        def _empty_extractors(state):
            return {
                "extracted_opportunities": [],
                "evidence_items": [],
                "errors": state.get("errors", []),
            }

        graph = StateGraph(DailyState)
        graph.add_node("fan_out_retrievers", _empty_retrievers)
        graph.add_node("fan_out_extractors", _empty_extractors)
        graph.add_node("coordinator", Coordinator())
        graph.add_node("verifier", _make_verifier_node())
        graph.add_node("audit_writer", _make_audit_node())
        graph.add_node("safe_degrade", _safe_degrade_node)
        graph.set_entry_point("fan_out_retrievers")
        graph.add_conditional_edges("fan_out_retrievers", _check_retrieval, {
            "extract": "fan_out_extractors",
            "safe_degrade": "safe_degrade",
        })
        graph.add_edge("fan_out_extractors", "coordinator")
        graph.add_edge("safe_degrade", "coordinator")
        graph.add_edge("coordinator", "verifier")
        graph.add_edge("verifier", "audit_writer")
        graph.add_edge("audit_writer", END)

        compiled = graph.compile()
        result = compiled.invoke({
            "profile_id": "p1",
            "run_id": "r1",
            "errors": [],
            "safe_degradation": False,
            "audit_events": [],
        })

        assert result["safe_degradation"] is True
        assert len(result["ranked_opportunities"]) == 0
        assert any("safe degradation" in e.lower() for e in result.get("errors", []))
