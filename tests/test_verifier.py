"""Tests for the deterministic verifier."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.engine.policy_engine import PolicyEngine
from app.engine.verifier import VerifierStatus, verify


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_policy_dir(tmp_path: Path, max_output_items: int = 50) -> Path:
    tools = {
        "agents": {
            "job_scout_retriever": {
                "allowed_tools": ["web_search"],
                "denied_tools": [],
            },
            "coordinator": {
                "allowed_tools": ["merge_items"],
                "denied_tools": ["web_search"],
            },
        }
    }
    budgets = {
        "agents": {
            "job_scout_retriever": {"max_steps": 5, "max_tokens": 4000},
        },
        "global": {"max_run_duration_seconds": 300, "max_output_items": max_output_items},
    }
    for name, data in [("tools", tools), ("budgets", budgets)]:
        (tmp_path / f"{name}.yaml").write_text(yaml.dump(data), encoding="utf-8")
    return tmp_path


def _good_opportunity(title: str = "SWE at Acme", source: str = "linkedin.com") -> dict:
    return {"title": title, "source": source}


def _good_claim(
    text: str = "Acme is hiring",
    requires_evidence: bool = True,
    evidence_ids: list[str] | None = None,
    confidence: float = 0.9,
) -> dict:
    return {
        "claim_text": text,
        "requires_evidence": requires_evidence,
        "evidence_ids": evidence_ids or (["ev1"] if requires_evidence else []),
        "confidence": confidence,
    }


def _good_evidence(eid: str = "ev1") -> dict:
    return {"id": eid, "url": "https://example.com", "content_hash": "abc123"}


# ------------------------------------------------------------------
# All-pass scenario
# ------------------------------------------------------------------


class TestAllPass:
    def test_basic_pass(self) -> None:
        report = verify(
            opportunities=[_good_opportunity()],
            claims=[_good_claim()],
            evidence_map={"ev1": _good_evidence()},
        )
        assert report.overall_status == VerifierStatus.PASS
        assert report.schema_valid is True
        assert report.evidence_coverage_ok is True
        assert report.dedup_ok is True
        assert report.output_bounds_ok is True
        assert len(report.errors) == 0

    def test_claim_without_evidence_requirement_passes(self) -> None:
        report = verify(
            opportunities=[_good_opportunity()],
            claims=[_good_claim(requires_evidence=False, evidence_ids=[])],
            evidence_map={},
        )
        assert report.overall_status == VerifierStatus.PASS

    def test_multiple_claims_all_pass(self) -> None:
        report = verify(
            opportunities=[_good_opportunity()],
            claims=[
                _good_claim("Claim A", evidence_ids=["ev1"]),
                _good_claim("Claim B", evidence_ids=["ev2"]),
            ],
            evidence_map={
                "ev1": _good_evidence("ev1"),
                "ev2": _good_evidence("ev2"),
            },
        )
        assert report.overall_status == VerifierStatus.PASS
        assert len(report.claim_results) == 2
        assert all(cr.status == VerifierStatus.PASS for cr in report.claim_results)


# ------------------------------------------------------------------
# Schema failures
# ------------------------------------------------------------------


class TestSchemaFailure:
    def test_missing_opportunity_title(self) -> None:
        report = verify(
            opportunities=[{"source": "indeed.com"}],  # missing title
            claims=[_good_claim(requires_evidence=False, evidence_ids=[])],
            evidence_map={},
        )
        assert report.overall_status == VerifierStatus.FAIL
        assert report.schema_valid is False
        assert any("title" in e for e in report.errors)

    def test_missing_opportunity_source(self) -> None:
        report = verify(
            opportunities=[{"title": "SWE"}],  # missing source
            claims=[_good_claim(requires_evidence=False, evidence_ids=[])],
            evidence_map={},
        )
        assert report.schema_valid is False

    def test_missing_claim_required_fields(self) -> None:
        report = verify(
            opportunities=[_good_opportunity()],
            claims=[{"confidence": 0.8}],  # missing claim_text, requires_evidence
            evidence_map={},
        )
        assert report.schema_valid is False

    def test_missing_evidence_fields(self) -> None:
        report = verify(
            opportunities=[_good_opportunity()],
            claims=[_good_claim(requires_evidence=False, evidence_ids=[])],
            evidence_map={"ev1": {"id": "ev1"}},  # missing url, content_hash
        )
        assert report.schema_valid is False


# ------------------------------------------------------------------
# Evidence coverage failures
# ------------------------------------------------------------------


class TestEvidenceCoverage:
    def test_claim_requires_evidence_but_has_none(self) -> None:
        report = verify(
            opportunities=[_good_opportunity()],
            claims=[_good_claim(evidence_ids=[])],
            evidence_map={},
        )
        assert report.overall_status == VerifierStatus.FAIL
        assert report.evidence_coverage_ok is False

    def test_claim_references_unknown_evidence(self) -> None:
        report = verify(
            opportunities=[_good_opportunity()],
            claims=[_good_claim(evidence_ids=["ev_missing"])],
            evidence_map={"ev1": _good_evidence()},
        )
        assert report.evidence_coverage_ok is False
        assert any("unknown evidence" in e for e in report.errors)


# ------------------------------------------------------------------
# Confidence threshold
# ------------------------------------------------------------------


class TestConfidence:
    def test_low_confidence_fails_claim(self) -> None:
        report = verify(
            opportunities=[_good_opportunity()],
            claims=[_good_claim(confidence=0.3)],
            evidence_map={"ev1": _good_evidence()},
        )
        # The claim itself should fail
        assert any(cr.confidence_ok is False for cr in report.claim_results)
        assert report.overall_status == VerifierStatus.FAIL

    def test_exactly_threshold_passes(self) -> None:
        report = verify(
            opportunities=[_good_opportunity()],
            claims=[_good_claim(confidence=0.7)],
            evidence_map={"ev1": _good_evidence()},
        )
        assert all(cr.confidence_ok is True for cr in report.claim_results)
        assert report.overall_status == VerifierStatus.PASS

    def test_below_threshold_fails(self) -> None:
        report = verify(
            opportunities=[_good_opportunity()],
            claims=[_good_claim(confidence=0.69)],
            evidence_map={"ev1": _good_evidence()},
        )
        failing = [cr for cr in report.claim_results if not cr.confidence_ok]
        assert len(failing) == 1


# ------------------------------------------------------------------
# Policy compliance
# ------------------------------------------------------------------


class TestPolicyCompliance:
    def test_forbidden_tool_use_detected(self, tmp_path: Path) -> None:
        pd = _make_policy_dir(tmp_path)
        pe = PolicyEngine(pd)
        events = [
            {"event_type": "tool_call", "agent": "coordinator", "data": {"tool": "web_search"}}
        ]
        report = verify(
            opportunities=[_good_opportunity()],
            claims=[_good_claim(requires_evidence=False, evidence_ids=[])],
            evidence_map={},
            audit_events=events,
            policy_engine=pe,
        )
        assert report.policy_compliant is False
        assert any("forbidden tool" in e for e in report.errors)

    def test_allowed_tool_use_ok(self, tmp_path: Path) -> None:
        pd = _make_policy_dir(tmp_path)
        pe = PolicyEngine(pd)
        events = [
            {"event_type": "tool_call", "agent": "job_scout_retriever", "data": {"tool": "web_search"}}
        ]
        report = verify(
            opportunities=[_good_opportunity()],
            claims=[_good_claim(requires_evidence=False, evidence_ids=[])],
            evidence_map={},
            audit_events=events,
            policy_engine=pe,
        )
        assert report.policy_compliant is True

    def test_no_policy_engine_skips_check(self) -> None:
        events = [
            {"event_type": "tool_call", "agent": "coordinator", "data": {"tool": "web_search"}}
        ]
        report = verify(
            opportunities=[_good_opportunity()],
            claims=[_good_claim(requires_evidence=False, evidence_ids=[])],
            evidence_map={},
            audit_events=events,
            policy_engine=None,
        )
        assert report.policy_compliant is True  # skipped, defaults to True


# ------------------------------------------------------------------
# Dedup
# ------------------------------------------------------------------


class TestDedup:
    def test_duplicate_opportunities_detected(self) -> None:
        report = verify(
            opportunities=[
                _good_opportunity("SWE", "linkedin.com"),
                _good_opportunity("SWE", "linkedin.com"),
            ],
            claims=[_good_claim(requires_evidence=False, evidence_ids=[])],
            evidence_map={},
        )
        assert report.dedup_ok is False
        assert report.overall_status == VerifierStatus.FAIL

    def test_same_title_different_source_ok(self) -> None:
        report = verify(
            opportunities=[
                _good_opportunity("SWE", "linkedin.com"),
                _good_opportunity("SWE", "indeed.com"),
            ],
            claims=[_good_claim(requires_evidence=False, evidence_ids=[])],
            evidence_map={},
        )
        assert report.dedup_ok is True


# ------------------------------------------------------------------
# Output bounds
# ------------------------------------------------------------------


class TestOutputBounds:
    def test_exceeds_max_output_items(self, tmp_path: Path) -> None:
        pd = _make_policy_dir(tmp_path, max_output_items=2)
        pe = PolicyEngine(pd)
        report = verify(
            opportunities=[
                _good_opportunity(f"Job {i}", f"source{i}.com") for i in range(5)
            ],
            claims=[_good_claim(requires_evidence=False, evidence_ids=[])],
            evidence_map={},
            policy_engine=pe,
        )
        assert report.output_bounds_ok is False
        assert report.overall_status == VerifierStatus.FAIL

    def test_within_bounds(self, tmp_path: Path) -> None:
        pd = _make_policy_dir(tmp_path, max_output_items=50)
        pe = PolicyEngine(pd)
        report = verify(
            opportunities=[_good_opportunity()],
            claims=[_good_claim(requires_evidence=False, evidence_ids=[])],
            evidence_map={},
            policy_engine=pe,
        )
        assert report.output_bounds_ok is True


# ------------------------------------------------------------------
# Safe degradation
# ------------------------------------------------------------------


class TestSafeDegradation:
    def test_failure_becomes_partial_with_safe_degradation(self) -> None:
        report = verify(
            opportunities=[_good_opportunity()],
            claims=[_good_claim(evidence_ids=[])],  # missing evidence -> would fail
            evidence_map={},
            safe_degradation=True,
        )
        assert report.overall_status == VerifierStatus.PARTIAL
        assert report.safe_degradation is True

    def test_failure_stays_fail_without_safe_degradation(self) -> None:
        report = verify(
            opportunities=[_good_opportunity()],
            claims=[_good_claim(evidence_ids=[])],
            evidence_map={},
            safe_degradation=False,
        )
        assert report.overall_status == VerifierStatus.FAIL

    def test_all_pass_stays_pass_with_safe_degradation(self) -> None:
        report = verify(
            opportunities=[_good_opportunity()],
            claims=[_good_claim()],
            evidence_map={"ev1": _good_evidence()},
            safe_degradation=True,
        )
        assert report.overall_status == VerifierStatus.PASS
