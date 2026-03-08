"""Tests for ReplayEngine and DiffEngine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.engine.audit_writer import AuditWriter
from app.engine.diff import DiffEngine
from app.engine.replay import ReplayEngine


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def artifacts_dir(tmp_path: Path) -> Path:
    return tmp_path / "artifacts"


@pytest.fixture()
def writer(artifacts_dir: Path) -> AuditWriter:
    return AuditWriter(artifacts_dir=artifacts_dir)


@pytest.fixture()
def replay_engine(writer: AuditWriter) -> ReplayEngine:
    return ReplayEngine(audit_writer=writer)


@pytest.fixture()
def diff_engine(writer: AuditWriter) -> DiffEngine:
    return DiffEngine(audit_writer=writer)


def _make_bundle(
    writer: AuditWriter,
    run_id: str,
    opportunities: list[dict[str, Any]] | None = None,
    summary: str = "Test summary",
    verifier_status: str = "pass",
) -> None:
    """Helper to create a bundle with given opportunities."""
    if opportunities is None:
        opportunities = [
            {
                "title": "Software Engineer at Acme",
                "source": "linkedin",
                "description": "Build things",
                "url": "https://example.com/job/1",
                "opportunity_type": "job",
            },
            {
                "title": "Backend Developer at Globex",
                "source": "indeed",
                "description": "Write APIs",
                "url": "https://example.com/job/2",
                "opportunity_type": "job",
            },
        ]
    writer.create_run_bundle(
        run_id=run_id,
        profile_hash="profile-hash-abc",
        policy_version_hash="policy-hash-xyz",
        verifier_report={"overall_status": verifier_status},
        final_artifacts={"opportunities": opportunities, "summary": summary},
    )


# ------------------------------------------------------------------
# ReplayEngine — strict
# ------------------------------------------------------------------


class TestReplayStrict:
    def test_returns_same_artifacts_as_original(
        self, writer: AuditWriter, replay_engine: ReplayEngine
    ) -> None:
        _make_bundle(writer, "orig-run-1")
        result = replay_engine.replay_strict("orig-run-1", "replay-run-1")

        assert result["run_id"] == "replay-run-1"
        assert result["replay_mode"] == "strict"
        assert result["original_run_id"] == "orig-run-1"
        assert result["drift"] == []

        opps = result["result"]["opportunities"]
        assert len(opps) == 2
        assert opps[0]["title"] == "Software Engineer at Acme"

    def test_verifier_report_preserved(
        self, writer: AuditWriter, replay_engine: ReplayEngine
    ) -> None:
        _make_bundle(writer, "orig-run-2", verifier_status="partial")
        result = replay_engine.replay_strict("orig-run-2", "replay-run-2")
        assert result["verifier_report"]["overall_status"] == "partial"

    def test_nonexistent_run_raises(self, replay_engine: ReplayEngine) -> None:
        with pytest.raises(ValueError, match="No bundle found"):
            replay_engine.replay_strict("nonexistent", "new-run")


# ------------------------------------------------------------------
# ReplayEngine — refresh
# ------------------------------------------------------------------


class TestReplayRefresh:
    def test_no_drift_when_identical(
        self, writer: AuditWriter, replay_engine: ReplayEngine
    ) -> None:
        _make_bundle(writer, "orig-run-3")
        original_bundle = writer.read_bundle("orig-run-3")
        assert original_bundle is not None

        # "Fresh" result is identical to original
        new_result = original_bundle["final_artifacts"]
        result = replay_engine.replay_refresh("orig-run-3", "refresh-run-1", new_result)

        assert result["replay_mode"] == "refresh"
        assert result["drift"] == []

    def test_detects_addition_drift(
        self, writer: AuditWriter, replay_engine: ReplayEngine
    ) -> None:
        _make_bundle(writer, "orig-run-4")

        # Fresh result has an extra opportunity
        new_result = {
            "opportunities": [
                {"title": "Software Engineer at Acme", "source": "linkedin"},
                {"title": "Backend Developer at Globex", "source": "indeed"},
                {"title": "New Role at Initech", "source": "glassdoor"},
            ],
        }
        result = replay_engine.replay_refresh("orig-run-4", "refresh-run-2", new_result)

        additions = [d for d in result["drift"] if d["type"] == "addition"]
        assert len(additions) == 1
        assert additions[0]["title"] == "New Role at Initech"

    def test_detects_removal_drift(
        self, writer: AuditWriter, replay_engine: ReplayEngine
    ) -> None:
        _make_bundle(writer, "orig-run-5")

        # Fresh result is missing one opportunity
        new_result = {
            "opportunities": [
                {"title": "Software Engineer at Acme", "source": "linkedin"},
            ],
        }
        result = replay_engine.replay_refresh("orig-run-5", "refresh-run-3", new_result)

        removals = [d for d in result["drift"] if d["type"] == "removal"]
        assert len(removals) == 1
        assert removals[0]["title"] == "Backend Developer at Globex"

    def test_nonexistent_run_raises(self, replay_engine: ReplayEngine) -> None:
        with pytest.raises(ValueError, match="No bundle found"):
            replay_engine.replay_refresh("nonexistent", "new-run", {})


# ------------------------------------------------------------------
# DiffEngine
# ------------------------------------------------------------------


class TestDiffIdentical:
    def test_no_changes_for_identical_runs(
        self, writer: AuditWriter, diff_engine: DiffEngine
    ) -> None:
        opps = [
            {"title": "SWE", "source": "linkedin", "description": "code"},
        ]
        _make_bundle(writer, "run-a", opportunities=opps)
        _make_bundle(writer, "run-b", opportunities=opps)

        result = diff_engine.diff_runs("run-a", "run-b")

        assert result["additions"] == []
        assert result["removals"] == []
        assert result["changes"] == []
        assert result["summary"]["added"] == 0
        assert result["summary"]["removed"] == 0
        assert result["summary"]["changed"] == 0


class TestDiffAdditionsRemovals:
    def test_detects_additions(
        self, writer: AuditWriter, diff_engine: DiffEngine
    ) -> None:
        opps_a = [{"title": "SWE", "source": "linkedin"}]
        opps_b = [
            {"title": "SWE", "source": "linkedin"},
            {"title": "DevOps", "source": "indeed"},
        ]
        _make_bundle(writer, "diff-a-1", opportunities=opps_a)
        _make_bundle(writer, "diff-b-1", opportunities=opps_b)

        result = diff_engine.diff_runs("diff-a-1", "diff-b-1")

        assert result["summary"]["added"] == 1
        assert result["additions"][0]["title"] == "DevOps"
        assert result["summary"]["removed"] == 0

    def test_detects_removals(
        self, writer: AuditWriter, diff_engine: DiffEngine
    ) -> None:
        opps_a = [
            {"title": "SWE", "source": "linkedin"},
            {"title": "DevOps", "source": "indeed"},
        ]
        opps_b = [{"title": "SWE", "source": "linkedin"}]
        _make_bundle(writer, "diff-a-2", opportunities=opps_a)
        _make_bundle(writer, "diff-b-2", opportunities=opps_b)

        result = diff_engine.diff_runs("diff-a-2", "diff-b-2")

        assert result["summary"]["removed"] == 1
        assert result["removals"][0]["title"] == "DevOps"
        assert result["summary"]["added"] == 0

    def test_detects_changes(
        self, writer: AuditWriter, diff_engine: DiffEngine
    ) -> None:
        opps_a = [
            {
                "title": "SWE",
                "source": "linkedin",
                "description": "Build things",
                "url": "https://example.com/1",
            },
        ]
        opps_b = [
            {
                "title": "SWE",
                "source": "linkedin",
                "description": "Build awesome things",
                "url": "https://example.com/1-updated",
            },
        ]
        _make_bundle(writer, "diff-a-3", opportunities=opps_a)
        _make_bundle(writer, "diff-b-3", opportunities=opps_b)

        result = diff_engine.diff_runs("diff-a-3", "diff-b-3")

        assert result["summary"]["changed"] == 1
        assert result["summary"]["added"] == 0
        assert result["summary"]["removed"] == 0

        change = result["changes"][0]
        assert change["title"] == "SWE"
        assert change["changes"]["description"]["old"] == "Build things"
        assert change["changes"]["description"]["new"] == "Build awesome things"
        assert change["changes"]["url"]["old"] == "https://example.com/1"
        assert change["changes"]["url"]["new"] == "https://example.com/1-updated"


class TestDiffErrors:
    def test_nonexistent_run_a_raises(
        self, writer: AuditWriter, diff_engine: DiffEngine
    ) -> None:
        _make_bundle(writer, "exists-run")
        with pytest.raises(ValueError, match="No bundle found for run nonexistent"):
            diff_engine.diff_runs("nonexistent", "exists-run")

    def test_nonexistent_run_b_raises(
        self, writer: AuditWriter, diff_engine: DiffEngine
    ) -> None:
        _make_bundle(writer, "exists-run-2")
        with pytest.raises(ValueError, match="No bundle found for run nonexistent"):
            diff_engine.diff_runs("exists-run-2", "nonexistent")


class TestDiffSummary:
    def test_verifier_status_comparison(
        self, writer: AuditWriter, diff_engine: DiffEngine
    ) -> None:
        _make_bundle(writer, "v-run-a", verifier_status="pass")
        _make_bundle(writer, "v-run-b", verifier_status="partial")

        result = diff_engine.diff_runs("v-run-a", "v-run-b")

        assert result["summary"]["verifier_a"] == "pass"
        assert result["summary"]["verifier_b"] == "partial"

    def test_opportunity_counts(
        self, writer: AuditWriter, diff_engine: DiffEngine
    ) -> None:
        opps_a = [{"title": "A", "source": "s"}]
        opps_b = [{"title": "B", "source": "s"}, {"title": "C", "source": "s"}]
        _make_bundle(writer, "count-a", opportunities=opps_a)
        _make_bundle(writer, "count-b", opportunities=opps_b)

        result = diff_engine.diff_runs("count-a", "count-b")

        assert result["summary"]["opportunities_a"] == 1
        assert result["summary"]["opportunities_b"] == 2
