"""Applies LLM-generated file changes to the target repository.

The editor accepts complete-file updates in a constrained BEGIN_FILE format,
validates that every destination remains inside target_repo, and writes only
when content actually changed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from config import AgentConfig
from llm import LLMImplementation


FILE_BLOCK_PATTERN = re.compile(
    r"BEGIN_FILE:\s*(?P<path>[^\n]+)\n"
    r"```(?:[a-zA-Z0-9_+.-]+)?\n"
    r"(?P<content>.*?)"
    r"\n```\s*END_FILE",
    re.DOTALL,
)


@dataclass(frozen=True)
class AppliedChange:
    """A file write performed by the editor."""

    path: Path
    relative_path: str
    action: str


class CodeEditor:
    """Parses and applies implementation output from the LLM."""

    def __init__(self, config: AgentConfig) -> None:
        self._config = config

    def apply(self, implementation: LLMImplementation) -> tuple[AppliedChange, ...]:
        """Apply all valid file blocks from a model implementation response."""

        changes: list[AppliedChange] = []
        blocks = list(FILE_BLOCK_PATTERN.finditer(implementation.text))

        if not blocks:
            raise ValueError("No valid BEGIN_FILE blocks were found in the LLM output.")

        for block in blocks:
            relative_path = self._normalize_relative_path(block.group("path"))
            content = block.group("content").rstrip() + "\n"
            destination = self._resolve_target_path(relative_path)

            previous_content = destination.read_text(encoding="utf-8") if destination.exists() else None
            if previous_content == content:
                continue

            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")
            changes.append(
                AppliedChange(
                    path=destination,
                    relative_path=relative_path,
                    action="updated" if previous_content is not None else "created",
                )
            )

        return tuple(changes)

    @staticmethod
    def _normalize_relative_path(path_text: str) -> str:
        """Normalize an LLM-provided target path."""

        normalized = path_text.strip().replace("\\", "/")
        if normalized.startswith("target_repo/"):
            normalized = normalized.removeprefix("target_repo/")

        if not normalized or normalized.startswith("/") or normalized.startswith("../"):
            raise ValueError(f"Unsafe file path from LLM output: {path_text}")

        return normalized

    def _resolve_target_path(self, relative_path: str) -> Path:
        """Resolve a relative target path and ensure it stays inside target_repo."""

        target_root = self._config.target_repo.resolve()
        destination = (target_root / relative_path).resolve()

        if destination != target_root and target_root not in destination.parents:
            raise ValueError(f"Refusing to write outside target_repo: {relative_path}")

        return destination
