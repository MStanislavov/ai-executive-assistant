"""Agent protocol and base class for LLM-powered agents."""

from __future__ import annotations

import logging
from typing import Any, Protocol

from app.llm.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class AgentProtocol(Protocol):
    """All agents must be callable: (state) -> state."""

    agent_name: str

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]: ...


class LLMAgent:
    """Base class for agents that use ChatOpenAI with structured output."""

    agent_name: str = ""

    def __init__(
        self,
        llm: Any | None = None,
        prompt_loader: PromptLoader | None = None,
    ):
        self._llm = llm
        self._prompt_loader = prompt_loader

    def _get_system_prompt(self, **kwargs: str) -> str:
        if self._prompt_loader is None:
            return f"You are a helpful {self.agent_name} agent."
        return self._prompt_loader.load(self.agent_name, **kwargs)

    def _invoke_structured(
        self,
        schema: type,
        system_prompt: str,
        user_content: str,
    ) -> Any:
        """Invoke the LLM with structured output. Returns the parsed schema instance."""
        structured_llm = self._llm.with_structured_output(schema)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        return structured_llm.invoke(messages)
