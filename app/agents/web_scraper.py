"""WebScraper agent: LLM-powered web search with structured output."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from app.agents.base import LLMAgent
from app.agents.schemas import WebScraperOutput

logger = logging.getLogger(__name__)


class WebScraperAgent(LLMAgent):
    """Searches the web via an LLM with a bound search tool.

    In mock mode (llm=None), returns hardcoded fixture data.
    In live mode, binds the search tool to the LLM and uses a
    tool-calling loop to find and return structured results.
    """

    agent_name = "web_scraper"

    def __init__(
        self,
        llm: Any | None = None,
        prompt_loader: Any | None = None,
        search_tool: Any | None = None,
    ):
        super().__init__(llm=llm, prompt_loader=prompt_loader)
        self._search_tool = search_tool

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        prompt = state.get("search_prompt", "")
        category = state.get("search_category", "")
        result_key = f"raw_{category}_results"

        if self._llm is None:
            return {result_key: self._mock_results(category)}

        try:
            today = date.today().isoformat()
            system_prompt = self._get_system_prompt(today=today)
            user_content = f"Search for: {prompt}"

            search_context = ""
            if self._search_tool is not None:
                # Tool-calling loop: bind search tool to LLM
                llm_with_tools = self._llm.bind_tools([self._search_tool])
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ]
                response = await llm_with_tools.ainvoke(messages)
                messages.append(response)

                # Process tool calls until the LLM returns a final response
                while response.tool_calls:
                    for tool_call in response.tool_calls:
                        tool_result = await self._search_tool.ainvoke(
                            tool_call["args"]
                        )
                        messages.append({
                            "role": "tool",
                            "content": str(tool_result),
                            "tool_call_id": tool_call["id"],
                        })
                    response = await llm_with_tools.ainvoke(messages)
                    messages.append(response)

                search_context = response.content or ""

            # Parse the final response as structured output,
            # including actual search results as context
            structured_input = (
                f"Search for: {prompt}\n\nSearch results found:\n{search_context}"
                if search_context
                else user_content
            )
            result = await self._invoke_structured(
                WebScraperOutput, system_prompt, structured_input
            )
            results = [r.model_dump() for r in result.results]
            return {result_key: results}

        except Exception as exc:
            logger.warning("WebScraper failed for %s: %s", category, exc)
            return {result_key: [], "errors": [f"WebScraper ({category}): {exc}"]}

    @staticmethod
    def _mock_results(category: str) -> list[dict[str, str]]:
        """Return hardcoded results for testing."""
        mocks = {
            "job": [
                {"title": "Senior Python Developer at TechCorp", "url": "https://example.com/job/1", "snippet": "Python, FastAPI, cloud experience required", "source": "LinkedIn"},
                {"title": "Backend Engineer at StartupXYZ", "url": "https://example.com/job/2", "snippet": "Building scalable APIs with Python", "source": "Indeed"},
                {"title": "Full Stack Developer at BigCo", "url": "https://example.com/job/3", "snippet": "React + Python full stack role", "source": "Glassdoor"},
            ],
            "cert": [
                {"title": "AWS Solutions Architect", "url": "https://example.com/cert/1", "snippet": "Cloud architecture certification", "source": "Amazon"},
                {"title": "Google Cloud Professional", "url": "https://example.com/cert/2", "snippet": "GCP certification program", "source": "Google"},
            ],
            "event": [
                {"title": "PyCon 2026", "url": "https://example.com/event/1", "snippet": "Annual Python conference", "source": "Python Software Foundation"},
                {"title": "KubeCon Europe", "url": "https://example.com/event/2", "snippet": "Kubernetes community conference", "source": "CNCF"},
            ],
            "group": [
                {"title": "Python Discord", "url": "https://example.com/group/1", "snippet": "Active Python community", "source": "Discord"},
                {"title": "r/Python", "url": "https://example.com/group/2", "snippet": "Python subreddit community", "source": "Reddit"},
            ],
            "trend": [
                {"title": "AI-Driven DevOps Automation", "url": "https://example.com/trend/1", "snippet": "Growing adoption of AI tools in CI/CD pipelines", "source": "TechCrunch"},
                {"title": "Edge Computing Growth", "url": "https://example.com/trend/2", "snippet": "Edge computing market expanding rapidly", "source": "Hacker News"},
            ],
        }
        return mocks.get(category, [])
