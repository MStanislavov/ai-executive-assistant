"""Cover letter agent: generates a cover letter from CV + JD."""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import LLMAgent


class CoverLetterAgent(LLMAgent):
    agent_name = "cover_letter"

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        cv_content = state.get("cv_content", "")
        jd_text = state.get("jd_text", "")
        job_opportunity = state.get("job_opportunity", {})

        if self._llm is None:
            title = job_opportunity.get("title", "the position")
            return {
                "cover_letter_content": (
                    f"Dear Hiring Manager,\n\n"
                    f"I am writing to express my interest in {title}. "
                    f"My experience aligns well with the requirements outlined.\n\n"
                    f"Based on the job description, I believe my skills make me a strong candidate.\n\n"
                    f"Thank you for considering my application.\n\n"
                    f"Sincerely,\nThe Candidate"
                ),
            }

        system_prompt = self._get_system_prompt()
        user_content = (
            f"CV Content:\n{cv_content}\n\n"
            f"Job Description:\n{jd_text}\n\n"
            f"Opportunity Details:\n{json.dumps(job_opportunity)}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        response = self._llm.invoke(messages)
        return {"cover_letter_content": response.content}
