"""Loads system prompts from Markdown files in prompts/ directory."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PromptLoader:
    """Loads and caches prompt templates from the prompts directory."""

    def __init__(self, prompts_dir: Path):
        self._prompts_dir = prompts_dir
        self._cache: dict[str, str] = {}

    def load(self, prompt_name: str, **kwargs: str) -> str:
        """Load a prompt template and format with kwargs.

        Args:
            prompt_name: Name without extension (e.g., "extractor", "coordinator")
            **kwargs: Template variables to substitute via str.format()

        Returns:
            Formatted prompt string.
        """
        if prompt_name not in self._cache:
            path = self._prompts_dir / f"{prompt_name}.md"
            if not path.exists():
                logger.warning("Prompt file not found: %s", path)
                return f"You are a helpful {prompt_name} agent."
            self._cache[prompt_name] = path.read_text(encoding="utf-8")

        template = self._cache[prompt_name]
        if kwargs:
            try:
                return template.format(**kwargs)
            except KeyError as e:
                logger.warning("Missing template var %s in prompt %s", e, prompt_name)
                return template
        return template

    def clear_cache(self) -> None:
        self._cache.clear()
