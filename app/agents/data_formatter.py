"""DataFormatter agent: converts raw search results into structured DTOs."""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import LLMAgent
from app.agents.schemas import DataFormatterOutput


class DataFormatterAgent(LLMAgent):
    agent_name = "data_formatter"

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        raw_jobs = state.get("raw_job_results", [])
        raw_certs = state.get("raw_cert_results", [])
        raw_events = state.get("raw_event_results", [])
        raw_groups = state.get("raw_group_results", [])
        raw_trends = state.get("raw_trend_results", [])

        if self._llm is None:
            return self._mock_format(raw_jobs, raw_certs, raw_events, raw_groups, raw_trends)

        system_prompt = self._get_system_prompt()
        user_content = (
            f"Raw job results:\n{json.dumps(raw_jobs, indent=2)}\n\n"
            f"Raw certification results:\n{json.dumps(raw_certs, indent=2)}\n\n"
            f"Raw event results:\n{json.dumps(raw_events, indent=2)}\n\n"
            f"Raw group results:\n{json.dumps(raw_groups, indent=2)}\n\n"
            f"Raw trend results:\n{json.dumps(raw_trends, indent=2)}"
        )
        result = await self._invoke_structured(DataFormatterOutput, system_prompt, user_content)
        return {
            "formatted_jobs": [j.model_dump() for j in result.jobs],
            "formatted_certifications": [c.model_dump() for c in result.certifications],
            "formatted_courses": [c.model_dump() for c in result.courses],
            "formatted_events": [e.model_dump() for e in result.events],
            "formatted_groups": [g.model_dump() for g in result.groups],
            "formatted_trends": [t.model_dump() for t in result.trends],
        }

    @staticmethod
    def _extract_company(title: str) -> str | None:
        """Extract company from 'Role at Company' title pattern."""
        if " at " in title:
            return title.rsplit(" at ", 1)[1]
        return None

    @classmethod
    def _mock_format(
        cls,
        raw_jobs: list[dict],
        raw_certs: list[dict],
        raw_events: list[dict],
        raw_groups: list[dict],
        raw_trends: list[dict],
    ) -> dict[str, Any]:
        """Convert raw results to formatted DTOs in mock mode."""
        jobs = [
            {
                "title": r.get("title", "Untitled"),
                "company": cls._extract_company(r.get("title", "")) or r.get("source"),
                "url": r.get("url"),
                "description": r.get("snippet"),
                "location": None,
                "salary_range": None,
            }
            for r in raw_jobs
        ]
        certs = [
            {
                "title": r.get("title", "Untitled"),
                "provider": r.get("source"),
                "url": r.get("url"),
                "description": r.get("snippet"),
                "cost": None,
                "duration": None,
            }
            for r in raw_certs
        ]
        events = [
            {
                "title": r.get("title", "Untitled"),
                "organizer": r.get("source"),
                "url": r.get("url"),
                "description": r.get("snippet"),
                "event_date": None,
                "location": None,
            }
            for r in raw_events
        ]
        groups = [
            {
                "title": r.get("title", "Untitled"),
                "platform": r.get("source"),
                "url": r.get("url"),
                "description": r.get("snippet"),
                "member_count": None,
            }
            for r in raw_groups
        ]
        trends = [
            {
                "title": r.get("title", "Untitled"),
                "category": None,
                "url": r.get("url"),
                "description": r.get("snippet"),
                "relevance": None,
                "source": r.get("source"),
            }
            for r in raw_trends
        ]
        return {
            "formatted_jobs": jobs,
            "formatted_certifications": certs,
            "formatted_courses": [],
            "formatted_events": events,
            "formatted_groups": groups,
            "formatted_trends": trends,
        }
