"""GoalExtractor agent: converts profile targets + skills + CV into search prompts."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from app.agents.base import LLMAgent
from app.agents.schemas import GoalExtractorOutput


class GoalExtractorAgent(LLMAgent):
    agent_name = "goal_extractor"

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        targets = state.get("profile_targets", [])
        skills = state.get("profile_skills", [])
        constraints = state.get("profile_constraints", [])
        cv_summary = state.get("cv_summary", "")
        today = date.today().isoformat()

        if self._llm is None:
            # Mock mode: generate simple search queries from targets
            target_str = ", ".join(targets) if targets else "software engineering"
            constraint_str = ", ".join(constraints) if constraints else ""
            suffix = f", constraints: {constraint_str}" if constraint_str else ""
            return {
                "search_prompts": {
                    "cert_prompt": f"best certifications for {target_str}{suffix} {today}",
                    "event_prompt": f"tech conferences and events for {target_str}{suffix} {today}",
                    "group_prompt": f"professional communities and groups for {target_str}{suffix} {today}",
                    "job_prompt": f"job openings for {target_str}{suffix} {today}",
                    "trend_prompt": f"emerging trends and market developments in {target_str}{suffix} {today}",
                },
            }

        system_prompt = self._get_system_prompt(today=today)
        user_parts = [
            f"Today's date: {today}",
            f"Profile targets: {json.dumps(targets)}",
            f"Profile skills: {json.dumps(skills)}",
        ]
        if constraints:
            user_parts.append(f"Profile constraints: {json.dumps(constraints)}")
        if cv_summary:
            user_parts.append(f"CV summary:\n{cv_summary[:3000]}")

        user_content = "\n".join(user_parts)
        result = self._invoke_structured(GoalExtractorOutput, system_prompt, user_content)
        return {
            "search_prompts": {
                "cert_prompt": result.cert_prompt,
                "event_prompt": result.event_prompt,
                "group_prompt": result.group_prompt,
                "job_prompt": result.job_prompt,
                "trend_prompt": result.trend_prompt,
            },
        }
