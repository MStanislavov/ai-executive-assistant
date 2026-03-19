"""CEO agent: provides strategic recommendations from all 5 DTO lists."""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import LLMAgent
from app.agents.schemas import CEOOutput


class CEOAgent(LLMAgent):
    agent_name = "ceo"

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        if self._llm is None:
            return {
                "strategic_recommendations": [
                    {
                        "area": "Career development",
                        "recommendation": "Focus on cloud certifications to complement existing skills",
                        "priority": "high",
                    },
                    {
                        "area": "Networking",
                        "recommendation": "Attend PyCon 2026 to build industry connections",
                        "priority": "medium",
                    },
                ],
                "ceo_summary": "Strategic outlook is positive. Focus on cloud skills and networking.",
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
        result = self._invoke_structured(CEOOutput, system_prompt, user_content)
        return {
            "strategic_recommendations": [r.model_dump() for r in result.strategic_recommendations],
            "ceo_summary": result.ceo_summary,
        }
