"""Tests for the cover letter LangGraph pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.audit_writer import AuditWriter
from app.engine.policy_engine import PolicyEngine
from app.graphs.cover_letter import build_cover_letter_graph


@pytest.fixture()
def policy_engine(tmp_path: Path) -> PolicyEngine:
    import yaml

    tools = {
        "agents": {
            "cover_letter": {
                "allowed_tools": ["read_cv", "read_jd"],
                "denied_tools": ["web_search", "web_fetch", "rss_fetch"],
            },
        }
    }
    budgets = {
        "agents": {
            "cover_letter": {"max_steps": 3, "max_tokens": 8000},
        },
        "global": {"max_run_duration_seconds": 120, "max_output_items": 5},
    }
    for name, data in [("tools", tools), ("budgets", budgets)]:
        (tmp_path / f"{name}.yaml").write_text(yaml.dump(data), encoding="utf-8")
    return PolicyEngine(tmp_path)


@pytest.fixture()
def audit_writer(tmp_path: Path) -> AuditWriter:
    return AuditWriter(artifacts_dir=tmp_path / "artifacts")


def _invoke_cover_letter(**overrides):
    """Helper to invoke the cover letter graph with default inputs."""
    inputs = {
        "profile_id": "test-profile",
        "run_id": "test-cl-run-001",
        "cv_content": "Experienced software engineer with 10 years in Python and cloud.",
        "jd_text": "Looking for a senior engineer with Python and AWS experience.",
        "opportunity": {
            "title": "Senior Software Engineer",
            "source": "TechCorp",
            "url": "https://example.com/job/123",
            "description": "Looking for a senior engineer with Python and AWS experience.",
            "opportunity_type": "job",
        },
        "errors": [],
        "audit_events": [],
    }
    inputs.update(overrides)
    graph = build_cover_letter_graph()
    compiled = graph.compile()
    return compiled.invoke(inputs)


class TestCoverLetterGraphExecution:
    def test_full_pipeline_runs(self) -> None:
        result = _invoke_cover_letter()
        assert "cover_letter_content" in result
        assert "verifier_report" in result
        assert "claims" in result
        assert "evidence_items" in result

    def test_cover_letter_has_content(self) -> None:
        result = _invoke_cover_letter()
        content = result["cover_letter_content"]
        assert len(content) > 100
        assert "Dear Hiring Manager" in content

    def test_mentions_opportunity_details(self) -> None:
        result = _invoke_cover_letter()
        content = result["cover_letter_content"]
        assert "Senior Software Engineer" in content
        assert "TechCorp" in content

    def test_produces_evidence_items(self) -> None:
        result = _invoke_cover_letter()
        evidence = result["evidence_items"]
        assert len(evidence) == 2
        types = {e["type"] for e in evidence}
        assert types == {"cv", "job_description"}
        for ev in evidence:
            assert "id" in ev
            assert "content_hash" in ev

    def test_produces_claims(self) -> None:
        result = _invoke_cover_letter()
        claims = result["claims"]
        assert len(claims) == 2
        for claim in claims:
            assert claim["requires_evidence"] is True
            assert len(claim["evidence_ids"]) > 0
            assert claim["confidence"] > 0.5

    def test_verifier_passes(self) -> None:
        result = _invoke_cover_letter()
        assert result["verifier_report"]["overall_status"] == "pass"

    def test_with_jd_text_only(self) -> None:
        """Cover letter from raw JD text (no opportunity)."""
        result = _invoke_cover_letter(
            opportunity={},
            jd_text="We need a data scientist with ML experience.",
        )
        assert "cover_letter_content" in result
        assert result["verifier_report"]["overall_status"] == "pass"

    def test_with_empty_cv(self) -> None:
        """Should still produce output even with empty CV."""
        result = _invoke_cover_letter(cv_content="")
        assert "cover_letter_content" in result
        assert len(result["cover_letter_content"]) > 0

    def test_with_policy_engine(self, policy_engine: PolicyEngine) -> None:
        graph = build_cover_letter_graph(policy_engine=policy_engine)
        compiled = graph.compile()
        result = compiled.invoke({
            "profile_id": "p1",
            "run_id": "r1",
            "cv_content": "Python developer",
            "jd_text": "Need Python dev",
            "opportunity": {"title": "Dev", "source": "Co"},
            "errors": [],
            "audit_events": [],
        })
        assert result["verifier_report"]["overall_status"] == "pass"

    def test_with_audit_writer(self, audit_writer: AuditWriter) -> None:
        graph = build_cover_letter_graph(audit_writer=audit_writer)
        compiled = graph.compile()
        run_id = "test-cl-audit-run"
        result = compiled.invoke({
            "profile_id": "p1",
            "run_id": run_id,
            "cv_content": "Python developer",
            "jd_text": "Need Python dev",
            "opportunity": {"title": "Dev", "source": "Co"},
            "errors": [],
            "audit_events": [],
        })
        bundle = audit_writer.read_bundle(run_id)
        assert bundle is not None
        events = audit_writer.read_log(run_id)
        assert len(events) > 0
