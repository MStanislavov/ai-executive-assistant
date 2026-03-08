"""Tests for the PolicyEngine."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from app.engine.policy_engine import Budget, PolicyEngine


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def policy_dir(tmp_path: Path) -> Path:
    """Create a minimal but complete set of policy YAML files."""
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
            "coordinator": {
                "allowed_tools": ["merge_items", "rank_items"],
                "denied_tools": ["web_search", "web_fetch", "rss_fetch"],
            },
        }
    }
    sources = {
        "scouts": {
            "job_scout": {
                "allowed_sources": ["linkedin.com/jobs", "indeed.com"],
                "denied_sources": ["*.onion"],
            },
            "cert_scout": {
                "allowed_sources": ["coursera.org"],
                "denied_sources": [],
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
    boundaries = {
        "agents": {
            "job_scout_retriever": {
                "inputs": ["profile_targets", "source_config"],
                "outputs": ["raw_job_listings"],
            },
            "coordinator": {
                "inputs": ["extracted_opportunities", "evidence_items"],
                "outputs": ["ranked_opportunities", "claims", "summary"],
            },
        }
    }
    redaction = {
        "rules": [
            {
                "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "replacement": "[REDACTED_EMAIL]",
                "applies_to": ["audit_log"],
            },
            {
                "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
                "replacement": "[REDACTED_SSN]",
                "applies_to": ["audit_log", "run_bundle"],
            },
        ]
    }

    for name, data in [
        ("tools", tools),
        ("sources", sources),
        ("budgets", budgets),
        ("boundaries", boundaries),
        ("redaction", redaction),
    ]:
        (tmp_path / f"{name}.yaml").write_text(yaml.dump(data), encoding="utf-8")

    return tmp_path


@pytest.fixture()
def engine(policy_dir: Path) -> PolicyEngine:
    return PolicyEngine(policy_dir)


# ------------------------------------------------------------------
# Loading / introspection
# ------------------------------------------------------------------


class TestLoading:
    def test_list_policies(self, engine: PolicyEngine) -> None:
        names = engine.list_policies()
        assert set(names) == {"tools", "sources", "budgets", "boundaries", "redaction"}

    def test_get_policy_returns_dict(self, engine: PolicyEngine) -> None:
        tools = engine.get_policy("tools")
        assert "agents" in tools

    def test_get_policy_unknown_raises(self, engine: PolicyEngine) -> None:
        with pytest.raises(KeyError, match="not found"):
            engine.get_policy("nonexistent")

    def test_version_hash_is_stable(self, engine: PolicyEngine) -> None:
        h1 = engine.version.hash
        h2 = engine.version.hash
        assert h1 == h2

    def test_version_hash_changes_on_yaml_edit(self, policy_dir: Path) -> None:
        engine = PolicyEngine(policy_dir)
        h1 = engine.version.hash

        # Mutate a YAML file
        budgets_path = policy_dir / "budgets.yaml"
        data = yaml.safe_load(budgets_path.read_text(encoding="utf-8"))
        data["global"]["max_output_items"] = 999
        budgets_path.write_text(yaml.dump(data), encoding="utf-8")

        engine.reload()
        h2 = engine.version.hash
        assert h1 != h2

    def test_version_policies_snapshot(self, engine: PolicyEngine) -> None:
        pv = engine.version
        assert isinstance(pv.policies, dict)
        assert "tools" in pv.policies


# ------------------------------------------------------------------
# Tool enforcement
# ------------------------------------------------------------------


class TestToolAllowlist:
    def test_allowed_tool_returns_true(self, engine: PolicyEngine) -> None:
        assert engine.is_tool_allowed("job_scout_retriever", "web_search") is True

    def test_denied_tool_returns_false(self, engine: PolicyEngine) -> None:
        assert engine.is_tool_allowed("job_scout_extractor", "web_search") is False

    def test_unlisted_tool_returns_false(self, engine: PolicyEngine) -> None:
        assert engine.is_tool_allowed("job_scout_retriever", "nuclear_launch") is False

    def test_unknown_agent_returns_false(self, engine: PolicyEngine) -> None:
        assert engine.is_tool_allowed("unknown_agent", "web_search") is False

    def test_coordinator_denied_retrieval(self, engine: PolicyEngine) -> None:
        for tool in ("web_search", "web_fetch", "rss_fetch"):
            assert engine.is_tool_allowed("coordinator", tool) is False

    def test_coordinator_allowed_planning(self, engine: PolicyEngine) -> None:
        assert engine.is_tool_allowed("coordinator", "merge_items") is True
        assert engine.is_tool_allowed("coordinator", "rank_items") is True


# ------------------------------------------------------------------
# Source enforcement
# ------------------------------------------------------------------


class TestSourceAllowlist:
    def test_allowed_source(self, engine: PolicyEngine) -> None:
        assert engine.is_source_allowed("job_scout", "https://linkedin.com/jobs/123") is True

    def test_denied_wildcard_source(self, engine: PolicyEngine) -> None:
        assert engine.is_source_allowed("job_scout", "http://something.onion") is False

    def test_denied_onion_source(self, engine: PolicyEngine) -> None:
        assert engine.is_source_allowed("job_scout", "darkweb.onion") is False

    def test_unlisted_source_returns_false(self, engine: PolicyEngine) -> None:
        assert engine.is_source_allowed("job_scout", "https://randomsite.xyz") is False

    def test_unknown_scout_returns_false(self, engine: PolicyEngine) -> None:
        assert engine.is_source_allowed("nonexistent_scout", "indeed.com") is False

    def test_cert_scout_allowed(self, engine: PolicyEngine) -> None:
        assert engine.is_source_allowed("cert_scout", "https://coursera.org/cert") is True

    def test_cert_scout_no_denied(self, engine: PolicyEngine) -> None:
        # cert_scout has empty denied list, but unlisted sources still fail
        assert engine.is_source_allowed("cert_scout", "https://randomsite.xyz") is False


# ------------------------------------------------------------------
# Budget queries
# ------------------------------------------------------------------


class TestBudgets:
    def test_get_budget_known_agent(self, engine: PolicyEngine) -> None:
        budget = engine.get_budget("job_scout_retriever")
        assert isinstance(budget, Budget)
        assert budget.max_steps == 5
        assert budget.max_tokens == 4000

    def test_get_budget_coordinator(self, engine: PolicyEngine) -> None:
        budget = engine.get_budget("coordinator")
        assert budget.max_steps == 3
        assert budget.max_tokens == 6000

    def test_get_budget_unknown_raises(self, engine: PolicyEngine) -> None:
        with pytest.raises(KeyError, match="No budget"):
            engine.get_budget("nonexistent_agent")


# ------------------------------------------------------------------
# Boundary queries
# ------------------------------------------------------------------


class TestBoundaries:
    def test_get_boundaries_known_agent(self, engine: PolicyEngine) -> None:
        b = engine.get_boundaries("job_scout_retriever")
        assert b["inputs"] == ["profile_targets", "source_config"]
        assert b["outputs"] == ["raw_job_listings"]

    def test_get_boundaries_coordinator(self, engine: PolicyEngine) -> None:
        b = engine.get_boundaries("coordinator")
        assert "extracted_opportunities" in b["inputs"]
        assert "ranked_opportunities" in b["outputs"]

    def test_get_boundaries_unknown_raises(self, engine: PolicyEngine) -> None:
        with pytest.raises(KeyError, match="No boundaries"):
            engine.get_boundaries("nonexistent_agent")


# ------------------------------------------------------------------
# Redaction
# ------------------------------------------------------------------


class TestRedaction:
    def test_get_redaction_rules_returns_list(self, engine: PolicyEngine) -> None:
        rules = engine.get_redaction_rules()
        assert isinstance(rules, list)
        assert len(rules) >= 2

    def test_apply_redaction_email(self, engine: PolicyEngine) -> None:
        text = "Contact user@example.com for info"
        result = engine.apply_redaction(text, "audit_log")
        assert "[REDACTED_EMAIL]" in result
        assert "user@example.com" not in result

    def test_apply_redaction_ssn(self, engine: PolicyEngine) -> None:
        text = "SSN is 123-45-6789"
        result = engine.apply_redaction(text, "audit_log")
        assert "[REDACTED_SSN]" in result
        assert "123-45-6789" not in result

    def test_apply_redaction_ssn_in_bundle(self, engine: PolicyEngine) -> None:
        text = "SSN is 123-45-6789"
        result = engine.apply_redaction(text, "run_bundle")
        assert "[REDACTED_SSN]" in result

    def test_apply_redaction_email_not_in_bundle(self, engine: PolicyEngine) -> None:
        # Email redaction only applies_to audit_log, not run_bundle
        text = "Contact user@example.com"
        result = engine.apply_redaction(text, "run_bundle")
        assert "user@example.com" in result

    def test_apply_redaction_no_match(self, engine: PolicyEngine) -> None:
        text = "Nothing sensitive here"
        result = engine.apply_redaction(text, "audit_log")
        assert result == text


# ------------------------------------------------------------------
# Global config
# ------------------------------------------------------------------


class TestGlobalConfig:
    def test_get_global_config(self, engine: PolicyEngine) -> None:
        cfg = engine.get_global_config()
        assert cfg["max_run_duration_seconds"] == 300
        assert cfg["max_output_items"] == 50
