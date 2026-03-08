"""LangGraph state definitions for all pipeline modes."""

from __future__ import annotations

from typing import Any, TypedDict


class DailyState(TypedDict, total=False):
    # Input
    profile_id: str
    profile_targets: list[str]
    source_config: dict[str, Any]

    # Raw retrievals
    raw_job_listings: list[dict[str, Any]]
    raw_cert_listings: list[dict[str, Any]]
    raw_trends_data: list[dict[str, Any]]

    # Extracted
    extracted_opportunities: list[dict[str, Any]]
    evidence_items: list[dict[str, Any]]

    # Coordinator output
    ranked_opportunities: list[dict[str, Any]]
    claims: list[dict[str, Any]]
    summary: str

    # Verifier
    verifier_report: dict[str, Any]

    # Audit
    audit_events: list[dict[str, Any]]
    run_id: str

    # Error tracking
    errors: list[str]
    safe_degradation: bool


class CoverLetterState(TypedDict, total=False):
    # Input
    profile_id: str
    cv_content: str
    opportunity_id: str
    jd_text: str
    opportunity: dict[str, Any]

    # Cover letter output
    cover_letter_content: str
    claims: list[dict[str, Any]]
    evidence_items: list[dict[str, Any]]

    # Verifier
    verifier_report: dict[str, Any]

    # Audit
    audit_events: list[dict[str, Any]]
    run_id: str

    # Error tracking
    errors: list[str]


class WeeklyState(TypedDict, total=False):
    # Input
    profile_id: str
    profile_targets: list[str]
    source_config: dict[str, Any]

    # Raw retrievals (all 3 scout types)
    raw_job_listings: list[dict[str, Any]]
    raw_cert_listings: list[dict[str, Any]]
    raw_trends_data: list[dict[str, Any]]

    # Extracted
    extracted_opportunities: list[dict[str, Any]]
    evidence_items: list[dict[str, Any]]

    # Coordinator output
    ranked_opportunities: list[dict[str, Any]]
    claims: list[dict[str, Any]]
    summary: str

    # CEO / CFO outputs
    strategic_recommendations: list[dict[str, Any]]
    risk_assessment: list[dict[str, Any]]

    # Verifier
    verifier_report: dict[str, Any]

    # Audit
    audit_events: list[dict[str, Any]]
    run_id: str

    # Error tracking
    errors: list[str]
    safe_degradation: bool
