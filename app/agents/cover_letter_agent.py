"""Cover letter agent: generates a cover letter from CV + JD."""

from __future__ import annotations

import json
import re
from typing import Any

from app.agents.base import LLMAgent


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting so text reads as plain prose."""
    # Remove headers (### Title -> Title)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    # Remove bullet prefixes
    text = re.sub(r"^[\-\*]\s+", "", text, flags=re.MULTILINE)
    # Collapse multiple newlines into a single space
    text = re.sub(r"\n+", " ", text)
    # Collapse multiple spaces
    text = re.sub(r"  +", " ", text)
    return text.strip()


# Section headers that should NOT be treated as a person's name
_SECTION_HEADERS = frozenset({
    "professional summary", "summary", "experience", "education",
    "skills", "certifications", "projects", "contact", "objective",
    "work experience", "technical skills", "profile", "about",
    "about me", "references", "languages", "interests", "hobbies",
})


def _extract_name_from_cv(cv_text: str) -> str | None:
    """Try to extract the person's name from the first line of CV text.

    CVs typically start with the person's name before any section header.
    Returns None if no plausible name is found.
    """
    if not cv_text or not cv_text.strip():
        return None
    for line in cv_text.strip().splitlines():
        line = re.sub(r"^#{1,6}\s+", "", line).strip()
        line = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", line).strip()
        if not line:
            continue
        normalized = line.lower()
        if normalized in _SECTION_HEADERS:
            continue
        # A name is typically 2-4 short words, all alphabetic
        words = line.split()
        if 2 <= len(words) <= 4 and all(w.isalpha() for w in words):
            return line
        # If the first non-empty, non-header line isn't a name, stop looking
        break
    return None


class CoverLetterAgent(LLMAgent):
    agent_name = "cover_letter"

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        cv_content = state.get("cv_content", "")
        jd_text = state.get("jd_text", "")
        job_opportunity = state.get("job_opportunity", {})
        profile_name = state.get("profile_name", "")
        profile_targets = state.get("profile_targets", [])
        profile_skills = state.get("profile_skills", [])
        profile_constraints = state.get("profile_constraints", [])

        if self._llm is None:
            return self._mock_cover_letter(
                profile_name, profile_skills, job_opportunity,
                cv_content, jd_text, profile_targets, profile_constraints,
            )

        system_prompt = self._get_system_prompt()

        sections = []
        if profile_name:
            sections.append(f"## Candidate Name\n{profile_name}")
        if profile_targets:
            sections.append(
                f"## Career Targets\n{', '.join(profile_targets)}"
            )
        if profile_skills:
            sections.append(f"## Key Skills\n{', '.join(profile_skills)}")
        if profile_constraints:
            sections.append(
                f"## Constraints/Preferences\n{', '.join(profile_constraints)}"
            )
        sections.append(f"## CV Summary\n{cv_content}")
        sections.append(f"## Job Description\n{jd_text}")
        if job_opportunity:
            sections.append(
                f"## Opportunity Details\n{json.dumps(job_opportunity)}"
            )

        user_content = "\n\n".join(sections)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        response = await self._llm.ainvoke(messages)
        content = response.content.replace("\u2014", ",").replace("\u2013", ",")
        return {"cover_letter_content": content}

    @staticmethod
    def _mock_cover_letter(
        profile_name: str,
        profile_skills: list[str],
        job_opportunity: dict[str, Any],
        cv_content: str = "",
        jd_text: str = "",
        profile_targets: list[str] | None = None,
        profile_constraints: list[str] | None = None,
    ) -> dict[str, Any]:
        name = _extract_name_from_cv(cv_content) or profile_name or "The Candidate"
        title = job_opportunity.get("title", "the position")
        company = job_opportunity.get("company", "your organization")
        description = job_opportunity.get("description", "")

        # Paragraph 1: Technical hook using CV context
        if cv_content and cv_content.strip():
            cv_clean = _strip_markdown(cv_content)
            cv_snippet = cv_clean[:200].rsplit(" ", 1)[0]
            hook = (
                f"Dear {company} Hiring Team,\n\n"
                f"Having built my career around delivering production-grade "
                f"software solutions, I was immediately drawn to the {title} "
                f"role at {company}. My background, which includes "
                f"{cv_snippet}, has given me a strong foundation in solving "
                f"the kinds of technical challenges this position demands. "
                f"I am confident that my hands-on experience positions me "
                f"to contribute meaningfully from day one."
            )
        else:
            hook = (
                f"Dear {company} Hiring Team,\n\n"
                f"Having built my career around delivering production-grade "
                f"software solutions, I was immediately drawn to the {title} "
                f"role at {company}. My track record of designing, building, "
                f"and shipping scalable systems across multiple domains has "
                f"given me a strong foundation in solving the kinds of "
                f"technical challenges this position demands. I am confident "
                f"that my hands-on experience positions me to contribute "
                f"meaningfully from day one."
            )

        # Paragraph 2: Stack alignment from skills + JD
        if profile_skills:
            primary = profile_skills[:3]
            secondary = profile_skills[3:6]
            skills_para = (
                f"My core expertise in {', '.join(primary)} aligns directly "
                f"with the technical requirements of this role. I have "
                f"applied these skills across production systems, "
                f"consistently delivering solutions that meet both "
                f"performance benchmarks and business objectives."
            )
            if secondary:
                skills_para += (
                    f" I also bring hands-on experience with "
                    f"{', '.join(secondary)}, which I have used across "
                    f"multiple production environments to deliver measurable "
                    f"improvements in system reliability, deployment "
                    f"velocity, and overall engineering quality."
                )
            if jd_text:
                jd_preview = _strip_markdown(jd_text)[:150].rsplit(" ", 1)[0]
                skills_para += (
                    f" Reviewing the role's requirements around "
                    f"{jd_preview}, I see a strong match with the projects "
                    f"I have led and the technical problems I have solved "
                    f"throughout my career."
                )
        elif jd_text:
            jd_preview = _strip_markdown(jd_text)[:200].rsplit(" ", 1)[0]
            skills_para = (
                f"The role's focus on {jd_preview} resonates strongly with "
                f"my professional experience. I have consistently delivered "
                f"solutions in similar technical domains, building systems "
                f"that balance performance, maintainability, and business "
                f"impact. I take pride in writing clean, well-tested code "
                f"and designing architectures that stand the test of time."
            )
        else:
            skills_para = (
                f"Throughout my career, I have consistently delivered "
                f"solutions that balance technical excellence with business "
                f"impact. I bring a strong foundation in software "
                f"engineering principles, system design, and collaborative "
                f"development practices that enable teams to ship reliable "
                f"software at scale. I take pride in writing clean, "
                f"well-tested code and designing architectures that are "
                f"both maintainable and performant."
            )

        # Paragraph 3: Culture fit, targets, and constraints
        culture_parts = []
        if profile_targets:
            culture_parts.append(
                f"My career trajectory toward {', '.join(profile_targets[:3])} "
                f"aligns well with the direction of this role"
            )
        if profile_constraints:
            culture_parts.append(
                f"I value a work environment that supports "
                f"{', '.join(profile_constraints[:2])}"
            )
        if description:
            desc_preview = _strip_markdown(description)[:120].rsplit(" ", 1)[0]
            culture_parts.append(
                f"the opportunity to work on {desc_preview} is "
                f"particularly compelling"
            )

        if culture_parts:
            culture_para = (
                f"{culture_parts[0]}, and "
                + ". ".join(culture_parts[1:])
                + ". I thrive in environments where engineering rigor meets "
                f"real-world problem solving, and I am eager to bring that "
                f"mindset to the {company} team. I believe that the best "
                f"software is built by teams that combine deep technical "
                f"skill with strong communication and a shared commitment "
                f"to quality."
            )
        else:
            culture_para = (
                f"I am drawn to teams that value engineering rigor, "
                f"continuous improvement, and collaborative problem solving. "
                f"The opportunity to contribute to {company}'s technical "
                f"challenges while growing alongside a talented team is "
                f"what makes this role stand out to me. I believe that the "
                f"best software is built by teams that combine deep "
                f"technical skill with strong communication and a shared "
                f"commitment to delivering real value to users."
            )

        # Paragraph 4: Call to action
        closing = (
            f"I would welcome the chance to discuss how my experience and "
            f"skills can contribute to {company}'s goals. I am genuinely "
            f"excited about the technical challenges this {title} role "
            f"presents and would appreciate the opportunity to speak with "
            f"you about how I can add value to your team. Please do not "
            f"hesitate to reach out at your convenience to arrange a "
            f"conversation.\n\n"
            f"Best regards,\n{name}"
        )

        content = f"{hook}\n\n{skills_para}\n\n{culture_para}\n\n{closing}"
        content = content.replace("\u2014", ",").replace("\u2013", ",")
        return {"cover_letter_content": content}
