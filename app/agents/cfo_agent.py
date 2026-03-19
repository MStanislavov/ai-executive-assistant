"""CFO agent: provides risk assessments from all 5 DTO lists."""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import LLMAgent
from app.agents.schemas import CFOOutput


class CFOAgent(LLMAgent):
    agent_name = "cfo"

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        if self._llm is None:
            return {
                "risk_assessments": [
                    {
                        "area": "Job market",
                        "risk_level": "medium",
                        "time_investment": "2-3 months for job search",
                        "roi_estimate": "high",
                    },
                    {
                        "area": "Certifications",
                        "risk_level": "low",
                        "time_investment": "40-80 hours study time",
                        "roi_estimate": "medium",
                    },
                ],
                "cfo_summary": "Investment in certifications has low risk and good ROI.",
            }

        system_prompt = self._get_system_prompt()
        user_content = (
            f"Profile targets: {json.dumps(state.get('profile_targets', []))}\n\n"
            f"Jobs: {json.dumps(state.get('formatted_jobs', []))}\n"
            f"Certifications: {json.dumps(state.get('formatted_certifications', []))}\n"
            f"Courses: {json.dumps(state.get('formatted_courses', []))}\n"
            f"Events: {json.dumps(state.get('formatted_events', []))}\n"
            f"Groups: {json.dumps(state.get('formatted_groups', []))}\n"
            f"Trends: {json.dumps(state.get('formatted_trends', []))}"
        )
        result = self._invoke_structured(CFOOutput, system_prompt, user_content)
        return {
            "risk_assessments": [r.model_dump() for r in result.risk_assessments],
            "cfo_summary": result.cfo_summary,
        }
